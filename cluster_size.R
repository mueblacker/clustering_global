
# Libraries ------------------------------------------------------
library(dplyr)
library(tidyr)
library(DBI)
library(duckdb)

options(scipen = 999)
options(digits = 10) 

con <- dbConnect(duckdb())

dbExecute(con, "SET threads = 16;")          
dbExecute(con, "SET memory_limit = '120GB';") 

counts <- dbGetQuery(con, "
    SELECT
        c.cluster_id,
        t.continent,
        COUNT(*) AS n_subcatchments
    FROM read_parquet('/data/mschuerz/clustering_global/world_v2/cluster30_parquet') c
    INNER JOIN read_parquet('/data/mschuerz/clustering_global/sub_catchment_continent_parquet') t
        USING (subc_id)
    GROUP BY c.cluster_id, t.continent
")


dbDisconnect(con, shutdown = TRUE)


totals <- counts %>%
  group_by(cluster_id) %>%
  summarise(
    total_subcatchments = sum(n_subcatchments),
    .groups = "drop"
  ) %>%
  mutate(
    total_percentage = 100 * total_subcatchments / sum(total_subcatchments)
  )

count_table <- counts %>%
  pivot_wider(
    names_from = continent,
    values_from = n_subcatchments,
    values_fill = 0
  ) %>%
  left_join(totals, by = "cluster_id") %>%
  relocate(total_subcatchments, .after = cluster_id) %>%
  select(-total_percentage) %>%
  arrange(desc(total_subcatchments))



 percentage_table <- counts %>%
  left_join(totals, by = "cluster_id") %>%
  mutate(
    percentage = 100 * n_subcatchments / total_subcatchments
  ) %>%
  select(cluster_id, total_subcatchments, total_percentage, continent, percentage) %>%
  pivot_wider(
    names_from = continent,
    values_from = percentage,
    values_fill = 0
  ) %>%
  arrange(desc(total_percentage))

# Save tables -------------------------------------------------
write.csv(count_table, "/data/mschuerz/clustering_global/world_v2/cluster_size_count_20260714.csv", row.names = FALSE)
write.csv(percentage_table, "/data/mschuerz/clustering_global/world_v2/cluster_size_percentages_20260714.csv", row.names = FALSE)
