# =========================================================================
# Silhoutte score and Within-Cluster Sum of Square (WSS)
# =========================================================================


# Import SparkSession
from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder.appName('silhouette_score').getOrCreate()

# Load modules
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Define the path to the previously created sampled dataset
reg_path = '/my_directory/data/clustering_global/l_fhc/samples/sample_0.01_seed123_parquet'

# Load the sampled dataset from Parquet.
sampled = spark.read.parquet(reg_path, header = True, inferSchema = True)

# Confirm that the sampled data has been loaded
print('Loaded data')

# Print the current number of Spark partitions in the loaded DataFrame.
print("Partitions:", sampled.rdd.getNumPartitions())

# Repartition the dataset into 300 partitions to control parallelism
# during feature assembly, K-means fitting, and evaluation.
sampled = sampled.repartition(300)

# Load the CSV file containing the selected environmental feature names.
# The first column of this file is expected to contain variable/column names.
selected_features = spark.read.csv(
    '/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv',
      header = True, inferSchema = True)

# Extract values from the first column and collect them into a Python list.
# These values are used as the input feature columns for clustering.
columns = selected_features.rdd.map(lambda x: x[0]).collect()

# Print the names of the environmental features used for K-means clustering.
print('Features:', columns)

# Create a VectorAssembler object that combines all selected feature columns
# into one vector column called `features`.
# Spark ML algorithms, including KMeans, require feature values in vector form.
assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

# Apply the assembler to the sampled dataset and retain only the resulting
# vector column. Each row in `df` now contains one feature vector.
df = assembler.transform(sampled).select('features')


# Create empty Python lists to store:
# - silhouette scores for each tested number of clusters
# - within-cluster sum of squares (WSS) for each tested number of clusters
silhouette_score=[]
within_sum_of_square=[]

# Define a clustering evaluator for calculating silhouette scores.
evaluator = ClusteringEvaluator(predictionCol = 'prediction',
                                featuresCol = 'features', 
                                metricName = 'silhouette', 
                                distanceMeasure = 'squaredEuclidean')

# Print a message
print('Run Silhoutte score')

# Define the candidate numbers of clusters (k) to test.
# Each value will be used to fit a separate K-means model.
k = [2, 10, 20, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 40, 50, 60, 70, 80, 90, 100]

# Loop over every candidate value of k
for i in k:
    # Create a K-means model configuration
    kmeans = KMeans(featuresCol = 'features', k = i).setInitSteps(100).setMaxIter(500).setSeed(256)
    # Train the K-means model using the feature vectors
    model = kmeans.fit(df)
    # Assign every observation to one of the fitted clusters
    predictions = model.transform(df)
    # Calculate the silhouette score for the current clustering result
    score = evaluator.evaluate(predictions)
    # Extract the K-means training cost, also known as the within-cluster
    # sum of squared distances (WSS).
    wss = model.summary.trainingCost
    # Store the silhouette score in the order corresponding to the values in `k`
    silhouette_score.append(score)
    # Print the silhouette score for the current number of clusters
    print('Silhouette Score for k =', i,'is', score)
    # Store the current k value and its WSS result as a dictionary
    within_sum_of_square.append({"k": i, 'wss': wss})
    # Print the WSS value for the current number of clusters
    print('WSS for k =', i, 'is', wss)
 


# Create a list of tuples pairing each tested k value with its corresponding
# silhouette score. The index positions in `k` and `silhouette_score` match.
sil_list = [(k[i], silhouette_score[i]) for i in range(len(k))]

# Convert the silhouette-score results into a Spark DataFrame with columns
sil_df = spark.createDataFrame(sil_list, ['k', 'sil'])

# Convert the WSS result dictionaries into a Spark DataFrame.
# The resulting columns are `k` and `wss`.
wss_df = spark.createDataFrame(within_sum_of_square)

# Save the silhouette-score and the within-cluster sum of squares (WSS) DataFrame as a CSV file.
# - `coalesce(1)`: produce one output CSV part file
# - `mode('overwrite')`: overwrite existing results
# - `option('header', 'true')`: include column names in the output
sil_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/my_directory/data/clustering_global/l_fhc/sil_0.01_seed123')
wss_df.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/my_directory/data/clustering_global/l_fhc/wss_0.01_seed123')


