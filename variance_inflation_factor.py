# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('vif_calculation').getOrCreate()

# Load libraries
from pyspark import SparkFiles
from pyspark.sql import functions as fun
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.sql.functions import col, isnan, when, count

# Function to calculate vif
def calculate_vif(data, features, vif_threshold=10):
    """
    Calculate Variance Inflation Factor (VIF) for the defined variables
    and eliminate variables iteratively based on VIF threshold.

    :param data: A PySpark DataFrame containing the predictor variables
    :param features: A list of column names for the predictor variables
    :param vif_threshold: The VIF threshold for eliminating variables (default is 5)
    :return: 1. A list of remaining features after eliminating variables based on the VIF threshold
             2. A DataFrame of remaining features and their VIF Values
    """
    remaining_features = features[:]
    vif_values = []

    while True:
        vif_values.clear()
        for feature in remaining_features:
            # Assemble the features into a vector
            assembler = VectorAssembler(inputCols=[col for col in remaining_features if col != feature],
                                        outputCol="features")
            feature_data = assembler.transform(data)

            #scaler = StandardScaler(inputCol="features", 
            #            outputCol="scaledFeatures", 
            #            withStd=True, 
            #            withMean=True)

            # Compute summary statistics by fitting the StandardScaler
            # scalerModel = scaler.fit(feature_data)

            # Normalize each feature to have unit standard deviation and means
            # sc_data = scalerModel.transform(feature_data)

            # Fit a linear regression model
            lr = LinearRegression(featuresCol='features', labelCol=feature)
            lr_model = lr.fit(feature_data)

            # Calculate VIF for the feature
            vif = 1 / (1 - lr_model.summary.r2)
            vif_values.append((feature, vif))

        # Find the feature with the highest VIF
        max_vif_feature, max_vif_value = max(vif_values, key=lambda item: item[1])

        # Eliminate the feature if its VIF is above the threshold
        if max_vif_value > vif_threshold:
            remaining_features.remove(max_vif_feature)
        else:
            break
    vif_df = spark.createDataFrame(vif_values, ['Variable', 'VIF'])
    return remaining_features, vif_df


# Load the data
#raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basins.csv", header = True, inferSchema = True)
#raw_data = spark.read.csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv", header = True, inferSchema = True)
reg_path = "/gpfs/gibbs/pi/hydro/hydro/dataproces/ENVTABLES/regional_unit_parquet/dataset=stats_standardized_v1_0/reg_id=178"
env_var = ['bio1', 'bio2', 'bio3', 'bio4', 'bio5', 'bio6', 'bio7', 'bio8',
           'bio9', 'bio10', 'bio11', 'bio12', 'bio13', 'bio14', 'bio15', 'bio16', 
           'bio17', 'bio18', 'bio19', 'elev', 'flowpos', 'spi', 'sti', 'cti',
           'length', 'stright', 'sinusoid', 'cum_length', 'out_dist', 'source_elev', 'outlet_elev', 
           'elev_drop', 'out_drop', 'gradient', 'flow_ltm', 'c10', 'c20', 'c30', 'c40', 'c50', 'c60', 'c70', 
           'c80', 'c90', 'c100', 'c110', 'c120', 'c130', 'c140', 'c150', 'c160', 'c170', 'c180', 
           'c190', 'c200', 'c210', 'c220'] #flow_ltm
raw_data = spark.read.parquet(reg_path, header = True, inferSchema = True).select(env_var)
print("Number of sub-catchments:")
print(raw_data.count())

# Remove land use classes with 0% in all sub-catchments
sums = raw_data.select(*[fun.sum(c).alias(c) for c in raw_data.columns]).first()
cols_to_drop = [c for c in sums.asDict() if sums[c] == 0]
raw_data = raw_data.drop(*cols_to_drop)
print("Removed land use classes with 0 percentage in all sub-catchments:")
print(cols_to_drop)


# Remove columns with NaN or NULL values
na_counts = raw_data.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) for c in raw_data.columns]).first()
cols_to_drop = [c for c in na_counts.asDict() if na_counts[c] > 0]
raw_data = raw_data.drop(*cols_to_drop)
print("Removed columns with NaN or NULL values:")
print(cols_to_drop)

#df_new = raw_data.select([x for x in raw_data.columns if 'mean' in x] + [x for x in raw_data.columns if 'stream' in x] + [x for x in raw_data.columns if 'land' in x]) 

columns = raw_data.columns


remaining_features, vif_values = calculate_vif(raw_data, columns, vif_threshold=10)

print("Remaining features after VIF elimination:", remaining_features)

# Save remaining features with vif value
vif_values.coalesce(1).write.mode('overwrite').option("header", "true").csv("/vast/palmer/scratch/sbsc/mu78/clustering_global/reg_id_178/vif_values")

# Stop spark session
spark.stop()
