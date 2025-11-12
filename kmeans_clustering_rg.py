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
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/amazon/correlation/uncorr_envVar_amazon.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')

raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Create a subset
# raw_data = raw_data.sample(fraction=0.1)


# Merge multiple columns into a vector column, scale the data and run a pca

selected_features = columns[0:len(columns)-1]
print("Selected features:")
print(selected_features)


assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

#scaler = StandardScaler(inputCol = 'features', 
#                        outputCol = 'scaled_features', 
#                        withStd = True, 
#                        withMean = True)

pca = PCA(k = 20, 
          inputCol = 'features', 
          outputCol = 'pca_features')

pipeline = Pipeline(stages=[assembler, pca])
pipeline_model = pipeline.fit(raw_data)
pipeline_model.transform(raw_data)

pca_data = pipeline_model.transform(raw_data).select('subc_id',
                                                     'features', 
                                                     'pca_features')



# Trains a k-means model.
kmeans = KMeans(featuresCol = 'features', k = 17).setInitSteps(100).setMaxIter(500).setSeed(256)
model = kmeans.fit(pca_data)
predictions = model.transform(pca_data)
clusters = predictions.select('subc_id', 'prediction')
# Save clusters as csv
clusters.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/amazon/cluster_prediction_17')
# Save parquet partition file
# clusters.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/amazon/cluster_prediction_parquet')
# Save kmeans model
model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/amazon/kmeans_model_17')




