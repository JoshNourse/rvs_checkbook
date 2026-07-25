from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from scripts import _config


logger = _config.logger_configure("play_bigquery_history")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_EXPORTS = PROJECT_ROOT / "data_exports"
BQ_TABLE_ID = "rvshare-analytics.seeds_insurance.checkbook_checks"

bq_keys = _config.get_bigquery_keys()
credentials = service_account.Credentials.from_service_account_info(bq_keys)

client = bigquery.Client(
    credentials=credentials,
    project=credentials.project_id,
)

HISTORY_COLUMNS = [
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


def _clean_text_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    return value


def _clean_record(record: dict) -> dict:
    return {key: _clean_text_value(value) for key, value in record.items()}


def _report(message, level="info"):
    _config.report(message, logger=logger, level=level)


# def _extract_reported_at_from_filename(csv_path: str | Path) -> datetime:
#     csv_path = Path(csv_path)
#     match = re.search(r"(\d{4}-\d{2}-\d{2})", csv_path.name)
#     if not match:
#         raise ValueError(f"Could not extract date from filename: {csv_path.name}")
#
#     file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
#     return file_date.replace(tzinfo=timezone.utc)

def _extract_reported_at_from_filename(csv_path: str | Path) -> str:
    csv_path = Path(csv_path)
    match = re.search(r"(\d{4}-\d{2}-\d{2})", csv_path.name)
    if not match:
        raise ValueError(f"Could not extract date from filename: {csv_path.name}")

    file_date = datetime.strptime(match.group(1), "%Y-%m-%d")
    return file_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _compute_row_hash(record: dict) -> str:
    values = ["" if record.get(col) is None else str(record.get(col)) for col in HISTORY_COLUMNS]
    payload = "|".join(values)
    return sha256(payload.encode("utf-8")).hexdigest()


def _normalize_record(record: dict) -> dict:
    row = dict(record)

    recipient_value = row.pop("recipient", None)
    if isinstance(recipient_value, dict):
        row["recipient"] = None
        row["recipient_line_1"] = recipient_value.get("line_1")
        row["recipient_line_2"] = recipient_value.get("line_2")
        row["recipient_city"] = recipient_value.get("city")
        row["recipient_state"] = recipient_value.get("state")
        row["recipient_zip"] = recipient_value.get("zip")
    else:
        row["recipient"] = recipient_value
        row["recipient_line_1"] = None
        row["recipient_line_2"] = None
        row["recipient_city"] = None
        row["recipient_state"] = None
        row["recipient_zip"] = None

    return row


def _add_metadata(records: list[dict], reported_at: datetime, batch_id=None) -> list[dict]:
    enriched = []
    for record in records:
        row = _normalize_record(record)
        row["reported_at"] = reported_at
        row["batch_id"] = batch_id
        row["row_hash"] = _compute_row_hash(row)
        enriched.append(_clean_record(row))

    return enriched


import json


def find_unserializable_records(records: list[dict]) -> pd.DataFrame:
    bad_records = []

    for idx, record in enumerate(records):
        try:
            json.dumps(record, ensure_ascii=False)
        except Exception as exc:
            bad_records.append(
                {
                    "record_index": idx,
                    "error": str(exc),
                    **record,
                }
            )

    result = pd.DataFrame(bad_records)
    _report(f"Unserializable records found: {len(result)}")

    if not result.empty:
        _report(f"Sample unserializable records:\n{result.head(10).to_string()}")

    return result


print(f"BEFORE _contains_suspicious_text {8}")

def _contains_suspicious_text(value):
    if not isinstance(value, str):
        return False

    # after cleaning, any of these should be gone
    return any(
        ch in value
        for ch in ("\n", "\r", "\t")
    ) or bool(re.search(r"[\x00-\x1f\x7f]", value))


def find_suspicious_history_csv_rows(csv_path: str | Path, mode: str = "raw") -> pd.DataFrame:
    csv_path = Path(csv_path)
    _report(f"Inspecting CSV for suspicious text: {csv_path} (mode={mode})")

    df = pd.read_csv(csv_path)

    rename_map = {
        "recipient.line_1": "recipient_line_1",
        "recipient.line_2": "recipient_line_2",
        "recipient.city": "recipient_city",
        "recipient.state": "recipient_state",
        "recipient.zip": "recipient_zip",
    }
    df = df.rename(columns=rename_map)

    drop_cols = ["Unnamed: 0", "address", "claim_number", "partner"]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns])

    if mode == "cleaned":
        records = df.to_dict(orient="records")
        records = [_clean_record(_normalize_record(record)) for record in records]
        df = pd.DataFrame(records)

    suspicious_rows = []

    for idx, row in df.iterrows():
        bad_columns = []

        for col, value in row.items():
            if _contains_suspicious_text(value):
                bad_columns.append(col)

        if bad_columns:
            suspicious_rows.append(
                {
                    "csv_row_index": idx,
                    "bad_columns": ", ".join(bad_columns),
                    **row.to_dict(),
                }
            )

    result = pd.DataFrame(suspicious_rows)
    _report(f"Suspicious rows found: {len(result)}")

    if not result.empty:
        _report(f"Sample suspicious rows:\n{result.head(10).to_string()}")

    return result


