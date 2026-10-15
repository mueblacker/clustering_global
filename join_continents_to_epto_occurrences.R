#  Add continent to sub-catchments with occurrence data

# Load libraries ----------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)


# Load occurrence data ----------------------------------------

epto <- fread(
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_corr_20260728.csv"
)
# Load sub-catchment spatial information ----------------------

tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_country_parquet",
  format = "parquet"
)

ids <- unique(epto$subcatchment_ID)

subcatchment_info <- tiles %>%
  select(subc_id,sub_region_name,pixel_count) %>%
  filter(subc_id %in% ids) %>%
  collect()


# Assign dominant sub-region to sub-catchments --------------

# Some sub-catchments overlap multiple UN sub-regions.
# The dominant sub-region is assigned based on the largest
# number of pixels belonging to each region.

subcatchment_info <- subcatchment_info %>%
  group_by(subc_id, sub_region_name) %>%
  summarise(pixel_count = sum(pixel_count),
    .groups = "drop") %>%
  group_by(subc_id) %>%
  slice_max(order_by = pixel_count, n = 1, with_ties = FALSE) %>%
  ungroup()


# Prepare occurrence dataset ---------------------------------

# Join spatial information and collapse UN sub-regions into
# broader continental categories.

sp_data <- epto %>%
  left_join(subcatchment_info, by = c("subcatchment_ID" = "subc_id")) %>%
  filter(!is.na(cluster_id), !is.na(sub_region_name)) %>%
  mutate(continent = case_when(

      sub_region_name %in% c(
        "Northern Europe",
        "Southern Europe",
        "Eastern Europe",
        "Western Europe"
      ) ~ "Europe",

      sub_region_name %in% c(
        "Eastern Asia",
        "Southern Asia",
        "South-eastern Asia",
        "Western Asia",
        "Central Asia"
      ) ~ "Asia",

      sub_region_name == "Northern America" ~ "North America",

      sub_region_name == "Latin America and the Caribbean" ~
        "South America",

      sub_region_name %in% c(
        "Sub-Saharan Africa",
        "Northern Africa"
      ) ~ "Africa",

      sub_region_name %in% c(
        "Melanesia",
        "Polynesia",
        "Micronesia",
        "Australia and New Zealand"
      ) ~ "Oceania",

      TRUE ~ "Other"
    ))

# Save ----------------------------------------------------


# 2. Direktes Mutate mit Prüfung: "Wenn Europe UND in Bounding-Box, dann ändern"
clean_table <- sp_data %>%
  mutate(continent = case_when(
    # --- BOX SÜDAMERIKA & KARIBIK ---
    # Breitengrad bis 25.0° N erweitert, um alle Karibikinseln mitzunehmen
    continent == "Europe" & (latitude >= -56.0 & latitude <= 25.0 & longitude >= -110.0 & longitude <= -34.0) ~ "South America",
    
    # --- BOX AFRIKA ---
    continent == "Europe" & (latitude >= -35.0 & latitude <= 38.0 & longitude >= -25.0 & longitude <= 60.0) ~ "Africa",
    
    # --- BOX OZEANIEN / WEST-PAZIFIK ---
    continent == "Europe" & (latitude >= -50.0 & latitude <= 15.0 & longitude >= 110.0 & longitude <= 180.0) ~ "Oceania",
    
    # --- BOX OZEANIEN / OST-PAZIFIK ---
    continent == "Europe" & (latitude >= -30.0 & latitude <= 5.0 & longitude >= -180.0 & longitude <= -110.0) ~ "Oceania",
    
    # --- BOX NORDAMERIKA (Restliches Nordamerika ohne Karibik) ---
    # Startet nun erst ab 25.0° N (z. B. für Saint-Pierre und Miquelon nahe Kanada)
    continent == "Europe" & (latitude > 25.0 & latitude <= 85.0 & longitude >= -170.0 & longitude <= -50.0) ~ "North America",
    
    # Standardfall: Wenn nichts zutrifft, behalte den alten Wert
    TRUE ~ continent
  ))

fwrite(clean_table,
  "/mnt/shared/mschuerz/Global_EPTO_database_clean_species_cluster_id_continent_20260803.csv", 
  row.names = FALSE, col.names = TRUE
)
