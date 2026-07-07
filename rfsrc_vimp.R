# Set working directory
setwd("/mnt/mschuerz/mschuerz/data/clustering_global")

# Functions ---------------------------------------------------------------

# Function to check if the required packages are installed and to load the library
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}

# Process time function
finish_progress <- function(nmax, t0, word) {
   cat("\r", paste0(rep(" ", 75), collapse = ""))
   interval(t0,now()) %>%
    round(.) %>%
    as.period(.) %>%
    as.character(.) %>%
    paste("Completed", word, nmax, "in", .)
}


# Libraries ---------------------------------------------------------------

usePackage("data.table")
usePackage("tidyverse")
usePackage("lubridate")
usePackage("randomForestSRC")
usePackage("arrow")



# Directories -------------------------------------------------------------
  
# Define path
cluster_path <- "/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/cluster_prediction_30_v2_parquet"
env_path <- "/mnt/shared/regional_unit_parquet/dataset=stats_standardized_v1_0"

# Selected features
features <- read.csv("/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/correlation/uncorr_envVar_world_085.csv")
selected_features <- features$V1

# Create paths for random forest output
rf_path <- "/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/vimp_30_v2"
if(!dir.exists(rf_path)) dir.create(rf_path)


# Input data --------------------------------------------------------------

# Open first parquet dataset
df_cluster <- open_dataset(cluster_path, format = "parquet")

# 1% sample per cluster
set.seed(123)
sample_ids <- df_cluster %>%
  select(subc_id, prediction) %>%     # only needed columns
  collect() %>%             # bring minimal data into R
  group_by(prediction) %>%
  slice_sample(prop = 0.01) %>%
  ungroup() 

# Extract unique IDs
ids_vector <- unique(sample_ids$subc_id)

# Open second parquet dataset
df_env <- open_dataset(env_path, format = "parquet")

# Filter second dataset using sampled IDs
sample_env <- df_env %>%
  filter(subc_id %in% ids_vector) %>%
  select(subc_id, matches(ids_vector)) %>%
  collect()

df <- inner_join(sample_env, sample_ids, by = "subc_id") %>%
    select(-subc_id) %>%
    rename(k = prediction) %>%
    mutate(k = as.factor(k))


# Random forest -----------------------------------------------------------

t0 <- now()
rf <- rfsrc(k~., data = df, ntree=500, importance = TRUE)
t1 <- finish_progress(i, t0, "rf")
print(t1)

# Save output --------------------------------------------------------------


write_rds(rf, paste0(rf_path, "/vimp_30_v2.rds"))


# Create VIMP plot --------------------------------------------------------

vimp <- as.data.frame(rf$importance) %>% 
  rownames_to_column(., var = "variable") 

write_csv(vimp, paste0(rf_path, "/vimp_30_v2.csv"))

vimp <- vimp %>% 
  select(variable, all) %>% 
  mutate(rel_vimp = all/max(all)) %>% 
  arrange(rel_vimp) 

# Save tabel
write_csv(vimp, paste0(rf_path, "/rel_vimp_all_30_v2.csv"))


quit(save = "no")