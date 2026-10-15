
# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)
library(sf)


# Load occurrence data ----------------------------------------
epto <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_subc_corr_20260803.csv")


cluster <- open_dataset(
  "/data/mschuerz/clustering_global/world_v2/cluster30_parquet/",
  format = "parquet"
)

subc_cluster <- cluster %>%
  filter(subc_id %in% unique(epto$subcatchment_ID)) %>%
  select(subc_id, cluster_id) %>%
  collect()

join_epto_cluster <- left_join(epto, subc_cluster, by = join_by(subcatchment_ID == subc_id))
na <- join_epto_cluster %>% filter(is.na(cluster_id))

fwrite(join_epto_cluster, "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_subc_corr_cluster_id_20260803.csv")
fwrite(na, "/mnt/shared/mschuerz/epto_na_20260803.csv")

sf_na <- na %>%
    st_as_sf(., coords = c("longitude", "latitude"), crs = 4326)

write_sf(sf_na, "/data/mschuerz/clustering_global/world_v2/epto_na_20260803.gpkg")

join_epto_cluster <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_subc_corr_cluster_id_20260803.csv")

join_epto_cluster <- join_epto_cluster %>% mutate(subcatchment_ID = ifelse(occurrence_ID == 107302491,  41723638, subcatchment_ID),
                                                  cluster_id = ifelse(occurrence_ID == 107302491, 6, cluster_id))
