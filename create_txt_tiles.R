# Create .txt file per tile ID with cluster IDs
# Including reg_id, basin_id, subc_id, cluster_id

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
usePackage("doParallel")
usePackage("foreach")
usePackage("stringr")

# For restarting the script -----------------------------------------------

# To check which tiles already exist
# files <- list.files(paste0(wdir, "/world/cluster_rasters/"), pattern = "\\.tif$")

# hv_string <- str_extract(files, "h\\d+v\\d+")

# Read data ---------------------------------------------------------------
# RUs of South America 
reg_ids <- c(35, 42, 34, 175, 41, 48, 176, 179, 178, 33, 47,
             40, 39, 177, 32, 26, 27)

# RUs of America (North + South)
reg_ids <- c(21, 20, 163, 25, 184, 164, 31, 15, 162, 19, 168, 158,
             30, 37, 24, 14, 165, 167, 9, 2, 1, 8, 13, 166,
             18, 23, 29, 36, 37, 43, 174, 50, 6, 5, 11, 10, 16, 12,
             7, 3, 49, 35, 42, 34, 175, 41, 48, 176, 179, 178, 33, 47,
             40, 39, 177, 32, 26, 27)

# List with tile number and overlapping RUs - Look up table
tiles_RUids <- fread("/mnt/shared/tiles_tb/tile_RUids_old.txt",
                     header = FALSE, fill = TRUE)

tiles_RUids <- tiles_RUids %>%
    rename(tile_id = V1) %>%
    pivot_longer(., cols = 2:ncol(.), names_to = "col",
                 values_to = "reg_id") %>%
    select(tile_id, reg_id) %>%
    na.omit() %>%
    #filter(!tile_id %in% hv_string)
    filter(reg_id %in% reg_ids)

tiles <- tiles_RUids$tile_id %>% unique()

# Define cores ------------------------------------------------------------

ncores <- 10 # parallel::detectCores() - 1
cl <- makeCluster(ncores)
registerDoParallel(cl)

foreach(i = tiles, .packages = c("data.table", "tidyverse", "arrow", "hydrographr")) %dopar% {

  # Read file with sub-catchment ids
    subc_ids <- fread(paste0("/mnt/shared/tiles_tb/indx/", i, "_subcID.txt"))
    tmp_subc_ids <- subc_ids$V1

  # Define RUids which overlap with the tile using the look up table
    tmp_RUids <- tiles_RUids %>%
      filter(tile_id == i) %>%
      mutate(reg_id = as.character(reg_id)) %>%
      .$reg_id %>% unique()


  # Read cluster and rf prediction of the defined RUids
    cl_pred <- open_dataset(paste0(wdir, "/south_america_wo_flo1k/cluster_prediction_24_parquet"))
    
    cl_df <- cl_pred %>%
        filter(reg_id %in% tmp_RUids) %>%
        collect() %>%
        filter(subc_id %in% tmp_subc_ids)

    cl_df <- cl_df %>%
      select(reg_id, basin_id, subc_id, prediction) %>%
      rename(cluster_id = prediction)

    rf_pred <- open_dataset(paste0(wdir, "/south_america_wo_flo1k/rf_prediction_24_ntree200_depth12"))

    rf_df <- rf_pred %>%
        filter(reg_id %in% tmp_RUids) %>%
        collect() %>%
        filter(subc_id %in% tmp_subc_ids)
    
    rf_df <- rf_df %>%
      select(reg_id, basin_id, subc_id, prediction) %>%
      rename(cluster_id = prediction)
    
    df <- cl_df %>%
        add_row(rf_df) %>%
        mutate(cluster_id = ifelse(cluster_id == 0, max(cluster_id)+1, cluster_id),
               subc_id = as.integer(subc_id),
               cluster_id = as.integer(cluster_id))

    # Save cluster prediction table
    fwrite(df, paste0(wdir, "/south_america_wo_flo1k/cluster_tables/clusters24_", i, ".txt"), sep=" ")

}

stopCluster(cl)