def _get_existing_hashes() -> dict[str, str]:
    query = f"""
        SELECT id, row_hash
        FROM `{BQ_TABLE_ID}`
        QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY reported_at DESC) = 1
    """
    _report("Querying existing BigQuery hashes")
    rows = client.query(query).result()

    existing = {}
    for row in rows:
        existing[str(row.id)] = row.row_hash

    _report(f"Loaded {len(existing)} existing row hashes")
    return existing


def filter_new_and_changed_records(records: list[dict]) -> list[dict]:
    existing_hashes = _get_existing_hashes()
    new_records = []

    for record in records:
        record_id = str(record.get("id"))
        current_hash = record.get("row_hash")
        previous_hash = existing_hashes.get(record_id)

        if previous_hash is None or previous_hash != current_hash:
            new_records.append(record)

    _report(f"Filtered records. incoming={len(records)}, new_or_changed={len(new_records)}")
    return new_records


def load_checkbook_history_csv(csv_path: str | Path, batch_id=None) -> int:
    csv_path = Path(csv_path)
    reported_at = _extract_reported_at_from_filename(csv_path)


    _report(f"Loading history CSV: {csv_path}")
    # _report(f"Using reported_at from filename: {reported_at.isoformat()}")
    _report(f"Using reported_at from filename: {reported_at}")

    df = pd.read_csv(csv_path)

    rename_map = {
        "recipient.line_1": "recipient_line_1",
        "recipient.line_2": "recipient_line_2",
        "recipient.city": "recipient_city",
        "recipient.state": "recipient_state",
        "recipient.zip": "recipient_zip",
    }
    df = df.rename(columns=rename_map)

    drop_cols = ["Unnamed: 0", "address", "claim_number", "partner"]
    df = df.drop(columns=[col for col in drop_cols if col in df.columns])

    _report(f"CSV columns: {list(df.columns)}")
    _report(f"Sample rows:\n{df.head(3).to_string()}")
    _report(f"Read CSV shape: {df.shape}")

    records = df.to_dict(orient="records")
    _report(f"Converted CSV to {len(records)} record(s)")

    records = _add_metadata(records, reported_at=reported_at, batch_id=batch_id)
    bad = find_unserializable_records(records)
    records = filter_new_and_changed_records(records)

    if not records:
        _report("No new or changed records detected. Nothing to load.")
        return 0

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    _report(f"Submitting {len(records)} record(s) to BigQuery table: {BQ_TABLE_ID}")
    load_job = client.load_table_from_json(records, BQ_TABLE_ID, job_config=job_config)
    load_job.result()

    _report(f"CSV history load completed successfully. rows_loaded={len(records)}")
    return len(records)


if __name__ == "__main__":
    # Example ad-hoc call:
    load_checkbook_history_csv(DATA_EXPORTS / "checks_download_all_2025-12-02.csv")

    # suspicious = find_suspicious_history_csv_rows(
    #     DATA_EXPORTS / "checks_download_all_2025-11-13.csv",
    #     mode="cleaned",
    # )
    # print(suspicious.head(20).to_string())


    pass