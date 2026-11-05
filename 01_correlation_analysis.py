# =========================================================================
# Pearson correlation analysis
# =========================================================================


# Load Modules 
from pyspark.ml.stat import Correlation
from pyspark.ml.linalg import Vectors
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler
from pyspark.sql.functions import col, isnan, when, count
from pyspark.sql import functions as fun

# Create a Spark session
spark = SparkSession.builder.appName("Correlation").getOrCreate()

# Load the data
# Define path to the standardized environmental data
reg_path = '/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
# Define variables
env_var = ['bio1', 'bio2', 'bio3', 'bio4', 'bio5', 'bio6', 'bio7', 'bio8',
           'bio9', 'bio10', 'bio11', 'bio12', 'bio13', 'bio14', 'bio15', 'bio16', 
           'bio17', 'bio18', 'bio19', 'elev', 'flowpos', 'spi', 'sti', 'cti',
           'sinusoid', 'cum_length', 'out_dist', 'gradient', 'flow_ltm',
	       'c10', 'c20', 'c30', 'c40', 'c50', 'c60', 'c70', 'c80', 'c90', 'c100', 
           'c110', 'c120', 'c130', 'c140', 'c150', 'c160', 'c170', 'c180', 
           'c190', 'c200', 'c210', 'c220'] 
# Read parquet dataset
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(env_var)

# Total number of sub-catchments
print("Number of sub-catchments:")
print(raw_data.count())

# Number of data partitions 
print("Partitions:")
print(raw_data.rdd.getNumPartitions())

# Remove columns where the standard diviaton is zero
sums = raw_data.select(*[fun.stddev(c).alias(c) for c in raw_data.columns]).first()
cols_to_drop = [c for c in sums.asDict() if sums[c] == 0]
raw_data = raw_data.drop(*cols_to_drop)
print("Removed columns with stddev == 0:")
print(cols_to_drop)


# Print columns with NaN or NULL values
na_counts = raw_data.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) for c in raw_data.columns]).first()
cols_to_drop = [c for c in na_counts.asDict() if na_counts[c] > 0]
# raw_data = raw_data.drop(*cols_to_drop)
print("Columns with NaN or NULL values:")
print(cols_to_drop)

# Remove sub-catchments (rows) with NaN or NULL values
print("Remaining number of sub-catchment after removing rows with NaN or NULL values:")
print(raw_data.na.drop().count())
raw_data = raw_data.na.drop()

# Get column names
columns = raw_data.columns

# Merge multiple columns into a vector column
assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

df = assembler.transform(raw_data).select('features')

# Code if the data is not standardized and needs to be scaled
# scaler = StandardScaler(inputCol='features', 
#                        outputCol='scaled_features', 
#                        withStd=True, 
#                        withMean=True)

# pipeline = Pipeline(stages=[assembler, scaler])
# pipeline_model = pipeline.fit(raw_data)
# scaled_data = pipeline_model.transform(raw_data).select('features',
#                                                         'scaled_features')

# df = df.cache()

# Correlation analysis
# Method can be changed to 'spearman', but it does take a lot of resources
corr = Correlation.corr(df, 'features', method='pearson').head()
rows = corr[0].toArray().tolist()
corr_df = spark.createDataFrame(rows, columns)

# Bring columns together and write them into a singel csv
# Warrning: Make sure that you define a new folder directory
# Existing folder directories will be overwritten!
corr_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/my_directory/data/clustering_global/l_fhc/correlation')

