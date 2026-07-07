species_continents <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, continent, clean_species) %>%
  group_by(cluster_id, clean_species) %>%
  summarise(
    n_continents = n_distinct(continent),
    .groups = "drop"
  )

multi_continent_species <- species_continents %>%
  group_by(cluster_id) %>%
  summarise(
    n_species = n(),
    n_multi_continent_species = sum(n_continents > 1),
    prop_multi_continent = 100 * n_multi_continent_species / n_species,
    .groups = "drop"
  )

multi_continent_order <- sp_data %>%
  filter(clean_species != "") %>%
  distinct(cluster_id, continent, order, clean_species) %>%
  group_by(cluster_id, order, clean_species) %>%
  summarise(
    n_continents = n_distinct(continent),
    .groups = "drop"
  ) %>%
  filter(n_continents > 1) %>%
  group_by(cluster_id, order) %>%
  summarise(
    n_multi_continent_species = n(),
    .groups = "drop"
  )

  dominant_order <- multi_continent_order %>%
  group_by(cluster_id) %>%
  slice_max(
    order_by = n_multi_continent_species,
    n = 1,
    with_ties = FALSE
  ) %>%
  ungroup()

  multi_continent_order <- multi_continent_order %>%
  group_by(cluster_id) %>%
  mutate(
    prop_multi_continent_species =
      100 * n_multi_continent_species /
      sum(n_multi_continent_species)
  ) %>%
  ungroup()

 multi_continent_order %>% print(n=83)
