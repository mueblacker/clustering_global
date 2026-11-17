# =========================================================================
# Add continent information to sub-catchments with occurrence data
#
# The script assigns each occurrence a continent based on the dominant UN
# sub-region of its sub-catchment. Additional geographic corrections are
# applied to occurrence records incorrectly assigned to Europe.
# =========================================================================


# Load libraries ----------------------------------------------------------

library(dplyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------------------

# Read the occurrence dataset containing sub-catchment and cluster IDs.
epto <- fread(
  "/my_directory/data/Global_EPTO_database_clean_species_cluster_id_corr_20260728.csv"
)

# Load sub-catchment spatial information ----------------------------------

# Open the Parquet dataset containing country and UN region information
# assigned to Hydrography90m sub-catchments.
tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_country_parquet",
  format = "parquet"
)

# Extract unique sub-catchment IDs represented in the occurrence dataset.
ids <- unique(epto$subcatchment_ID)

# Load sub-region and pixel-count information only for relevant sub-catchments.
subcatchment_info <- tiles %>%
  select(subc_id, sub_region_name, pixel_count) %>%
  filter(subc_id %in% ids) %>%
  collect()


# Assign dominant sub-region to sub-catchments ----------------------------

# Some sub-catchments overlap more than one country or UN sub-region.
# First, sum pixel counts for each sub-catchment/sub-region combination.
# Then select the sub-region with the largest pixel count as the dominant
# sub-region of that sub-catchment.
subcatchment_info <- subcatchment_info %>%
  group_by(subc_id, sub_region_name) %>%
  summarise(
    pixel_count = sum(pixel_count),
    .groups = "drop"
  ) %>%
  group_by(subc_id) %>%
  slice_max(
    order_by = pixel_count,
    n = 1,
    with_ties = FALSE
  ) %>%
  ungroup()


# Prepare occurrence dataset ----------------------------------------------

# Join dominant sub-region information to occurrence records.
# Keep only occurrences with both a cluster ID and an assigned sub-region.
#
# UN sub-regions are then grouped into broader continent categories.
sp_data <- epto %>%
  left_join(
    subcatchment_info,
    by = c("subcatchment_ID" = "subc_id")
  ) %>%
  filter(!is.na(cluster_id), !is.na(sub_region_name)) %>%
  mutate(
    continent = case_when(

      # European UN sub-regions.
      sub_region_name %in% c(
        "Northern Europe",
        "Southern Europe",
        "Eastern Europe",
        "Western Europe"
      ) ~ "Europe",

      # Asian UN sub-regions.
      sub_region_name %in% c(
        "Eastern Asia",
        "Southern Asia",
        "South-eastern Asia",
        "Western Asia",
        "Central Asia"
      ) ~ "Asia",

      # Northern America.
      sub_region_name == "Northern America" ~ "North America",

      # Latin America and the Caribbean are grouped as South America here.
      sub_region_name == "Latin America and the Caribbean" ~
        "South America",

      # African UN sub-regions.
      sub_region_name %in% c(
        "Sub-Saharan Africa",
        "Northern Africa"
      ) ~ "Africa",

      # Oceanian UN sub-regions.
      sub_region_name %in% c(
        "Melanesia",
        "Polynesia",
        "Micronesia",
        "Australia and New Zealand"
      ) ~ "Oceania",

      # Assign all unmatched sub-regions to "Other".
      TRUE ~ "Other"
    )
  )


# Apply geographic corrections --------------------------------------------

# Correct records initially assigned to Europe where their occurrence
# coordinates clearly fall within another continent or oceanic region.
#
# These corrections are based on broad longitude/latitude bounding boxes
# and may apply to island territories or sub-catchments assigned to Europe
# because of nearest-country or spatial-overlay effects.
clean_table <- sp_data %>%
  mutate(
    continent = case_when(
      
      # South America and the Caribbean.
      continent == "Europe" &
        (latitude >= -56.0 & latitude <= 25.0 &
         longitude >= -110.0 & longitude <= -34.0) ~ "South America",
      
      # Africa.
      continent == "Europe" &
        (latitude >= -35.0 & latitude <= 38.0 &
         longitude >= -25.0 & longitude <= 60.0) ~ "Africa",
      
      # Oceania and the western Pacific.
      continent == "Europe" &
        (latitude >= -50.0 & latitude <= 15.0 &
         longitude >= 110.0 & longitude <= 180.0) ~ "Oceania",
      
      # Oceania and the eastern Pacific.
      continent == "Europe" &
        (latitude >= -30.0 & latitude <= 5.0 &
         longitude >= -180.0 & longitude <= -110.0) ~ "Oceania",
      
      # North America, excluding the Caribbean latitude range handled above.
      continent == "Europe" &
        (latitude > 25.0 & latitude <= 85.0 &
         longitude >= -170.0 & longitude <= -50.0) ~ "North America",
      
      # Keep the existing continent assignment for all other records.
      TRUE ~ continent
    )
  )


# Save --------------------------------------------------------------------

# Save the occurrence dataset with sub-region and continent assignments.
fwrite(
  clean_table,
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_continent_20260803.csv", 
  row.names = FALSE,
  col.names = TRUE
)