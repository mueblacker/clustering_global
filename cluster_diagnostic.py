# Start the Pyspark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("cluster_stats").getOrCreate()


# Moduls -----------------------------------------------

from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeansModel
from pyspark.ml.functions import vector_to_array, squared_distance
from pyspark.sql.types import ArrayType, DoubleType, StructType, StructField, IntegerType
from pyspark.ml.linalg import Vectors
from pyspark.sql.functions import broadcast


# Load the data -------------------------------------------
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Assemble scaled features -------------------------------
print('1')

selected_features = columns[0:len(columns)-3]
print("Selected features:")
print(selected_features)
assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

df = assembler.transform(raw_data)


#  Load saved KMeans model -----------------------------
print('2')

model_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world/kmeans_model_30_v2"
model = KMeansModel.load(model_path)

# Transform data
prediction_df = model.transform(df)


#  Compute variance per cluster per feature ---------------
print('2.1')
# Group by cluster and compute variance for each feature
cluster_variance_df = prediction_df.groupBy("prediction").agg(
    *[F.variance(F.col(f)).alias(f"var_{f}") for f in selected_features]
)


# Save results for inspection -------------------------

cluster_variance_df.coalesce(1).write.mode("overwrite") \
    .option("header", True) \
    .csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/world/cluster_feature_variance_30_v1")



# Create centroid DataFrame --------------------------
print('4')
# Extract centroids from model
centers = model.clusterCenters()

centroid_rows = [
    (i, Vectors.dense([float(x) for x in center]))
    for i, center in enumerate(model.clusterCenters())
]

schema = StructType() \
    .add("prediction", IntegerType(), False) \
    .add("centroid", "vector", False)

centroid_df = spark.createDataFrame(centroid_rows, schema)

# Join centroids to each row ----------------------------
print('5')

df_with_centroid = prediction_df.join(
    broadcast(centroid_df),
    on="prediction",
    how="inner"
)


# Compute Euclidean distance using Spark SQL ------------
print('6')

df_with_distance = df_with_centroid.withColumn(
    "distance_to_centroid",
    F.sqrt(squared_distance("features", "centroid"))
)

# Cluster-level statistics ------------------------------
print('7')

cluster_stats = (
    df_with_distance
    .groupBy("prediction")
    .agg(
        F.count("*").alias("count"),
        F.mean("distance_to_centroid").alias("mean_distance"),
        F.stddev("distance_to_centroid").alias("std_distance"),
        F.min("distance_to_centroid").alias("min_distance"),
        F.max("distance_to_centroid").alias("max_distance")
    )
)


# Global statistics -------------------------------------
print('8')

global_stats = df_with_distance.agg(
    F.count("*").alias("total_count"),
    F.mean("distance_to_centroid").alias("global_mean_distance")
)


# Final diagnostics table -------------------------------
print('9')

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
    .drop("total_count", "global_mean_distance")
    .orderBy("prediction")
)


# Save results ------------------------------------------
print('10')

cluster_diagnostics.coalesce(1) \
    .write.mode("overwrite") \
    .option("header", True) \
    .csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/world/cluster_diagnostics_30_v1")


