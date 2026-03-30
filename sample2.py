# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('sample').getOrCreate()

# Load libraries
#from pyspark.ml import Pipeline
#from pyspark.ml.pipeline import PipelineModel
#from pyspark.ml.feature import VectorAssembler, PCA


# Load the data
reg_path = "/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0"
selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
print('Loaded data')
# Drop rows with NULL values
raw_data = raw_data.na.drop()
print('Dropped NULL values')
#va_pca_model = PipelineModel.load('/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/pca_model')
#print('Loaded PCA model')
#pca_data = va_pca_model.transform(raw_data)
#print('Transformed data')


# Create a subset
fractions = {c.reg_id: 0.01 for c in raw_data.select('reg_id').distinct().collect()}
sampled = raw_data.sampleBy('reg_id', fractions, seed = 3)
rows = sampled.count()
print('Number of sampled subc:', rows)
sampled = sampled.repartition(300)

# Save subset
sampled.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/samples/sample_0.01_seed3_parquet')



