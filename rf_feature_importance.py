# Start spark session
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("RandomForestClassifier").getOrCreate()

# Load libraries
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, min, max



# Load the data
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/correlation/uncorr_envVar_south_america.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
# Drop rows with NULL values
raw_data = raw_data.na.drop()

# Load cluster prediction
prediction = spark.read.parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/cluster_prediction_24_parquet', header = True, inferSchema = True)

# Join DataFrames
df = prediction.join(raw_data, ['subc_id', 'basin_id', 'reg_id'])


#df = df.withColumn("prediction", df["prediction"].cast("double"))
df = df.withColumnRenamed('prediction', 'clusters')


# Merge multiple columns into a vector column

selected_features = columns[0:len(columns)-3]
print('Selected features:')
print(selected_features)


assembler = VectorAssembler(
       inputCols = selected_features,
       outputCol = 'features'
   )

df = assembler.transform(df)

# Split data into training and test data
train_data, test_data = df.randomSplit([0.8, 0.2], seed = 256)


# Random Forest
rf = RandomForestClassifier(
    featuresCol = 'features',
    labelCol = 'clusters',
    numTrees = 500,
    maxDepth = 20,
    impurity = 'gini',
    featureSubsetStrategy = 'sqrt',
    seed = 256
)

rf_model = rf.fit(train_data)
predictions = rf_model.transform(test_data)
predictions.select('features', 'clusters', 'prediction').show(5)


# Print the accuracy
evaluator = MulticlassClassificationEvaluator(labelCol = 'clusters', predictionCol = 'prediction')
accuracy = evaluator.evaluate(predictions, {evaluator.metricName: 'accuracy'})
f1_score = evaluator.evaluate(predictions, {evaluator.metricName: 'f1'})
print(f'Accuracy: {accuracy:.4f}')
print(f'F1 Score: {f1_score:.4f}')


# Feature importance
feature_importances = rf_model.featureImportances
fimp_list = [float(col) for col in  feature_importances]
fimp = list(zip(selected_features, fimp_list))
fimp_table = spark.createDataFrame(fimp, ['feature', 'importance'])

# Normalize feature importance
min_fimp, max_fimp = fimp_table.select(min('importance'), max('importance')).first()
fimp_table = fimp_table.withColumn('importance_scaled', (col('importance') - min_fimp) / (max_fimp - min_fimp))

# Save feature importance
fimp_table.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/feature_importance_24_ntree500_depth20')
for feature, importance in zip(selected_features, feature_importances):
    print(f'Feature: {feature}, Importance: {importance:.4f}')


# Save Model
rf_model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/rf_model_24_ntree500_depth20')

