
library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load data --------------------------------------------------

epto <- fread("/mnt/shared/mschuerz/Global_EPTO_database_corrected_continent_20260804.csv")

# Select taxon -----------------------------------------------

sp_data <- epto %>%
    mutate(clean_species = ifelse(grepl("sp\\.", clean_species), "", clean_species),
           clean_species = ifelse(grepl("^[^_]+_[^_,]+,_[0-9]{4}$", species), "", clean_species),
            taxon = clean_species) 
   
sp_continent <- sp_data %>%
  distinct(
    cluster_id,
    taxon,
    order,
    continent,
    subcatchment_ID
  )

species_cluster_range <- sp_continent %>%
  distinct(taxon,cluster_id) %>%
  count(taxon,name = "n_clusters")

restricted_multicontinent_species <- sp_continent %>%
  left_join(species_cluster_range, by = "taxon") %>%
  filter(n_clusters == 1) %>%
  group_by(
    cluster_id,
    taxon,
    order,
    continent) %>%
  summarise(
    n_subcatchments = n_distinct(subcatchment_ID),
    n_records = n(),
    .groups = "drop") %>%
  group_by(
    cluster_id,
    taxon,
    order) %>%
  summarise(

    # Number of continents occupied
    n_continents = n_distinct(continent),

   # List of continents
   # continents = paste(
   #   sort(unique(continent)),
   #   collapse = "; "
   # ),

    # Subcatchment distribution by continent
    #subcatchments_by_continent = paste(
    #  paste0(
    #    continent,
    #    ": ",
    #    n_subcatchments
    #  ),
    #  collapse = "; "
    #),

    # Record distribution by continent
    records_by_continent = paste(
      paste0(continent, ": ", n_records),
      collapse = "; "
    ),

    # Total number of records for this species
    #total_records = sum(n_records),

    # Total number of subcatchments occupied
    #total_subcatchments = sum(n_subcatchments),

    .groups = "drop") %>%
  filter(n_continents > 1) %>%
  select(-n_continents)

# Save -------------------------------------------------------
fwrite(restricted_multicontinent_species,
  "/data/mschuerz/clustering_global/world_v2/restricted_multicontinent_species_20260828.csv", 
  row.names = FALSE, col.names = TRUE
)

t <- sp_data %>% filter(cluster_id %in% restricted_multicontinent_species$cluster_id, taxon %in% restricted_multicontinent_species$taxon)
s <- st_as_sf(t, coords = c("longitude", "latitude"), crs = 4326)
st_write(s, "/data/mschuerz/clustering_global/world_v2/restricted_multicontinent_species_20260828.gpkg")
