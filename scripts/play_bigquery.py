from hashlib import sha256
from datetime import datetime

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from scripts import _config


logger = _config.logger_configure("play_bigquery")

BQ_TABLE_ID = "rvshare-analytics.seeds_insurance.checkbook_checks"

bq_keys = _config.get_bigquery_keys()
credentials = service_account.Credentials.from_service_account_info(bq_keys)

client = bigquery.Client(
    credentials=credentials,
    project=credentials.project_id,
)


def _normalize_checkbook_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    _config.report(f"Starting dataframe normalization. input_shape={df.shape}", logger=logger)

    df = df.copy()

    rename_map = {
        "recipient.line_1": "recipient_line_1",
        "recipient.line_2": "recipient_line_2",
        "recipient.city": "recipient_city",
        "recipient.state": "recipient_state",
        "recipient.zip": "recipient_zip",
    }
    df = df.rename(columns=rename_map)

    _config.report(f"Finished dataframe normalization. output_shape={df.shape}", logger=logger)
    return df


def _validate_and_convert_dates(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns:
        raise ValueError("Expected a 'date' column but none was found.")

    _config.report("Validating date column", logger=logger)

    df = df.copy()
    converted = pd.to_datetime(df["date"], errors="coerce")
    bad_rows = df[converted.isna() & df["date"].notna()]

    if not bad_rows.empty:
        sample = bad_rows[["id", "date"]].head(10).to_dict("records")
        message = f"Date validation failed for {len(bad_rows)} row(s). Sample: {sample}"
        _config.report(message, logger=logger, level="error")
        raise ValueError(message)

    df["date"] = converted.dt.normalize()
    _config.report("Date validation passed", logger=logger)
    return df


def _compute_row_hash(row: pd.Series) -> str:
    values = row.fillna("").astype(str).tolist()
    payload = "|".join(values)
    return sha256(payload.encode("utf-8")).hexdigest()


def _prepare_for_bigquery(df: pd.DataFrame, batch_id=None) -> pd.DataFrame:
    df = _normalize_checkbook_dataframe(df)
    df = _validate_and_convert_dates(df)

    _config.report("Applying dataframe type cleanup", logger=logger)

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    if "reported_at" not in df.columns:
        df["reported_at"] = pd.Timestamp.utcnow()

    df["reported_at"] = pd.to_datetime(df["reported_at"], errors="coerce")
    df["batch_id"] = batch_id

    string_cols = [
        "id",
        "number",
        "direction",
        "status",
        "name",
        "description",
        "sender",
        "recipient",
        "recipient_line_1",
        "recipient_line_2",
        "recipient_city",
        "recipient_state",
        "recipient_zip",
        "image_uri",
        "row_hash",
        "batch_id",
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    hash_columns = [
        "id",
        "date",
        "number",
        "direction",
        "status",
        "amount",
        "name",
        "description",
        "sender",
        "recipient",
        "recipient_line_1",
        "recipient_line_2",
        "recipient_city",
        "recipient_state",
        "recipient_zip",
        "image_uri",
    ]

    missing_hash_cols = [col for col in hash_columns if col not in df.columns]
    if missing_hash_cols:
        raise ValueError(f"Missing required hash columns: {missing_hash_cols}")

    _config.report("Computing row hashes", logger=logger)
    df["row_hash"] = df[hash_columns].apply(_compute_row_hash, axis=1).astype("string")

    ordered_columns = hash_columns + ["reported_at", "row_hash", "batch_id"]
    df = df[ordered_columns]

    _config.report(f"Prepared dataframe for BigQuery. final_shape={df.shape}", logger=logger)
    _config.report(f"Dataframe dtypes:\n{df.dtypes}", logger=logger)

    return df


def find_bad_fixed_binary(df: pd.DataFrame):
    for col in df.columns:
        s = df[col]

        # Only care about object/string-like columns where bytes might be hiding
        if s.dtype == "object" or str(s.dtype).startswith("string"):
            mask_bytes = s.apply(lambda x: isinstance(x, (bytes, bytearray)))
            if mask_bytes.any():
                lengths = s[mask_bytes].apply(lambda x: len(x))
                bad = lengths[lengths != 16]
                print(f"\nCOLUMN {col}: bytes rows={mask_bytes.sum()}  unique_lengths={sorted(lengths.unique())}")
                if not bad.empty:
                    print("Bad (len != 16) examples:")
                    print(df.loc[bad.index, [col]].head(20))

def load_checkbook_checks_to_bigquery(df: pd.DataFrame, batch_id=None) -> int:
    _config.report(f"Starting BigQuery load. input_shape={df.shape}", logger=logger)

    df = _prepare_for_bigquery(df, batch_id=batch_id)

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    _config.report(f"Submitting load job to BigQuery table: {BQ_TABLE_ID}", logger=logger)
    load_job = client.load_table_from_dataframe(df, BQ_TABLE_ID, job_config=job_config)
    load_job.result()

    _config.report(f"BigQuery load completed successfully. rows_loaded={len(df)}", logger=logger)
    return len(df)




if __name__ == "__main__":
    # pass

    from scripts import fx_checkbook as cbio
    df = cbio.cbio_build_checks_dataframe(
    use_cache=False,
    export_csv=False,
    output_path=None,
    start_days_back=30,
)
    df_pre = _prepare_for_bigquery(df, batch_id=None)
    df_find =  find_bad_fixed_binary(df)