# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('silhouette_score').getOrCreate()

# Load libraries
from pyspark.sql import functions as fun
from pyspark.ml import Pipeline
from pyspark.ml.pipeline import PipelineModel
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Load the data
reg_path = "/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0"
selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/correlation/uncorr_envVar_world.csv', header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
print('Loaded data')
# Drop rows with NULL values
raw_data = raw_data.na.drop()
print('Dropped NULL values')
va_pca_model = PipelineModel.load('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/pca_model_32')
print('Loaded PCA model')
pca_data = va_pca_model.transform(raw_data)
print('Transformed data')

# Remove land use classes with 0% in all sub-catchments
# sums = raw_data.select(*[fun.sum(c).alias(c) for c in raw_data.columns]).first()
# cols_to_dop = [c for c in sums.asDict() if sums[c] == 0]
# raw_data = raw_data.drop(*cols_to_dop)

# Create a subset
fractions = {c.reg_id: 0.1 for c in pca_data.select('reg_id').distinct().collect()}
sampled = pca_data.sampleBy('reg_id', fractions, seed = 256)
rows = sampled.count()
print('Number of sampled subc:', rows)
print("Partitions:", sampled.rdd.getNumPartitions())
sampled = sampled.repartition(300)

sampled.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/sample_0.1_seed256_parquet')

# Merge multiple columns into a vector column, scale the data and run a pca
# Merge multiple columns into a vector column
# assembler = VectorAssembler(inputCols = columns,
#                            outputCol = 'features')

# df = assembler.transform(sampled).select('features')

# Code if the data needs to be scaled
# scaler = StandardScaler(inputCol='features', 
#                        outputCol='scaled_features', 
#                        withStd=True, 
#                        withMean=True)

#pipeline = Pipeline(stages=[assembler, scaler])
#pipeline_model = pipeline.fit(raw_data)
#scaled_data = pipeline_model.transform(raw_data).select('features',
#                                                        'scaled_features')

# print('Run PCA')
#i = 20
#var = 0.5
#while var < 0.98:
#    k = i
#    i = k + 1
#    pca = PCA(k = i, inputCol = 'features', outputCol = 'pca_features')
#    pca_model = pca.fit(df)
#    var = sum(pca_model.explainedVariance).item()


#print(pca_model.explainedVariance)
#print('PCA =', i, 'Var =', var)

#pca_data = pca_model.transform(df)


# Calculate Silhouette score
silhouette_score=[]
within_sum_of_square=[]

evaluator = ClusteringEvaluator(predictionCol = 'prediction',
                                featuresCol = 'pca_features', 
                                metricName = 'silhouette', 
                                distanceMeasure = 'squaredEuclidean')
print('Run Silhoutte score')
k = [2, 10, 20, 30, 40, 50, 60]
for i in k:
    kmeans = KMeans(featuresCol = 'pca_features', k = i).setInitSteps(100).setMaxIter(500).setSeed(256)
    model = kmeans.fit(sampled)
    predictions = model.transform(sampled)
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
sil_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/sil_0.1_seed256')
wss_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world/wss_0.1_seed256')


