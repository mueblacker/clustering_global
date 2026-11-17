# =========================================================================
# Cluster restricted species occurring across multiple continents
#
# Identifies species that occur in only one L-FHC cluster
# globally but are represented by occurrence records from more than one
# continent within that cluster.
# =========================================================================


# Load libraries ----------------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)
library(sf)

# Load data ---------------------------------------------------------------

# Read the corrected EPTO occurrence dataset containing cluster,
# sub-catchment, and continent assignments.
epto <- fread(
  "/my_directory/data/Global_EPTO_database_corrected_continent_20260804.csv"
)


# Prepare species data ----------------------------------------------------

# Remove records that are not identified to species level.
# The resulting `taxon` field is used for all species-level summaries.
sp_data <- epto %>%
  mutate(
    clean_species = ifelse(
      grepl("sp\\.", clean_species),
      "",
      clean_species
    ),
    clean_species = ifelse(
      grepl("^[^_]+_[^_,]+,_[0-9]{4}$", species),
      "",
      clean_species
    ),
    taxon = clean_species
  )

# Keep unique combinations of cluster, species, taxonomic order,
# continent, and sub-catchment.
sp_continent <- sp_data %>%
  filter(taxon != "") %>%
  distinct(
    cluster_id,
    taxon,
    order,
    continent,
    subcatchment_ID
  )


# Identify restricted species ---------------------------------------------

# Calculate the number of clusters occupied by each taxon.
# Species occurring in only one cluster are treated as cluster-restricted.
species_cluster_range <- sp_continent %>%
  distinct(taxon, cluster_id) %>%
  count(
    taxon,
    name = "n_clusters"
  )

# Identify cluster-restricted species that occur on more than one continent.
restricted_multicontinent_species <- sp_continent %>%
  
  # Add the number of clusters occupied by each taxon.
  left_join(species_cluster_range, by = "taxon") %>%
  
  # Retain species found in only one cluster.
  filter(n_clusters == 1) %>%
  
  # Count occupied sub-catchments and records within each continent.
  group_by(
    cluster_id,
    taxon,
    order,
    continent
  ) %>%
  summarise(
    n_subcatchments = n_distinct(subcatchment_ID),
    n_records = n(),
    .groups = "drop"
  ) %>%
  
  # Summarise each restricted species across continents.
  group_by(
    cluster_id,
    taxon,
    order
  ) %>%
  summarise(
    
    # Number of continents in which the species occurs.
    n_continents = n_distinct(continent),
    
    # Store occurrence-record counts by continent as a text field.
    records_by_continent = paste(
      paste0(continent, ": ", n_records),
      collapse = "; "
    ),
    
    .groups = "drop"
  ) %>%
  
  # Keep species represented on more than one continent.
  filter(n_continents > 1) %>%
  
  # Remove the intermediate continent-count field from final output.
  select(-n_continents)


# Save results ------------------------------------------------------------

# Save the table of cluster-restricted, multi-continent species.
fwrite(
  restricted_multicontinent_species,
  "/my_directory/data/clustering_global/l_fhc/restricted_multicontinent_species_20260828.csv", 
  row.names = FALSE,
  col.names = TRUE
)


# Create spatial output ---------------------------------------------------

# Keep all occurrence records belonging to the identified cluster/species
# combinations for spatial inspection.

t <- sp_data %>%
  filter(
    cluster_id %in% restricted_multicontinent_species$cluster_id,
    taxon %in% restricted_multicontinent_species$taxon
  )

# Convert selected occurrence records to WGS84 point features.
s <- st_as_sf(
  t,
  coords = c("longitude", "latitude"),
  crs = 4326
)

# Write occurrence locations to a GeoPackage for mapping and review.
st_write(
  s,
  "/my_directory/data/clustering_global/l_fhc/restricted_multicontinent_species_20260828.gpkg"
)