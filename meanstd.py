# Load modules
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# Initialize Spark session
spark = SparkSession.builder \
    .appName("Mean and Standard Deviation Calculation") \
    .getOrCreate()

# Load your data into a Spark DataFrame
# Load the data
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
feature_columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(feature_columns)



# Calculate mean and standard deviation
stats_df = raw_data.select(
    *[F.mean(F.col(column)).alias(f"mean_{column}") for column in feature_columns] +
    [F.stddev(F.col(column)).alias(f"stddev_{column}") for column in feature_columns]
)


stats_df.coalesce(1).write.mode("overwrite").option("header", True).csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/mean_std_check")

print(stats_df)
