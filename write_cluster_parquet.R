# Libraries --------------------------------------------------

library(dplyr)
library(tidyr)
library(data.table)
library(arrow)
library(db)
library(DBI)
library(duckdb)

library(arrow)
library(dplyr)
library(readr)

cluster_dir <- "/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/cluster_tables"

files <- list.files(
  cluster_dir,
  pattern = "\\.txt$",
  full.names = TRUE
)

out_dir <- "/data/mschuerz/clustering_global/world_v2/cluster_lookup_parquet"

if (dir.exists(out_dir))
  unlink(out_dir, recursive = TRUE)

for(i in seq_along(files)) {

  cat(i, "/", length(files), basename(files), "\n")

  x <- fread(files[i],  select = c("subc_id", "cluster_id")) %>%
    distinct(subc_id, cluster_id)

  write_dataset(
    x,
    path = out_dir,
    format = "parquet",
    basename_template = paste0("part-", i, "-{i}.parquet"),
    existing_data_behavior = "overwrite"
  )

  rm(x)
  gc()
}

con <- dbConnect(duckdb())

dbExecute(con, sprintf("
CREATE TABLE clusters AS
SELECT * FROM read_parquet('%s/**/*.parquet');
", out_dir))

bad <- dbGetQuery(con, "
SELECT
    subc_id,
    COUNT(DISTINCT cluster_id) AS n_clusters
FROM clusters
GROUP BY subc_id
HAVING COUNT(DISTINCT cluster_id) > 1
")

dbExecute(con, "
COPY (
    SELECT
        subc_id,
        MIN(cluster_id) AS cluster_id
    FROM clusters
    GROUP BY subc_id
)
TO '/data/mschuerz/clustering_global/world_v2/cluster30_parquet'
(
    FORMAT PARQUET,
    PARTITION_BY (cluster_id)
);
")
