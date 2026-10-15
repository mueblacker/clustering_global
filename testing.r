library(data.table)
library(dplyr)
library(sf)

epto_org <- fread("/mnt/shared/mschuerz/Global_EPTO_database.csv")
epto <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_corr_20260728.csv")
multi_con <- fread("/data/mschuerz/clustering_global/world_v2/restricted_multicontinent_species_20260728.csv")

epto_con <- fread("/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_corr_continent_20260728.csv")
filtered <- epto_con %>%
    filter(cluster_id %in% multi_con$cluster_id & clean_species %in% multi_con$taxon) 

sf_multi_con <- filtered %>%
    st_as_sf(., coords = c("longitude", "latitude"), crs = 4326)

write_sf(sf_multi_con, "/data/mschuerz/clustering_global/world_v2/multi_con_records_20260804.gpkg")

subc <- tiles %>%
  filter(subc_id == 76) %>%
  collect()

test <- fread("/mnt/shared/mschuerz/Global_EPTO_database_subc_ids.csv")

fwrite("")

