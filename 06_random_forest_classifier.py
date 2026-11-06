# =========================================================================
# Random Forest cluster prediction of sub-catchment with NA values
# for the variables spi, cti, sti, flow_ltm
# =========================================================================

# Import SparkSession
from pyspark.sql import SparkSession


# Create a new Spark session
spark = pyspark.sql.SparkSession.builder.appName("RandomForestClassifier").getOrCreate()

# Load modules
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, min, max



# Define path to the full standardized environmental dataset
reg_path = '/my_directory/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'

# Load a CSV file containing the environmental variables selected after
# correlation filtering. The first column is expected to contain feature names
uncorr_envVar = spark.read.csv('/my_directory/data/clustering_global/l_fhc/correlation/uncorr_envVar_lfhc_085.csv', header = True, inferSchema = True)

# Extract the feature names from the first column and collect them as
# a Python list.
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()

# Add identifier columns
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Identify sub-catchments that contain missing values in any of the four
# specified variables. These records will later receive cluster predictions
# from the trained Random Forest model.
subc_to_predict = raw_data.where(
    (raw_data['spi'].isNull()) |
    (raw_data['cti'].isNull()) |
    (raw_data['sti'].isNull()) |
    (raw_data['flow_ltm'].isNull()))


# Remove all records containing NULL values in any selected column.
# The remaining complete cases are used to train and evaluate the classifier.
raw_data = raw_data.na.drop()

# Define the columns that have missing values for some subcatchments and
# should therefore not be used as input features in the Random Forest model.
to_remove = ['spi', 'cti', 'sti', 'flow_ltm']

# Create a list of retained columns by excluding the variables in `to_remove`.
# This list still includes the three identifier columns.
clean_cols = [c for c in columns if c not in to_remove]

# Keep only the retained variables and identifier columns in the complete dataset.
raw_data = raw_data.select(clean_cols)

# Apply the same column selection to the records with missing values.
subc_to_predict = subc_to_predict.select(clean_cols)

# Load the previously generated K-means cluster prediction
prediction = spark.read.parquet('/my_directory/data/clustering_global/l_fhc/lfhc_cluster_prediction_30_v1_parquet', header = True, inferSchema = True)

# Join the K-means cluster assignments with the complete environmental data.
# The join uses the spatial identifiers so each training record has:
# - environmental predictor variables
# - a cluster label from K-means
df = prediction.join(raw_data, ['subc_id', 'basin_id', 'reg_id'])

# Confirm that source data have been successfully loaded and joined
print('Loaded and joined datasets')

# Rename the K-means `prediction` column to `clusters`.
# This makes it clear that this value is the target class label for
# Random Forest training, rather than a Random Forest prediction.
df = df.withColumnRenamed('prediction', 'clusters')

# Create a dictionary defining stratified sample fractions for each cluster.
# Each distinct cluster is sampled at a rate of 5%.
fractions = {c.clusters: 0.05 for c in df.select('clusters').distinct().collect()}

# Draw a stratified sample from the labelled dataset.
# `sampleBy()` attempts to preserve the cluster distribution by sampling
# approximately 5% of observations within each cluster.
sampled = df.sampleBy('clusters', fractions, seed = 42)
sampled = sampled.repartition(300)

# Confirm that the stratified sample has been created.
print('Sampled data')

# Select environmental features used by the Random Forest classifier
selected_features = clean_cols[0:len(clean_cols)-3]

# Print the selected predictor variables.
print('Selected features:')
print(selected_features)

# Create a VectorAssembler that merges all selected environmental variables
# into a single vector column named `features`.
assembler = VectorAssembler(
       inputCols = selected_features,
       outputCol = 'features'
   )

# Add the assembled feature vector to the sampled, labelled training data.
sampled = assembler.transform(sampled)

# Add the same feature vector to records that had missing values in the
# removed variables and therefore need cluster predictions.
subc_to_predict = assembler.transform(subc_to_predict)

# Confirm that feature-vector creation has finished.
print('Vectorized')

# Randomly split the labelled sample into:
# - 80% training data, used to fit the Random Forest
# - 20% test data, used to evaluate model performance
train_data, test_data = sampled.randomSplit([0.8, 0.2], seed = 42)

