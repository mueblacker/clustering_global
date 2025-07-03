# Start the PySpark server
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('vif_calculation').getOrCreate()

# Load libraries
from pyspark import SparkFiles
from pyspark.sql import functions as fun
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.sql.functions import col

# Function to calculate vif
def calculate_vif(data, features, vif_threshold=5):
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

            scaler = StandardScaler(inputCol="features", 
                        outputCol="scaledFeatures", 
                        withStd=True, 
                        withMean=True)

            # Compute summary statistics by fitting the StandardScaler
            scalerModel = scaler.fit(feature_data)

            # Normalize each feature to have unit standard deviation and means
            sc_data = scalerModel.transform(feature_data)

            # Fit a linear regression model
            lr = LinearRegression(featuresCol='features', labelCol=feature)
            lr_model = lr.fit(sc_data)

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
# raw_data = spark.read.csv("/vast/palmer/scratch/sbsc/mu78/test_data/basin_59_1173421.csv", header = True, inferSchema = True)
raw_data = spark.read.csv("/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv", header = True, inferSchema = True)


# Remove land use classes with 0% in all sub-catchments
sums = raw_data.select(*[fun.sum(c).alias(c) for c in raw_data.columns]).first()
cols_to_dop = [c for c in sums.asDict() if sums[c] == 0]
raw_data = raw_data.drop(*cols_to_dop)

df_new = raw_data.select([x for x in raw_data.columns if 'mean' in x] + [x for x in raw_data.columns if 'stream' in x] + [x for x in raw_data.columns if 'land' in x]) 

columns = df_new.columns


remaining_features, vif_values = calculate_vif(df_new, columns, vif_threshold=5)

print("Remaining features after VIF elimination:", remaining_features)

# Save remaining features with vif value
vif_values.coalesce(1).write.mode('overwrite').option("header", "true").csv("/home/mueblacker/Documents/Glowabio/Data/test_data_clustering/vif_values")

# Stop spark session
spark.stop()