# Set working directory
setwd('/home/mueblacker/Documents/Glowabio/Data/test_data_clustering')


# Libraries ---------------------------------------------------------------

library('data.table')
library('dplyr')
library('hydrographr')



# Load file with reclassification rules -----------------------------------
wdir <- '/home/mueblacker/Documents/Glowabio/Data/test_data_clustering'
raw_data <- fread("/home/mueblacker/Documents/Glowabio/Code/pyspark/basin_59_1173421.csv") %>% 
  select(subcID)

reclass <- fread(paste0(wdir, '/cluster_prediction.csv')) %>% 
  mutate(prediction = ifelse(prediction == 0, max(prediction) + 1, prediction),
         prediction = as.integer(prediction)) %>% 
  inner_join(raw_data, reclass, by = 'subcID')


# Directories for input and output raster ---------------------------------


# Define input and output raster layer
subc_raster <- paste0(wdir, "/subcatchment_1173421.tif")

recl_raster <- paste0(wdir, "/reclassified_raster_1173421.tif") 


# Reclassification of the raster file -------------------------------------


# Reclassify the stream network to obtain the Strahler stream order raster
cluster_rast <- reclass_raster(data = reclass,
                               rast_val = "subcID",
                               new_val = "prediction",
                               raster_layer = subc_raster,
                               recl_layer = recl_raster,
                               quiet = FALSE)
