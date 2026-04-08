from google.oauth2 import service_account
from google.cloud import bigquery
import pandas as pd
import _config


bq_keys = _config.get_bigquery_keys()
credentials = service_account.Credentials.from_service_account_info(bq_keys)

# client = bigquery.Client()

client = bigquery.Client(
    credentials=credentials,
    project=credentials.project_id,   # or "rvshare-analytics"
)



sql = "SELECT * FROM `rvshare-analytics.seeds_insurance.insurance_carrier_rates` "
query_job = client.query(sql)  # API request
df = query_job.result().to_dataframe()

# Perform a query.
# QUERY = (
#     'SELECT name FROM `bigquery-public-data.usa_names.usa_1910_2013` '
#     'WHERE state = "TX" '
#     'LIMIT 100')
# query_job = client.query(QUERY)  # API request


rows = query_job.result()  # Waits for query to finish

for row in rows:
    print(row)