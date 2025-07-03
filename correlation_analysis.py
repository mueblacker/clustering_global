from pyspark.ml.stat import Correlation
from pyspark.ml.linalg import Vectors
from pyspark.sql import SparkSession
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, StandardScaler

# Create a Spark session
spark = SparkSession.builder.appName("Correlation").getOrCreate()

# Load the data
# raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basin_59_1173421.csv", header = True, inferSchema = True)
raw_data = spark.read.csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv", header = True, inferSchema = True)
raw_data = raw_data.select([x for x in raw_data.columns if 'mean' in x] + [x for x in raw_data.columns if 'stream' in x] + [x for x in raw_data.columns if 'land' in x])

columns = raw_data.columns

# Merge multiple columns into a vector column, scale the data and run a pca
assembler = VectorAssembler(inputCols = columns,
                            outputCol='features')

scaler = StandardScaler(inputCol='features', 
                        outputCol='scaled_features', 
                        withStd=True, 
                        withMean=True)

pipeline = Pipeline(stages=[assembler, scaler])
pipeline_model = pipeline.fit(raw_data)
scaled_data = pipeline_model.transform(raw_data).select('features',
                                                        'scaled_features')

scaled_data.cach()

corr = Correlation.corr(scaled_data, 'scaled_features', method='pearson').collect()[0[0]]

print(str(spearmanCorr).replace('nan', 'NaN'))

def correlation_df(df, target_var, feature_cols, method):
    target_var = [target_var]
    feature_cols = feature_cols
    df_cor = df.select(target_var+feature_cols)
    assembler = VectorAssembler(inputCols=target_var+feature_cols, outputCol="features")
    df_cor = assembler.transform(df_cor)
    correlation_matrix = Correlation.corr(df_cor, "features", method=method).head()
    target_corr_list = [correlation_matrix[0][i, 0] for i in range(len(feature_cols)+1)][1:]
    correlation_data = [(feature_cols[i], float(target_corr_list[i])) for i in range(len(feature_cols))]
    correlation_df = spark.createDataFrame(correlation_data, ["feature", "correlation"])
    correlation_df = correlation_df.withColumn("abs_correlation", abs("correlation"))
    return correlation_df

correlation_df(raw_data, 'topo_elev_mean', columns[1:], 'pearson')