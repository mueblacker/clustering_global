# =========================================================================
# Stratified sampling by regional unit
# =========================================================================

# Load modules
from pyspark.sql import SparkSession

# Start the PySpark server
spark = SparkSession.builder.appName('sample').getOrCreate()


# Define the path of the regional-unit Parquet dataset with the environmental variables
reg_path = '/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'

# Read a CSV file containing the names of environmental variables/features
# selected after correlation filtering.
selected_features = spark.read.csv('/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv', 
                                   header = True, inferSchema = True)

# Extract values from the first column of `selected_features` and collect
# them into a Python list. These values are expected to be feature names
columns = selected_features.rdd.map(lambda x: x[0]).collect()

# Add identifier columns that should be included in the data
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')

# Read the full regional dataset from Parquet format and select only
# the previously chosen environmental features plus identifier columns.
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Confirm that the data has been loaded
print('Loaded data')

# Remove every row containing at least one NULL value in any selected column
raw_data = raw_data.na.drop()

# Confirm that rows with missing values have been removed
print('Dropped NULL values')


# Build a sampling-fraction dictionary for stratified sampling by `reg_id`.
# Each distinct region is assigned a sampling fraction of 0.01 (1%).
fractions = {c.reg_id: 0.01 for c in raw_data.select('reg_id').distinct().collect()}

# Draw a stratified sample from `raw_data` using `reg_id` as the stratum.
# Approximately 1% of records from each region are sampled.
# The seed ensures that the random sample can be reproduced.
sampled = raw_data.sampleBy('reg_id', fractions, seed = 123)

# Count the number of rows in the sampled dataset
rows = sampled.count()
print('Number of sampled subc:', rows)

# Repartition the sampled DataFrame into 300 partitions
# This can improve parallelism and control the number of output files
# when writing the data.
sampled = sampled.repartition(300)

# Save the sampled data as Parquet files
# The output is partitioned into directories based on `reg_id`.
# Warning: `mode('overwrite')` replaces any existing data at the output location.
sampled.write.partitionBy('reg_id').mode('overwrite').parquet('/my_directory/data/clustering_global/l_fhc/samples/sample_0.01_seed123_parquet')



