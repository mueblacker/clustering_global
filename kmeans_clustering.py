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
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')

raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Create a subset
# raw_data = raw_data.sample(fraction=0.1)


# Merge multiple columns into a vector column, scale the data and run a pca

selected_features = columns[0:len(columns)-3]
print("Selected features:")
print(selected_features)
assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

#scaler = StandardScaler(inputCol = 'features', 
#                        outputCol = 'scaled_features', 
#                        withStd = True, 
#                        withMean = True)

pca = PCA(k = 32, 
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
# Save pipeline
pipeline_model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/pca_model_32')


print("Finished PCA")
# Trains a k-means model.
kmeans = KMeans(featuresCol = 'features', k = 30).setInitSteps(100).setMaxIter(500).setSeed(256)
model = kmeans.fit(pca_data)

print("Finished clustering")

# Save kmeans model
model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/kmeans_model_30')

# Prediction
predictions = model.transform(pca_data)
clusters = predictions.select('reg_id', 'basin_id' ,'subc_id', 'prediction')
print("Finished prediction")

# Save clusters as csv
# clusters.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/america/cluster_prediction_26')
# Save kmeans model
# model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/america/kmeans_model_26')
# Save parquet partition file
clusters.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/cluster_prediction_30_parquet')





