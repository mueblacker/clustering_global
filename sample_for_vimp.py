# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('sample').getOrCreate()


# Modules
from pyspark.sql import functions as F

# Load the data
parquet1_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world/cluster_prediction_30_v2_parquet"
parquet2_path = "/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0"
columns_csv_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world_085.csv"
output_csv_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world/sample_25K_30_for_vimp"


# Read columns names 
columns_df = spark.read.option("header", True).csv(columns_csv_path)

selected_columns = [row[0] for row in columns_df.collect()]

if "subc_id" not in selected_columns:
    selected_columns.insert(0, "subc_id")

# Read parquet
df1 = spark.read.parquet(parquet1_path).select("subc_id", "prediction")
df2 = spark.read.parquet(parquet2_path)

# Sample
TARGET = 25000

# 1) Count rows per category
counts = df1.groupBy("prediction").count()

# 2) Compute fraction per category (cap at 1.0)
fractions = counts.withColumn(
    "fraction",
    F.least(F.lit(1.0), F.lit(TARGET) / F.col("count"))
).select("prediction", "fraction")

# 3) Join + sample
df_sampled = (
    df1.join(fractions, on="prediction", how="inner")
      .withColumn("r", F.rand(seed=42))
      .filter(F.col("r") <= F.col("fraction"))
)

# Join
result = df2.join(df_sampled, "subc_id", "inner")

result = result.select(
    *selected_columns,
    "prediction"
)

# write csv
(
    result
    .coalesce(1)  # optional single output file
    .write
    .option("header", True)
    .mode("overwrite")
    .csv(output_csv_path)
)

print(f"Sample saved to: {output_csv_path}")




