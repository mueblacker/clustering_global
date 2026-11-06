# =========================================================================
# Estimate overall and cluster-wise variable importance (vimp) using
# the Random Forest classification model of the R package `randomForestSRC`
# =========================================================================

# Set working directory
setwd("/my_directory/data/clustering_global")

# Functions ---------------------------------------------------------------

# Define a helper function that checks whether an R package is installed.
# If the package is not installed, it installs the package and its dependencies.
# It then loads the package into the current R session.
usePackage <- function(p){
  if (!is.element(p, installed.packages()[,1])) install.packages(p, dep = TRUE)
  library(p, character.only = TRUE)
}

# Define a helper function to print the elapsed processing time
finish_progress <- function(nmax, t0, word) {
   cat("\r", paste0(rep(" ", 75), collapse = ""))
   interval(t0,now()) %>%
    round(.) %>%
    as.period(.) %>%
    as.character(.) %>%
    paste("Completed", word, nmax, "in", .)
}


# Libraries ---------------------------------------------------------------

# Load required R packages, installing them first if necessary
usePackage("data.table")
usePackage("tidyverse")
usePackage("lubridate")
usePackage("randomForestSRC")
usePackage("arrow")



# Directories -------------------------------------------------------------
  
# Define the directory containing the sampled CSV output created by Spark
sample_path <- "/my_directory/data/clustering_global/l_fhc/pfhc_cluster_20_25K_sample_for_vimp_rfsrc"

# Define an output directory for Random Forest model results and
# variable-importance output file
rf_path <- "/my_directory/data/clustering_global/lfhc/lfhc_cluster_30_vimp_rfsrc"
# Create the output directory if it does not already exist
if(!dir.exists(rf_path)) dir.create(rf_path)


# Input data --------------------------------------------------------------

# Find CSV files in the sample-output directory
sample_file <- list.files(sample_path, pattern = "\\.csv$", full.names = TRUE)

# Read the first CSV file returned by `list.files()`
sample_df <- read.csv(sample_file[1], header = TRUE)

# Prepare the dataset for Random Forest classification
df <- sample_df %>%
    select(-subc_id) %>%
    rename(k = prediction) %>%
    mutate(k = as.factor(k))


# Random forest -----------------------------------------------------------

# Record the current time before fitting the model
t0 <- now()
# Fit a Random Forest classification model
rf <- rfsrc(k~., data = df, ntree=500, importance = TRUE)
# Create a message describing the elapsed Random Forest fitting time
t1 <- finish_progress(i, t0, "rf")
# Print the elapsed-time/completion message
print(t1)

# Save output --------------------------------------------------------------

# Save the fitted Random Forest model as an RDS file
write_rds(rf, paste0(rf_path, "/lfhc_cluster_30_vimp_rfsrc.rds"))


# Create VIMP table --------------------------------------------------------

# Extract the variable-importance output from the fitted model
vimp <- as.data.frame(rf$importance) %>% 
  rownames_to_column(., var = "variable") 

# Save the complete raw variable-importance table as a CSV file
write_csv(vimp, paste0(rf_path, "/lfhc_cluster_30_vimp_rfsrc.csv"))


# Create a relative variable-importance table.
#
# - Retain the variable name and the overall importance metric (`all`).
# - Divide each importance value by the maximum importance value, so the
#   most important variable has a relative importance of 1.
# - Sort variables from lowest to highest relative importance.
vimp <- vimp %>% 
  select(variable, all) %>% 
  mutate(rel_vimp = all/max(all)) %>% 
  arrange(rel_vimp) 

# Save the relative variable-importance table as CSV
write_csv(vimp, paste0(rf_path, "/lfhc_cluster_30_rel_vimp_all_rfsrc.csv"))

# Exit R without saving the current workspace image
quit(save = "no")