# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('silhouette_score').getOrCreate()

# Load libraries
from pyspark.sql import functions as fun
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Load the data
# raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basin_59_1173421.csv", header = True, inferSchema = True)
raw_data = spark.read.csv('/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv', header = True, inferSchema = True)


# df_new = raw_data.select([x for x in raw_data.columns if 'mean' in x] + [x for x in raw_data.columns if 'stream' in x] + [x for x in raw_data.columns if 'land' in x]) 
# columns = df_new.columns

selected_features = spark.read.csv('/home/mueblacker/Documents/Glowabio/Data/test_data_clustering/sman_uncorr_envVar_00_000006_screening.csv', header = True, inferSchema = True)
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

pipeline = Pipeline(stages=[assembler, scaler])
pipeline_model = pipeline.fit(raw_data)
scaled_data = pipeline_model.transform(raw_data).select('subcID', 
                                                        'features',
                                                        'scaled_features')

i = 15
var = 0.5
while var < 0.98:
    k = i
    i = k + 1
    pca = PCA(k = i, inputCol = 'scaled_features', outputCol = 'pca_features')
    pca_model = pca.fit(scaled_data)
    var = sum(pca_model.explainedVariance).item()


pca_data = pca_model.transform(scaled_data)


# Calculate Silhouette score
silhouette_score=[]
within_sum_of_square=[]

evaluator = ClusteringEvaluator(predictionCol = 'prediction',
                                featuresCol = 'pca_features', 
                                metricName = 'silhouette', 
                                distanceMeasure = 'squaredEuclidean')

k = [2, 5, 10, 15, 20, 25, 30, 35, 40]
for i in k:
    kmeans=KMeans(featuresCol='pca_features', k=i).setInitSteps(10).setMaxIter(100).setSeed(256)
    model=kmeans.fit(pca_data)
    predictions=model.transform(pca_data)
    score=evaluator.evaluate(predictions)
    wss= model.summary.trainingCost
    silhouette_score.append(score)
    print('Silhouette Score for k =',i,'is',score)
    within_sum_of_square.append({"k": i, 'wss': wss})
 


# Create rdd list and save silhouette score
sil_list = [(k[i], silhouette_score[i]) for i in range(len(k))]
sil_df = spark.createDataFrame(sil_list, ['k', 'sil'])
wss_df = spark.createDataFrame(within_sum_of_square)
#df.write.option("header",True).csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/sil_score.csv")
sil_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/home/mueblacker/Documents/Glowabio/Data/test_data_clustering/sil_score')
wss_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/home/mueblacker/Documents/Glowabio/Data/test_data_clustering/wss')
