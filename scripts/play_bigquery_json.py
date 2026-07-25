from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from google.cloud import bigquery
from google.oauth2 import service_account

from scripts import _config


logger = _config.logger_configure("play_bigquery_json")

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


def _report(message, level="info"):
    _config.report(message, logger=logger, level=level)


def _compute_row_hash(record: dict) -> str:
    values = ["" if record.get(col) is None else str(record.get(col)) for col in HISTORY_COLUMNS]
    payload = "|".join(values)
    return sha256(payload.encode("utf-8")).hexdigest()


def _add_metadata(records: list[dict], batch_id=None) -> list[dict]:
    reported_at = datetime.now(timezone.utc).isoformat()

    enriched = []
    for record in records:
        row = dict(record)
        row["reported_at"] = reported_at
        row["batch_id"] = batch_id
        row["row_hash"] = _compute_row_hash(row)
        enriched.append(row)

    return enriched


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

    _report(
        f"Filtered records. incoming={len(records)}, new_or_changed={len(new_records)}"
    )
    return new_records


def load_checkbook_records_to_bigquery(records: list[dict], batch_id=None) -> int:
    _report(f"Starting JSON BigQuery load. incoming_records={len(records)}")

    if not records:
        _report("No records to load", level="warning")
        return 0

    records = _add_metadata(records, batch_id=batch_id)
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

    _report(f"BigQuery JSON load completed successfully. rows_loaded={len(records)}")
    return len(records)

if __name__ == "__main__":
    # pass

    from scripts import fx_checkbook as cbio
    # jdata = cbio.cbio_build_checks_json(
    # use_cache=False,
    # start_days_back=30,
    # )
    jdata = cbio.cbio_build_checks_json(use_cache=True )
    load_checkbook_records_to_bigquery(jdata, batch_id = None)
    # df_pre = _prepare_for_bigquery(df, batch_id=None)
    # df_find =  find_bad_fixed_binary(df)