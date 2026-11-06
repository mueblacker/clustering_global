# =========================================================================
# Evaluation of the cluster quality
# =========================================================================

# Import SparkSession
from pyspark.sql import SparkSession

# Create a Spark session
spark = SparkSession.builder.appName("cluster_stats").getOrCreate()


# Load modules
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast
from pyspark.ml.functions import vector_to_array
from pyspark.ml.linalg import Vectors
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeansModel


# Define the location of the standardized regional-unit environmental dataset
reg_path = '/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'

# Load a CSV file containing the names of environmental features selected
# after correlation filtering.
# The first column is assumed to contain the feature/variable names.
uncorr_envVar = spark.read.csv('/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv', 
                               header = True, inferSchema = True)
# Extract the values from the first column and collect them as a Python list.
# These values are expected to match column names in the regional dataset.
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
# Add identifier columns
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')

# Load the standardized regional data from Parquet format and select only
# the chosen environmental features and identifier columns.
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Remove rows that have one or more NULL values in the selected columns.
raw_data = raw_data.na.drop()


# Assemble scaled features
print('Assemble scaled features')

# Select environmental feature columns
selected_features = columns[0:len(columns)-3]

# Print the names of the features
print("Selected features:")
print(selected_features)

# Create a VectorAssembler that combines all selected environmental variables
# into one Spark ML vector column named `features`.
assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

# Apply the VectorAssembler to the complete environmental dataset.
# The resulting DataFrame includes original columns plus `features`,
# which contains the vector used for clustering.
df = assembler.transform(raw_data)


#  Load saved K-Means model -----------------------------------------------
print('Load saved K-Means model')

# Define the path of the previously fitted K-means model.
model_path = "/my_directory/data/clustering_global/l_fhc/lfhc_kmeans_model_30_v1"
# Load the saved K-means model
model = KMeansModel.load(model_path)

# Apply the K-means model to the assembled data
prediction_df = model.transform(df)


# Extract cluster centers -------------------------------------------------
print('Extract cluster centers')

# Extract K-means cluster centers from the fitted model.
#
# `model.clusterCenters()` returns a collection of centroid vectors, one for
# each cluster. `enumerate()` assigns cluster IDs beginning at 0, matching
# Spark K-means `prediction` labels.
#
# Each entry is converted to a dense vector and stored as:
# - cluster index / prediction label
# - centroid vector
centers = [
    (i, Vectors.dense([float(x) for x in center]))
    for i, center in enumerate(model.clusterCenters())
]

# Convert the Python list of cluster-centroid tuples into a Spark DataFrame.
# The DataFrame contains:
# - `prediction`: cluster identifier (cluster ID)
# - `centroid`: vector representing the cluster center
centers_df = spark.createDataFrame(
    centers,
    ["prediction", "centroid"]
)

# Broadcast the small centroid DataFrame so it can be joined efficiently
# with the much larger prediction DataFrame.
centers_df = broadcast(centers_df)


# Attach centroid to each row ---------------------------------------------
print('Attach centroid to each row')

# Join every clustered observation with the centroid of its assigned cluster
df_with_centroid = prediction_df.join(
    centers_df,
    on="prediction",
    how="inner"
)

# Repartition the dataset into 600 partitions before performing the
# computationally intensive vector-distance calculation.
df_with_centroid = df_with_centroid.repartition(600)


# Compute distance to centroid --------------------------------------------
print('Compute distance to centroid')

# Calculate the Euclidean distance from each observation's feature vector
# to the centroid of its assigned cluster.
#
# Calculation steps:
# 1. Convert both `features` and `centroid` vectors into arrays.
# 2. Zip corresponding feature and centroid values into pairs.
# 3. Use `aggregate()` to sum squared differences for all dimensions:
#      sum((feature_i - centroid_i)^2)
# 4. Take the square root to obtain Euclidean distance:
#      sqrt(sum((feature_i - centroid_i)^2))
#
# After calculating the distance, remove the centroid vector column because
# it is no longer required for subsequent statistics.

df_with_distance = (
    df_with_centroid
    .withColumn(
        "distance_to_centroid",
        F.sqrt(
            F.aggregate(
                F.arrays_zip(
                    vector_to_array("features").alias("f"),
                    vector_to_array("centroid").alias("c")
                ),
                F.lit(0.0),
                lambda acc, x: acc + F.pow(x["f"] - x["c"], 2)
            )
        )
    )
    .drop("centroid")
)


# Trigger computation of the distance DataFrame.
# Since Spark is lazy, this action forces the transformation pipeline above
# to run. It also materialize the cache. 
df_with_distance.count()


# Cluster statistics ------------------------------------------------------
print('Cluster statistics')

# Calculate distance-to-centroid statistics separately for every cluster.
#
# For each K-means cluster (`prediction`), calculate:
# - `count`: number of observations assigned to the cluster
# - `mean_distance`: average distance from observations to the centroid
# - `std_distance`: standard deviation of distances within the cluster
# - `p90_distance`: approximate 90th percentile of distances
# - `p99_distance`: approximate 99th percentile of distances
# - `min_distance`: smallest distance to the centroid
# - `max_distance`: largest distance to the centroid

cluster_stats = (
    df_with_distance
    .groupBy("prediction")
    .agg(
        F.count("*").alias("count"),
        F.mean("distance_to_centroid").alias("mean_distance"),
        F.stddev("distance_to_centroid").alias("std_distance"),
        F.expr(
            "percentile_approx(distance_to_centroid, 0.9)"
        ).alias("p90_distance"),
        F.expr(
            "percentile_approx(distance_to_centroid, 0.99)"
        ).alias("p99_distance"),
        F.min("distance_to_centroid").alias("min_distance"),
        F.max("distance_to_centroid").alias("max_distance")
    )
)



