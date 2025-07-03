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
# raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basin_59_1173421.csv", header = True, inferSchema = True)
# raw_data = spark.read.csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv", header = True, inferSchema = True)
raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basins.csv", header = True, inferSchema = True)

selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/test_data/sman_uncorr_envVar_00_000006_screening.csv', header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()

# Remove land use classes with 0% in all sub-catchments
# sums = raw_data.select(*[fun.sum(c).alias(c) for c in raw_data.columns]).first()
# cols_to_dop = [c for c in sums.asDict() if sums[c] == 0]
# raw_data = raw_data.drop(*cols_to_dop)

# Create a subset
# raw_data = raw_data.sample(fraction=0.1)


# Merge multiple columns into a vector column, scale the data and run a pca
assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

scaler = StandardScaler(inputCol = 'features', 
                        outputCol = 'scaled_features', 
                        withStd = True, 
                        withMean = True)

pca = PCA(k = 28, 
          inputCol = 'scaled_features', 
          outputCol = 'pca_features')

pipeline = Pipeline(stages=[assembler, scaler, pca])
pipeline_model = pipeline.fit(raw_data)
pipeline_model.transform(raw_data)

pca_data = pipeline_model.transform(raw_data).select('subcID', 
                                                     'features', 
                                                     'scaled_features', 
                                                     'pca_features')



# Trains a k-means model.
kmeans = KMeans(featuresCol = 'scaledFeatures', k = 30).setInitSteps(100).setMaxIter(500).setSeed(256)
model = kmeans.fit(pca_data)
predictions = model.transform(pca_data)
clusters = predictions.select('subcID', 'prediction')
# Save clusters as csv
clusters.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/test_data/cluster_prediction')
# Save kmeans model
model.save('/vast/palmer/scratch/sbsc/mu78/test_data/kmeans_model')


spark.stop()