# Cache the training data in memory/disk because it is used repeatedly
# during Random Forest fitting and row counting.
train_data = train_data.cache()
# Count the training records. This also materializes the cached DataFrame.
rows = train_data.count()

# Print the number of rows available for model training.
print('Number of rows for training:', rows)

# Configure a Random Forest classifier to reproduce the K-means cluster labels.
rf = RandomForestClassifier(
    featuresCol = 'features',
    labelCol = 'clusters',
    numTrees = 200,
    maxDepth = 12,
    impurity = 'gini',
    featureSubsetStrategy = 'sqrt',
    seed = 256
)

# Train the Random Forest classifier using the labelled training dataset.
rf_model = rf.fit(train_data)

# Apply the trained model to the held-out test dataset.
# The output contains predicted cluster labels, class probabilities,
# and other Random Forest prediction fields.
predictions = rf_model.transform(test_data)

# Optional inspection of selected prediction results
#predictions.select('features', 'clusters', 'prediction').show(5)


# Create a multiclass evaluator that compares actual K-means cluster labels
# (`clusters`) with Random Forest-predicted cluster labels (`prediction`).
evaluator = MulticlassClassificationEvaluator(labelCol = 'clusters', 
                                              predictionCol = 'prediction')

# Calculate classification accuracy: the proportion of test records for which
# the Random Forest predicted the same cluster as the K-means assignment.
accuracy = evaluator.evaluate(predictions, {evaluator.metricName: 'accuracy'})

# Calculate the weighted F1 score, which balances precision and recall
# across the multiple cluster classes.
f1_score = evaluator.evaluate(predictions, {evaluator.metricName: 'f1'})

# Print model-performance metrics 
print(f'Accuracy: {accuracy:.4f}')
print(f'F1 Score: {f1_score:.4f}')

# Apply the trained Random Forest model to sub-catchments that originally
# had NULL values in `spi`, `cti`, `sti`, or `flow_ltm`.
predictions = rf_model.transform(subc_to_predict)

# Retain spatial identifiers, the predicted cluster label, and the vector
# of class probabilities for each predicted sub-catchment.
out = predictions.select('reg_id', 'subc_id', 'basin_id', 'prediction', 'probability')

# Save Random Forest cluster predictions for sub-catchments with missing values.
out.write.partitionBy('reg_id').mode('overwrite').parquet('/my_directory/data/clustering_global/l_fhc/lfhc_rf_prediction_30_ntree200_depth12_v1')

# Obtain feature-importance scores from the fitted Random Forest model.
# Spark calculates importance based on the total contribution of each feature
# to impurity reduction across all trees.
feature_importances = rf_model.featureImportances

# Convert Spark's feature-importance vector to a standard Python list
fimp_list = [float(col) for col in  feature_importances]

# Pair each selected feature name with its corresponding importance value
fimp = list(zip(selected_features, fimp_list))

# Convert the feature-importance pairs to a Spark DataFrame
fimp_table = spark.createDataFrame(fimp, ['feature', 'importance'])

# Find the minimum and maximum raw feature-importance values
min_fimp, max_fimp = fimp_table.select(min('importance'), max('importance')).first()

# Normalize importance scores to the range from 0 to 1 using min-max scaling:
# scaled importance = (importance - minimum) / (maximum - minimum)
fimp_table = fimp_table.withColumn('importance_scaled', 
                                   (col('importance') - min_fimp) / (max_fimp - min_fimp))

# Save the feature-importance table as a CSV file.
# - `coalesce(1)`: produce one output CSV part file
# - `mode('overwrite')`: overwrite existing results
# - `option('header', 'true')`: include column names in the output
fimp_table.coalesce(1).write.mode('overwrite').option('header', 'true').csv(
    '/my_directory/data/clustering_global/l_fhc/lfhc_feature_importance_30_ntree200_depth12_v1')

# Print the raw importance score of every selected feature.
# The score is formatted to four decimal places.
for feature, importance in zip(selected_features, feature_importances):
    print(f'Feature: {feature}, Importance: {importance:.4f}')


# Save the trained Random Forest model
rf_model.save('/my_directory/data/clustering_global/l_fhc/lfhc_rf_model_30_ntree200_depth12_v1')


