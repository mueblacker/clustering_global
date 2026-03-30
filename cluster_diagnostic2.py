# Start the Pyspark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("cluster_stats").getOrCreate()


# Moduls -----------------------------------------------

from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast
from pyspark.ml.functions import vector_to_array
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml.linalg import Vectors
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans, KMeansModel
from pyspark import StorageLevel

# Load the data -------------------------------------------
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
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

model_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/kmeans_model_75_v1"
model = KMeansModel.load(model_path)

# Transform data
prediction_df = model.transform(df)


# ---------------------------------------------
# 2. Extract cluster centers
# ---------------------------------------------
print('3')

centers = [
    (i, Vectors.dense([float(x) for x in center]))
    for i, center in enumerate(model.clusterCenters())
]

centers_df = spark.createDataFrame(
    centers,
    ["prediction", "centroid"]
)

centers_df = broadcast(centers_df)


# ---------------------------------------------
# 3. Attach centroid to each row
# ---------------------------------------------
print('4')

df_with_centroid = prediction_df.join(
    centers_df,
    on="prediction",
    how="inner"
)

df_with_centroid = df_with_centroid.repartition(600)
# ---------------------------------------------
# 4. Compute distance to centroid
# ---------------------------------------------
print('5')

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

#df_with_distance = df_with_distance.persist(StorageLevel.MEMORY_AND_DISK)
# materialize cache
df_with_distance.count()


# ---------------------------------------------
# 5. Cluster statistics
# ---------------------------------------------
print('6')

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


# ---------------------------------------------
# 6. Global statistics
# ---------------------------------------------
print('7')

global_stats = df_with_distance.agg(
    F.count("*").alias("total_count"),
    F.mean("distance_to_centroid").alias("global_mean_distance"),
    F.expr(
        "percentile_approx(distance_to_centroid, 0.99)"
    ).alias("global_p99_distance")
)

global_stats = broadcast(global_stats)


# ---------------------------------------------
# 7. Combine cluster + global statistics
# ---------------------------------------------
print('8')

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


# ---------------------------------------------
# 8. Detect outliers
# ---------------------------------------------
print('9')

df_outliers = (
    df_with_distance
    .crossJoin(global_stats)
    .withColumn(
        "is_outlier",
        F.col("distance_to_centroid") > F.col("global_p99_distance")
    )
)


outlier_ratio = (
    df_outliers
    .groupBy("prediction")
    .agg(
        F.mean(
            F.col("is_outlier").cast("double")
        ).alias("outlier_ratio")
    )
)


# ---------------------------------------------
# 9. Add outlier info
# ---------------------------------------------
print('10')

cluster_diagnostics = (
    cluster_diagnostics
    .join(outlier_ratio, on="prediction", how="left")
)


# ---------------------------------------------
# 10. Add cluster quality flags
# ---------------------------------------------
print('11')

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


# ---------------------------------------------
# 11. Final diagnostics table
# ---------------------------------------------
print('12')
cluster_diagnostics = (
    cluster_diagnostics
    .select(
        "prediction",
        "count",
        "cluster_percent",
        "mean_distance",
        "std_distance",
        "p90_distance",
        "p99_distance",
        "min_distance",
        "max_distance",
        "relative_compactness",
        "outlier_ratio",
        "quality_flag"
    )
    .orderBy("prediction")
)

print('13')
(
    cluster_diagnostics
    .coalesce(1)
    .write
    .mode("overwrite")
    .option("header", True)
    .csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/cluster_diagnostics_75_v1")
)
