# Start Spark session
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("SMD_calculation").getOrCreate()

# Moduls
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeansModel

# Load Data --------------------------------------------------------

reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'

uncorr_envVar = spark.read.csv(
    '/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation/uncorr_envVar_world_085.csv',
    header=True,
    inferSchema=True
)

columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns += ['subc_id', 'basin_id', 'reg_id']

raw_data = (
    spark.read.parquet(reg_path)
    .select(columns)
    .na.drop()
)


# Assemble features -----------------------------------------------

selected_features = columns[:-3]

assembler = VectorAssembler(
    inputCols=selected_features,
    outputCol='features'
)

df = assembler.transform(raw_data)


# Load trained KMeans model ----------------------------------------

model_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/kmeans_model_75_v1"
model = KMeansModel.load(model_path)

prediction_df = model.transform(df)


# Cluster means ----------------------------------------------------

mean_df = prediction_df.groupBy("prediction").agg(
    *[F.mean(F.col(f)).alias(f"mean_{f}") for f in selected_features]
)


# Global mean and std ----------------------------------------------

global_stats = prediction_df.agg(
    *(
        [F.mean(F.col(f)).alias(f"global_mean_{f}") for f in selected_features] +
        [F.stddev(F.col(f)).alias(f"global_std_{f}") for f in selected_features]
    )
)


# Join cluster stats with global stats -----------------------------

stats_df = mean_df.crossJoin(global_stats)


# Compute SMD ------------------------------------------------------

for f in selected_features:
    stats_df = stats_df.withColumn(
        f"smd_{f}",
        F.when(
            F.col(f"global_std_{f}") != 0,
            (F.col(f"mean_{f}") - F.col(f"global_mean_{f}")) /
            F.col(f"global_std_{f}")
        ).otherwise(F.lit(0.0))
    )


# Keep only prediction + SMD columns -------------------------------

smd_cluster_wide = stats_df.select(
    ["prediction"] + [f"smd_{f}" for f in selected_features]
)

# Rename smd columns back to original feature names ----------------

for f in selected_features:
    smd_cluster_wide = smd_cluster_wide.withColumnRenamed(
        f"smd_{f}", f
    )


# Rows = Features, Columns = Cluster numbers -----------------------

# Collect cluster ids
cluster_ids = [row["prediction"] for row in smd_cluster_wide.select("prediction").collect()]

# Build transposed dataframe
exprs = [
    F.struct(
        F.lit(c).alias("cluster"),
        F.array(*[F.col(f) for f in selected_features]).alias("values")
    )
    for c in cluster_ids
]

# Convert to Pandas-like structure via stacking manually
smd_matrix = (
    smd_cluster_wide
    .groupBy()
    .pivot("prediction")
    .agg(F.first(F.array(*selected_features)))
)

# Explode arrays into rows
smd_matrix = smd_matrix.select(
    F.posexplode(F.array(*[
        F.col(str(c)) for c in cluster_ids
    ])).alias("pos", "cluster_values")
)

# Add feature names
smd_matrix = smd_matrix.withColumn(
    "Feature",
    F.array([F.lit(f) for f in selected_features])[F.col("pos")]
)

# Final reshape
for i, c in enumerate(cluster_ids):
    smd_matrix = smd_matrix.withColumn(
        str(c),
        F.col("cluster_values")[i]
    )

smd_matrix = smd_matrix.drop("pos", "cluster_values").orderBy("Feature")


# Write output --------------------------------------------------

smd_matrix.coalesce(1) \
    .write.mode("overwrite") \
    .option("header", True) \
    .csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/smd_matrix_75_v1")
