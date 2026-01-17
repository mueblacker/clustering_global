# Reclassification of cluster IDs

# Set working directory ---------------------------------------------------

wdir <- "/mnt/mschuerz/mschuerz/data/clustering_global"
setwd(wdir)

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}

# Libraries ---------------------------------------------------------------
usePackage("data.table")
usePackage("tidyverse")
usePackage("hydrographr")
usePackage("arrow")

# Read data ---------------------------------------------------------------

# List with tile number and overlapping RUs - Look up table
tiles_RUids <- fread("/mnt/shared/tiles_tb/tile_RUids_old.txt")

tiles <- tiles_RUids$x %>% unique()

# Define cores ------------------------------------------------------------

ncores <- parallel::detectCores() - 1
cl <- makeCluster(ncores)
registerDoParallel(cl)

result <- foreach(i = tiles) %dopar% {

  # Read file with sub-catchment ids
    subc_ids <- fread(paste0("/mnt/shared/tiles_tb/indx/", i, "_subcID.txt"))

  # Define RUids which overlap with the tile

  # Read cluster and rf prediction of the defined RUids
    cl_pred <- open_dataset(past0(wdir, "/world/cluster_prediction_30_parquet"))
    rf_pred <- open_dataset(past0(wdir, "/world/rf_prediction_ntree200_depth12"))

    cl_df <- cl_pred %>%
        filter(reg_id %in% RUids) %>%
        collect() %>%
        filter(subc_id %in% subc_ids)
    
    rf_df <- rf_pred %>%
        filter(reg_id %in% RUids) %>%
        collect() %>%
        filter(subc_id %in% subc_ids)
    
    df <- cl_df %>%
        add_row(rf_df)
     


}
