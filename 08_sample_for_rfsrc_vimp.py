# =========================================================================
# Take a balanced sample per cluster to estimate variable importance (vimp)
# with the classification random forest of the R package `randomForestSRC`
# =========================================================================


# Import SparkSession
from pyspark.sql import SparkSession

# Create a Spark session
spark = SparkSession.builder.appName('sample').getOrCreate()


# Import PySpark SQL functions with the alias `F`
from pyspark.sql import functions as F

# Define the path to the Parquet dataset containing K-means cluster assignments
parquet1_path = "/my_directory/data/clustering_global/l_lfhc/lfhc_cluster_prediction_30_v1_parquet"
# Define the path to the full standardized regional environmental dataset
parquet2_path = "/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0"
# Define the path to the CSV file containing the selected environmental-variable names
columns_csv_path = "/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv"
# Define the output directory where the sampled dataset will be written as CSV
output_csv_path = "/my_directory/data/clustering_global/l_fhc/lfhc_cluster_30_25K_sample_for_vimp_rfsrc"



# Read the CSV file containing the names of selected environmental variables after
# correlation filtering
columns_df = spark.read.option("header", True).csv(columns_csv_path)

# Extract values from the first column of the CSV file and collect them into
# a Python list. These values are assumed to be the selected feature names.
selected_columns = [row[0] for row in columns_df.collect()]

# Insert  the sub-catchment identifier  at the beginning of the column list 
# if it is not already present.
if "subc_id" not in selected_columns:
    selected_columns.insert(0, "subc_id")

# Read the K-means cluster-prediction dataset
df1 = spark.read.parquet(parquet1_path).select("subc_id", "prediction")

# Read the full standardized environmental dataset
df2 = spark.read.parquet(parquet2_path)

# Define the desired approximate maximum sample size for each cluster/category.
# The code attempts to sample up to 25,000 sub-catchments per cluster.
TARGET = 25000

# 1) Count rows per category
# Group the cluster-assignment DataFrame by cluster ID and count
# the number of sub-catchments assigned to each cluster.
counts = df1.groupBy("prediction").count()

# 2) Compute fraction per category (cap at 1.0)
# Calculate a sampling fraction separately for each cluster.
# The intended fraction is TARGET / count:
# - If a cluster contains more than 25,000 records, only a fraction is sampled.
# - If a cluster contains 25,000 or fewer records, the fraction is capped at 1.0,
#   so all records in that cluster can be retained.
fractions = counts.withColumn(
    "fraction",
    F.least(F.lit(1.0), F.lit(TARGET) / F.col("count"))
).select("prediction", "fraction")



# 3) Join + sample
# Join each subcatchment cluster assignment with the sampling fraction
# corresponding to its cluster.
#
# Generate a reproducible random value between 0 and 1 for every row using
# seed 42, then retain the row when its random value is less than or equal
# to the fraction assigned to that cluster.
#
# This produces an approximately balanced sample containing up to roughly
# 25,000 observations per cluster. The exact count may vary because the
# selection is random.

df_sampled = (
    df1.join(fractions, on="prediction", how="inner")
      .withColumn("r", F.rand(seed=42))
      .filter(F.col("r") <= F.col("fraction"))
)

# Join the sampled sub-catchments and their cluster assignments (`df_sampled`)
# with the full environmental dataset (`df2`) using `subc_id`.
#
# `how="inner"` retains only records that occur in both datasets.
# The resulting DataFrame contains selected sampled sub-catchments, their
# environmental data, and their K-means cluster assignments.
result = df2.join(df_sampled, "subc_id", "inner")

# Select the requested environmental variables plus the cluster assignment.
# `*selected_columns` expands the Python list into individual column arguments.
# The final `prediction` column is the K-means cluster label.
result = result.select(
    *selected_columns,
    "prediction"
)

# Write the sampled data as a CSV file
# - `coalesce(1)`: combine all output partitions into one CSV part file.
#   This is useful for small-to-medium outputs but can reduce write performance
#   for large datasets.
# - `option("header", True)`: include column names in the CSV output.
# - `mode("overwrite")`: replace any data already present at the output path.
result.coalesce(1).write.option("header", True).mode("overwrite").csv(output_csv_path)

# Print the path of the output folder
print(f"Sample saved to: {output_csv_path}")




