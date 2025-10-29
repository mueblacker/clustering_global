# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('clustering').getOrCreate()

# Load libraries
from pyspark.sql import functions as fun
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Load the data
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0/reg_id=178'
selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/reg_id_178/correlation/uncorr_envVar.csv', header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()
columns_to_load = columns.append('subc_id', 'basin_id')

raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns_to_load)
# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Create a subset
# raw_data = raw_data.sample(fraction=0.1)


# Merge multiple columns into a vector column, scale the data and run a pca
assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

#scaler = StandardScaler(inputCol = 'features', 
#                        outputCol = 'scaled_features', 
#                        withStd = True, 
#                        withMean = True)

pca = PCA(k = 22, 
          inputCol = 'features', 
          outputCol = 'pca_features')

pipeline = Pipeline(stages=[assembler, pca])
pipeline_model = pipeline.fit(raw_data)
pipeline_model.transform(raw_data)

pca_data = pipeline_model.transform(raw_data).select('reg_id',
						       'basin_id',
						       'subc_id',
                                                     'features', 
                                                     'pca_features')



# Trains a k-means model.
kmeans = KMeans(featuresCol = 'features', k = 26).setInitSteps(100).setMaxIter(500).setSeed(256)
model = kmeans.fit(pca_data)
predictions = model.transform(pca_data)
clusters = predictions.select('reg_id', 'basin_id' ,'subc_id', 'prediction')
# Save clusters as csv
# clusters.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/reg_id_178/cluster_prediction')
# Save parquet partition file
clusters.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america/cluster_prediction')
# Save kmeans model
model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america/kmeans_model')


spark.stop()


