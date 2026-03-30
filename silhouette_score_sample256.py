# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('silhouette_score').getOrCreate()

# Load libraries
from pyspark.sql import functions as fun
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Load the data
reg_path = '/vast/palmer/scratch/sbsc/mu78/clustering_global/samples/sample_0.01_seed256_parquet'
sampled = spark.read.parquet(reg_path, header = True, inferSchema = True)
print('Loaded data')
print("Partitions:", sampled.rdd.getNumPartitions())
sampled = sampled.repartition(300)

selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()

print('Features:', columns)

# Merge multiple columns into a vector column, scale the data and run a pca
# Merge multiple columns into a vector column
assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

df = assembler.transform(sampled).select('features')


# Calculate Silhouette score
silhouette_score=[]
within_sum_of_square=[]

evaluator = ClusteringEvaluator(predictionCol = 'prediction',
                                featuresCol = 'features', 
                                metricName = 'silhouette', 
                                distanceMeasure = 'squaredEuclidean')
print('Run Silhoutte score')
k = [2, 10, 20, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 40, 50, 60, 70, 80, 90, 100]
for i in k:
    kmeans = KMeans(featuresCol = 'features', k = i).setInitSteps(100).setMaxIter(500).setSeed(256)
    model = kmeans.fit(df)
    predictions = model.transform(df)
    score = evaluator.evaluate(predictions)
    wss = model.summary.trainingCost
    silhouette_score.append(score)
    print('Silhouette Score for k =', i,'is', score)
    within_sum_of_square.append({"k": i, 'wss': wss})
    print('WSS for k =', i, 'is', wss)
 


# Create rdd list and save silhouette score
sil_list = [(k[i], silhouette_score[i]) for i in range(len(k))]
sil_df = spark.createDataFrame(sil_list, ['k', 'sil'])
wss_df = spark.createDataFrame(within_sum_of_square)
#df.write.option("header",True).csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/sil_score.csv")
sil_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/sil_0.01_seed256')
wss_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/wss_0.01_seed256')


