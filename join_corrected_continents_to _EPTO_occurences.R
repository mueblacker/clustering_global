#  Add continent to sub-catchments with occurrence data

# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------

epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_corrected_20260803.csv"
)
# Load sub-catchment spatial information ----------------------

continents <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_continent_parquet",
  format = "parquet"
)

ids <- unique(epto$subcatchment_ID)

subcatchment_info <- continents %>%
  select(subc_id, continent) %>%
  filter(subc_id %in% ids) %>%
  collect()

sp_data <- epto %>%
  left_join(subcatchment_info, by = c("subcatchment_ID" = "subc_id")) 

fwrite(sp_data,
  "/mnt/shared/mschuerz/Global_EPTO_database_corrected_continent_20260804.csv", 
  row.names = FALSE, col.names = TRUE
)
