import pickle
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from scripts import _config


cbio_keys = _config.get_cbio_keys()
logger = _config.logger_configure("fx_checkbook")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_EXPORTS = PROJECT_ROOT / "data_exports"


def _cache_name_for_days_back(start_days_back):
    if start_days_back is None:
        return "checks_all.pkl"
    return f"checks_all_last_{start_days_back}_days.pkl"


def cbio_get_sent_received_list(auth, params=None, partner_name=None, start_days_back=None):
    if params is None:
        params = {"page": 1}

    url_base = "https://api.checkbook.io/v3/check"
    headers = {
        "accept": "application/json",
        "Authorization": auth,
    }

    page = 1
    pages = 2
    params = dict(params)
    params.update({"page": 1})

    if start_days_back is not None:
        start_date = (datetime.today() - timedelta(days=start_days_back)).strftime("%Y-%m-%d")
        params["start_date"] = start_date

    checks = []

    if partner_name:
        _config.report(
            f"Fetching partner: {partner_name} (start_days_back={start_days_back})",
            logger=logger,
        )

    while page < pages:
        response = requests.get(url_base, params=params, headers=headers)
        response.raise_for_status()

        rspj = response.json()
        page = rspj["page"]
        pages = rspj["pages"]
        total = rspj.get("total", 0)

        _config.report(f"  page {page} of {pages} ({total} records)", logger=logger)

        params.update({"page": page + 1})

        if total > 0:
            checks.extend(rspj.get("checks", []))

    return checks


def cbio_get_sent_received_list_all_partners(start_days_back=None):
    checks_all = []
    partner_count = len(cbio_keys)

    _config.report(
        f"Starting fetch for {partner_count} partner(s), start_days_back={start_days_back}",
        logger=logger,
    )

    for idx, partner_name in enumerate(cbio_keys, start=1):
        _config.report(f"Partner {idx}/{partner_count}: {partner_name}", logger=logger)
        checks_partner = cbio_get_sent_received_list(
            cbio_keys[partner_name],
            partner_name=partner_name,
            start_days_back=start_days_back,
        )
        checks_all.extend(checks_partner)

    _config.report(f"Finished fetching all partners. Total raw checks: {len(checks_all)}", logger=logger)
    return checks_all


def cbio_build_checks_dataframe(
    use_cache=True,
    export_csv=False,
    output_path=None,
    start_days_back=None,
):
    cache_name = _cache_name_for_days_back(start_days_back)
    cache_path = DATA_EXPORTS / cache_name
    DATA_EXPORTS.mkdir(parents=True, exist_ok=True)

    _config.report(
        f"Build dataframe started. use_cache={use_cache}, export_csv={export_csv}, start_days_back={start_days_back}",
        logger=logger,
    )
    _config.report(f"Using cache file: {cache_path}", logger=logger)

    if use_cache and cache_path.exists():
        _config.report(f"Loading checks from cache: {cache_path}", logger=logger)
        with open(cache_path, "rb") as f:
            checks_all = pickle.load(f)
        _config.report(f"Loaded {len(checks_all)} checks from cache", logger=logger)
    else:
        _config.report("Fetching checks from API", logger=logger)
        checks_all = cbio_get_sent_received_list_all_partners(start_days_back=start_days_back)
        with open(cache_path, "wb") as f:
            pickle.dump(checks_all, f)
        _config.report(f"Saved cache to: {cache_path}", logger=logger)

    df_checks = pd.json_normalize(checks_all)
    _config.report(f"Normalized dataframe shape: {df_checks.shape}", logger=logger)

    checks_col_order = [
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
        "recipient.line_1",
        "recipient.line_2",
        "recipient.city",
        "recipient.state",
        "recipient.zip",
        "image_uri",
    ]

    api_only_cols = sorted(set(df_checks.columns) - set(checks_col_order))
    if api_only_cols:
        _config.report(
            f"New API columns detected that are not in checks_col_order: {api_only_cols}",
            logger=logger,
            level="warning",
        )

    existing_cols = [col for col in checks_col_order if col in df_checks.columns]
    df_checks = df_checks[existing_cols]
    _config.report(f"Filtered dataframe shape: {df_checks.shape}", logger=logger)

    if export_csv:
        if output_path is None:
            output_path = DATA_EXPORTS / f"checks_download_all_{pd.Timestamp.today().strftime('%Y-%m-%d')}.csv"
        else:
            output_path = Path(output_path)

        df_checks.to_csv(output_path, index=True)
        _config.report(f"Exported CSV to: {output_path}", logger=logger)

    _config.report("Build dataframe finished", logger=logger)
    return df_checks






# Example Query Params.
# url_prod_1 = "https://api.checkbook.io/v3/check/digital"
# url_prod_from = "https://dapi.checkbook.io/v3/check?start_date=2023-09-01"
# url_prod_page = "https://dapi.checkbook.io/v3/check?page=2"
# url_prod_page_from = "https://demo.checkbook.io/v3/check?page=2&start_date=2023-09-01"






"""

params_all = {
    "q": "string",
    "page": "int of page number to get",
    "per_page": "int of 10, 25, 50",
    "start_date": 'string of iso date',
    "end_date": "string of iso date",
    "direction": "INCOMING OR OUTGOING",
    "sort": "see docs",
    "status": "str [PAID, IN_PROCESS, UNPAID, VOID, EXPIRED, PRINTED, MAILED, FAILED, REFUNDED "

}




rspt = response.text
rspj = response.json()
# print(rsp)

page = rspj['page']
pages = rspj['pages']
checks = rspj['checks']

checks.extend(checks)


while page < pages:
    url_prod_pag = f"https://api.checkbook.io/v3/check?page={page+1}"
    response_pag = requests.get(url_prod_pag, headers=headers)
    rsp_j = response_pag.json()
    page = rsp_j['page']
    checks_ = rsp_j['checks']
"""