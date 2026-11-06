# =========================================================================
# K-means|| clustering
# =========================================================================


# Import SparkSession
from pyspark.sql import SparkSession

# Create a Spark session
spark = SparkSession.builder.appName('clustering').getOrCreate()

# Load modules
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator


# Define path to the full standardized environmental dataset
reg_path = '/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'

# Load a CSV file containing the environmental variables selected after
# correlation filtering. The first column is expected to contain feature names.
uncorr_envVar = spark.read.csv('/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv', 
                               header = True, inferSchema = True)

# Extract the feature names from the first column and collect them as
# a Python list.
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()

# Add identifier columns
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')

# Read the standardized regional data from Parquet format and retain only
# the selected environmental variables and identifier columns.
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Remove all rows that contain one or more NULL values in the selected columns.
# This ensures that K-means receives complete numeric feature vectors.
raw_data = raw_data.na.drop()


# Select only the environmental variables for clustering
selected_features = columns[0:len(columns)-3]

# Print the list of environmental features included in the clustering process
print("Selected features:")
print(selected_features)

# Create a VectorAssembler that combines all selected feature columns into
# one vector column named `features`.
# Spark ML K-means requires input data in this vector format.
assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

# Apply the assembler to the raw data.
# Keep the regional, basin, and subcatchment identifiers so that cluster
# assignments can later be linked back to their original spatial units.
# The `features` column contains the combined vector used by K-means.
df = assembler.transform(raw_data).select('reg_id',
                                          'basin_id',
                                          'subc_id',
                                          'features')



# Configure a K-means clustering model.
kmeans = KMeans(featuresCol = 'features', k = 30).setInitSteps(100).setMaxIter(500).setSeed(256)

# Fit/train the K-means model using all feature vectors in `df`.
model = kmeans.fit(df)

# Print a message
print("Finished clustering")

# Save the fitted K-means model to disk.
# The saved model can later be reloaded and used to assign clusters to
# new data without retraining.
model.save('/my_directory/data/clustering_global/l_fhc/lfhc_kmeans_model_30_v1')

# Apply the fitted K-means model to the data.
# This creates a `prediction` column containing the assigned cluster number
# for each sub-catchment.
predictions = model.transform(df)

# Select only identifying information and the predicted cluster assignment.
# The feature vector is excluded from the final cluster-output dataset.
clusters = predictions.select('reg_id', 'basin_id' ,'subc_id', 'prediction')

# Print a message
print("Finished prediction")


# Save the cluster assignments in Parquet format.
# - `partitionBy('reg_id')`: organize output into separate folders by region.
# - `mode('overwrite')`: will overwrite any existing output at this location.
clusters.write.partitionBy('reg_id').mode('overwrite').parquet('/my_directory/data/clustering_global/l_fhc/lfhc_cluster_prediction_30_v1_parquet')





