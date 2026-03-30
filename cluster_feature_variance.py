# Start the Pyspark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("cluster_variance").getOrCreate()


# Moduls -----------------------------------------------

from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeansModel


# Load the data -------------------------------------------
reg_path = '/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0'
uncorr_envVar = spark.read.csv('/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/correlation/uncorr_envVar_world_085.csv', header = True, inferSchema = True)
columns = uncorr_envVar.rdd.map(lambda x: x[0]).collect()
columns.append('subc_id')
columns.append('basin_id')
columns.append('reg_id')
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(columns)

# Drop rows with NULL values
raw_data = raw_data.na.drop()


# Assemble scaled features -------------------------------
print('1')

selected_features = columns[0:len(columns)-3]
print("Selected features:")
print(selected_features)
assembler = VectorAssembler(inputCols = selected_features,
                            outputCol = 'features')

df = assembler.transform(raw_data)


#  Load saved KMeans model -----------------------------
print('2')

model_path = "/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/kmeans_model_20_v1"
model = KMeansModel.load(model_path)

# Transform data
prediction_df = model.transform(df)


#  Compute variance per cluster per feature ---------------
print('2.1')
# Group by cluster and compute variance for each feature
cluster_variance_df = prediction_df.groupBy("prediction").agg(
    *[F.variance(F.col(f)).alias(f"var_{f}") for f in selected_features]
)


# Save results for inspection -------------------------

cluster_variance_df.coalesce(1).write.mode("overwrite") \
    .option("header", True) \
    .csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/world_wo_lc/cluster_feature_variance_20_v1")


