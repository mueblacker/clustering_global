# Start spark session
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("RandomForestClassifier").getOrCreate()

# Load libraries
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.sql.functions import col, min, max



# Load the data for prediction
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/correlation/uncorr_envVar_south_america.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')

# List of countries you want to read
rus_to_load = ["35", "42", "34", "175", "41", "48", "176", "179", "178", "33", "47", "40", "39", "177", "32", "26", "27"]


raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns).filter(col("reg_id").isin(rus_to_load))


# Subc with NULL values
subc_to_predict = raw_data.where(
    (raw_data['spi'].isNull()) |
    (raw_data['cti'].isNull()) |
    (raw_data['sti'].isNull()))


# Drop rows with NULL
raw_data = raw_data.na.drop()

# Columns to remove
to_remove = [ 'spi', 'sti', 'cti']
clean_cols = [c for c in columns if c not in to_remove]

raw_data = raw_data.select(clean_cols)
subc_to_predict = subc_to_predict.select(clean_cols)

# Load cluster prediction
prediction = spark.read.parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/cluster_prediction_24_parquet', header = True, inferSchema = True)

# Join DataFrames
df = prediction.join(raw_data, ['subc_id', 'basin_id', 'reg_id'])

print('Loaded and joined datasets')

#df = df.withColumn("prediction", df["prediction"].cast("double"))
df = df.withColumnRenamed('prediction', 'clusters')

fractions = {c.clusters: 0.1 for c in df.select('clusters').distinct().collect()}
sampled = df.sampleBy('clusters', fractions, seed = 42)
sampled = sampled.repartition(300)

print('Sampled data')

# Merge multiple columns into a vector column

selected_features = clean_cols[0:len(clean_cols)-3]
print('Selected features:')
print(selected_features)


assembler = VectorAssembler(
       inputCols = selected_features,
       outputCol = 'features'
   )

sampled = assembler.transform(sampled)
subc_to_predict = assembler.transform(subc_to_predict)

print('Vectorized')

# Split data into training and test data
train_data, test_data = sampled.randomSplit([0.8, 0.2], seed = 42)

train_data = train_data.cache()
rows = train_data.count()

print('Number of rows for training:', rows)

# Random Forest
rf = RandomForestClassifier(
    featuresCol = 'features',
    labelCol = 'clusters',
    numTrees = 200,
    maxDepth = 12,
    impurity = 'gini',
    featureSubsetStrategy = 'sqrt',
    seed = 256
)

rf_model = rf.fit(train_data)
predictions = rf_model.transform(test_data)
#predictions.select('features', 'clusters', 'prediction').show(5)


# Print the accuracy
evaluator = MulticlassClassificationEvaluator(labelCol = 'clusters', predictionCol = 'prediction')
accuracy = evaluator.evaluate(predictions, {evaluator.metricName: 'accuracy'})
f1_score = evaluator.evaluate(predictions, {evaluator.metricName: 'f1'})
print(f'Accuracy: {accuracy:.4f}')
print(f'F1 Score: {f1_score:.4f}')

# Predict cluster for subc with NULL values
predictions = rf_model.transform(subc_to_predict)
out = predictions.select('reg_id', 'subc_id', 'basin_id', 'prediction', 'probability')

# Save prediction
out.write.partitionBy('reg_id').mode('overwrite').parquet('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/rf_prediction_24_ntree200_depth12')

# Feature importance
feature_importances = rf_model.featureImportances
fimp_list = [float(col) for col in  feature_importances]
fimp = list(zip(selected_features, fimp_list))
fimp_table = spark.createDataFrame(fimp, ['feature', 'importance'])

# Normalize feature importance
min_fimp, max_fimp = fimp_table.select(min('importance'), max('importance')).first()
fimp_table = fimp_table.withColumn('importance_scaled', (col('importance') - min_fimp) / (max_fimp - min_fimp))

# Save feature importance
fimp_table.coalesce(1).write.mode('overwrite').option('header', 'true').csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k//feature_importance_24_ntree200_depth12_wnv')
for feature, importance in zip(selected_features, feature_importances):
    print(f'Feature: {feature}, Importance: {importance:.4f}')



# Save Model
rf_model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/south_america_wo_flo1k/rf_model_24_ntree200_depth12_wnv')


