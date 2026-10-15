library(DBI)
library(duckdb)
library(arrow)

tiles <- open_dataset(
  "/data/mschuerz/clustering_global/sub_catchment_country_parquet"
)

con <- dbConnect(duckdb())

duckdb_register_arrow(
  con,
  "tiles",
  tiles
)

dbExecute(con, "

COPY (

    WITH continent_pixels AS (

        SELECT
            subc_id,
            CASE

                 WHEN tile IN ('h10v06', 'h12v06', 'h12v08', 'h08v06') THEN 'South America'
                 WHEN tile IN ('h34v10', 'h00v04',  'h00v06', 'h00v08', 'h00v10', 'h02v06', 'h02v08', 'h02v10') THEN 'Oceania'
                 WHEN tile IN ('h22v08', 'h22v10',  'h20v10') THEN 'Africa'

                WHEN sub_region_name IN (
                    'Northern Europe',
                    'Southern Europe',
                    'Eastern Europe',
                    'Western Europe'
                )
                THEN 'Europe'

                WHEN sub_region_name IN (
                    'Eastern Asia',
                    'Southern Asia',
                    'South-eastern Asia',
                    'Western Asia',
                    'Central Asia'
                )
                THEN 'Asia'

                WHEN sub_region_name = 'Northern America'
                THEN 'North America'

                WHEN sub_region_name = 'Latin America and the Caribbean'
                THEN 'South America'

                WHEN sub_region_name IN (
                    'Northern Africa',
                    'Sub-Saharan Africa'
                )
                THEN 'Africa'

                WHEN sub_region_name IN (
                    'Melanesia',
                    'Micronesia',
                    'Polynesia',
                    'Australia and New Zealand'
                )
                THEN 'Oceania'

                ELSE 'Other'

            END AS continent,

            pixel_count

        FROM tiles

    ),

    aggregated AS (

        SELECT
            subc_id,
            continent,
            SUM(pixel_count) AS pixels

        FROM continent_pixels

        GROUP BY
            subc_id,
            continent

    ),

    dominant AS (

        SELECT
            subc_id,
            continent,

            ROW_NUMBER() OVER(
                PARTITION BY subc_id
                ORDER BY pixels DESC
            ) AS rn

        FROM aggregated

    )

    SELECT
        subc_id,
        continent

    FROM dominant

    WHERE rn = 1

)

 TO '/data/mschuerz/clustering_global/sub_catchment_continent_parquet'
    (
        FORMAT PARQUET,
        PARTITION_BY (continent)
    );

")
