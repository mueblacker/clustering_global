from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, lit

spark = SparkSession.builder.appName("cluster_size").getOrCreate()

# -----------------------------
# CONFIG
# -----------------------------
PRED1_PATH = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/cluster_prediction_75_v1_parquet"
PRED2_PATH = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/rf_prediction_75_ntree200_depth12_v1"
OUTPUT_PATH = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/cluster_size_75"

# -----------------------------
# LOAD PREDICTIONS
# -----------------------------
pred1 = spark.read.parquet(PRED1_PATH).select("prediction")
pred2 = spark.read.parquet(PRED2_PATH).select("prediction")

# -----------------------------
# CLUSTER SIZE (PARQUET 1)
# -----------------------------
cluster1 = (
    pred1.groupBy("prediction")
    .agg(count("*").alias("cluster_size_parquet1"))
)

# -----------------------------
# COMBINED DATA
# -----------------------------
combined = pred1.unionByName(pred2)

cluster12 = (
    combined.groupBy("prediction")
    .agg(count("*").alias("cluster_size_combined"))
)

# -----------------------------
# TOTAL COUNTS
# -----------------------------
total1 = pred1.count()
total12 = combined.count()

cluster1 = cluster1.withColumn(
    "proportion_parquet1",
    col("cluster_size_parquet1") / lit(total1)
)

cluster12 = cluster12.withColumn(
    "proportion_combined",
    col("cluster_size_combined") / lit(total12)
)

# -----------------------------
# FINAL TABLE
# -----------------------------
result = (
    cluster1.join(cluster12, "prediction", "outer")
    .orderBy("prediction")
)

# -----------------------------
# SAVE CSV
# -----------------------------
result.coalesce(1).write \
    .mode("overwrite") \
    .option("header", True) \
    .csv(OUTPUT_PATH)
