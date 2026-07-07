import duckdb
import pandas as pd

# -----------------------------
# SETTINGS
# -----------------------------
parquet1_path = "/data/mschuerz/clustering_global/world_v2/cluster_prediction_30_v2_parquet" 
parquet2_path = "/data/mschuerz/dataset=stats_standardized_v1_0"
columns_csv_path = "/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/correlation/uncorr_envVar_world_085.csv"
output_csv_path = "/mnt/mschuerz/mschuerz/data/clustering_global/world_v2/sample0.01_for_vimp.csv"

seed = 123
sample_fraction = 0.01

# -----------------------------
# READ COLUMN NAMES
# -----------------------------
columns_df = pd.read_csv(columns_csv_path)

# First column contains desired column names
selected_columns = columns_df.iloc[:, 0].tolist()

# Ensure ID is included
if "subc_id" not in selected_columns:
    selected_columns.insert(0, "subc_id")

columns_sql = ", ".join([f"p2.{col}" for col in selected_columns])

# -----------------------------
# CONNECT
# -----------------------------
con = duckdb.connect()
con.execute("PRAGMA threads=1")        # ensure deterministic order
con.execute(f"SELECT setseed({seed / 1_000_000})")

# -----------------------------
# QUERY
# -----------------------------
query = f"""
WITH sampled AS (
    SELECT subc_id, "prediction"
    FROM (
        SELECT
            subc_id,
            "prediction",
            ROW_NUMBER() OVER (
                PARTITION BY "prediction"
                ORDER BY random()
            ) AS rn,
            COUNT(*) OVER (PARTITION BY "prediction") AS n_group
        FROM read_parquet('{parquet1_path}')
    )
    WHERE rn <= CEIL({sample_fraction} * n_group)
)

SELECT {columns_sql}, s."prediction"
FROM read_parquet('{parquet2_path}') p2
INNER JOIN sampled s
ON p2.subc_id = s.subc_id
"""

# -----------------------------
# WRITE DIRECTLY TO CSV (memory efficient)
# -----------------------------
con.execute(f"""
COPY (
{query}
) TO '{output_csv_path}' (HEADER, DELIMITER ',')
""")

print(f"Sample saved to: {output_csv_path}")