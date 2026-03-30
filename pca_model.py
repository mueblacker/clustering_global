# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('pca').getOrCreate()

# Load libraries
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, PCA


# Load the data
reg_path = "/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0"
selected_features = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation/uncorr_envVar_world_085.csv', 
                                   header = True, inferSchema = True)
columns = selected_features.rdd.map(lambda x: x[0]).collect()

raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)
# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Remove land use classes with 0% in all sub-catchments
# sums = raw_data.select(*[fun.sum(c).alias(c) for c in raw_data.columns]).first()
# cols_to_dop = [c for c in sums.asDict() if sums[c] == 0]
# raw_data = raw_data.drop(*cols_to_dop)


# Merge multiple columns into a vector column and run a pca
# Merge multiple columns into a vector column

print("Selected features:")
print(columns)

assembler = VectorAssembler(inputCols = columns,
                            outputCol = 'features')

df = assembler.transform(raw_data).select('features')


# Find the k which explains 0.98% of the data
i = 10
var = 0.5
while var < 0.98:
    k = i
    i = k + 1
    pca = PCA(k = i, inputCol = 'features', outputCol = 'pca_features')
    pca_model = pca.fit(df)
    var = sum(pca_model.explainedVariance).item()


print('PCA =', i, 'Var =', var)


pipeline = Pipeline(stages=[assembler, pca])
pipeline_model = pipeline.fit(raw_data)

# Save pipeline
pipeline_model.save('/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/pca_model')