# Global statistics -------------------------------------------------------
print('Global statistics')


# Calculate distance-to-centroid statistics across all clusters combined.
#
# - `total_count`: total number of clustered observations
# - `global_mean_distance`: average distance to assigned centroids globally
# - `global_p99_distance`: approximate global 99th-percentile distance

global_stats = df_with_distance.agg(
    F.count("*").alias("total_count"),
    F.mean("distance_to_centroid").alias("global_mean_distance"),
    F.expr(
        "percentile_approx(distance_to_centroid, 0.99)"
    ).alias("global_p99_distance")
)

# Broadcast the one-row global-statistics DataFrame so it can be efficiently
# cross-joined to cluster summaries and individual observations.
global_stats = broadcast(global_stats)


# Combine cluster + global statistics -------------------------------------
print('Combine cluster + global statistics')

# Attach global summary values to every cluster summary using a cross join.
#
# Then calculate:
# - `cluster_percent`: percentage of all observations in each cluster
# - `relative_compactness`: mean within-cluster distance divided by the
#   global mean distance. Values below 1 indicate clusters that are more
#   compact than the global average; values above 1 indicate looser clusters.

cluster_diagnostics = (
    cluster_stats
    .crossJoin(global_stats)
    .withColumn(
        "cluster_percent",
        F.col("count") / F.col("total_count") * 100
    )
    .withColumn(
        "relative_compactness",
        F.col("mean_distance") / F.col("global_mean_distance")
    )
)


# Detect outliers ---------------------------------------------------------
print('Detect outliers')

# Attach the global outlier threshold to every observation and flag rows whose
# distance to their assigned centroid exceeds the global 99th-percentile
# distance threshold.
#
# `is_outlier` is a Boolean column:
# - True: observation is farther from its centroid than global_p99_distance
# - False: observation is within or equal to the global threshold

df_outliers = (
    df_with_distance
    .crossJoin(global_stats)
    .withColumn(
        "is_outlier",
        F.col("distance_to_centroid") > F.col("global_p99_distance")
    )
)

# Calculate the proportion of observations classified as outliers within
# each cluster.
#
# Boolean values are converted to double:
# - True becomes 1.0
# - False becomes 0.0
#
# The mean of these values is therefore the share/proportion of outliers
# in each cluster.

outlier_ratio = (
    df_outliers
    .groupBy("prediction")
    .agg(
        F.mean(
            F.col("is_outlier").cast("double")
        ).alias("outlier_ratio")
    )
)


# Add outlier info --------------------------------------------------------
print('Add outlier info')

# Add the per-cluster outlier ratio to the cluster diagnostics table.
# A left join ensures that all cluster-statistics rows are retained.
cluster_diagnostics = (
    cluster_diagnostics
    .join(outlier_ratio, on="prediction", how="left")
)


# Add cluster quality flags ------------------------------------------------
print('Add cluster quality flags')

# Assign a quality label to each cluster based on predefined diagnostic rules.
#
# Rules are checked in order:
# 1. `tiny_cluster`: cluster represents less than 1% of all observations.
# 2. `loose_cluster`: mean distance is more than 1.5 times the global mean.
# 3. `outlier_heavy`: more than 10% of observations are global-distance outliers.
# 4. `good`: none of the above conditions are met.
#
# Because `when()` conditions are evaluated in sequence, a tiny cluster will
# be labelled "tiny_cluster" even if it is also loose or outlier-heavy.

cluster_diagnostics = (
    cluster_diagnostics
    .withColumn(
        "quality_flag",
        F.when(
            F.col("cluster_percent") < 1,
            "tiny_cluster"
        )
        .when(
            F.col("relative_compactness") > 1.5,
            "loose_cluster"
        )
        .when(
            F.col("outlier_ratio") > 0.1,
            "outlier_heavy"
        )
        .otherwise("good")
    )
)


# Final diagnostics table ----------------------------------------------------
print('Final diagnostics table')

# Retain the final set of desired diagnostic columns and order rows by
# K-means cluster label.

cluster_diagnostics = (
    cluster_diagnostics
    .select(
        "prediction",            # K-means cluster ID
        "count",                 # Number of observations in the cluster
        "cluster_percent",       # Cluster size as a percentage of all observations
        "mean_distance",         # Mean distance to the cluster centroid
        "std_distance",          # Standard deviation of centroid distances
        "p90_distance",          # 90th percentile of centroid distances
        "p99_distance",          # 99th percentile of centroid distances
        "min_distance",          # Minimum centroid distance
        "max_distance",          # Maximum centroid distance
        "relative_compactness",  # Mean distance relative to global mean distance
        "outlier_ratio",         # Proportion of observations beyond global p99 distance
        "quality_flag"           # Rule-based cluster quality classification
    )
    .orderBy("prediction")
)

# Write the final cluster-diagnostics table as CSV file.
# - `coalesce(1)`: create one output part file; suitable for this small
#   diagnostics table but generally not recommended for very large outputs.
# - `mode("overwrite")`: replace any existing output directory.
# - `option("header", True)`: include column names in the CSV output
cluster_diagnostics.coalesce(1).write.mode("overwrite").option("header", True).csv(
    "/my_directory/data/clustering_global/l_fhc/lfhc_cluster_30_diagnostics_v1")

