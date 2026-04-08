import argparse

from scripts import _config
from scripts import fx_checkbook as cbio


logger = _config.logger_configure("main")


def main():
    parser = argparse.ArgumentParser(description="Run Checkbook API data pull")
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Load checks from the pickle cache if available",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Ignore cache and fetch fresh data from API",
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        help="Write the final dataframe to a CSV file",
    )
    parser.add_argument(
        "--start-days-back",
        type=int,
        default=None,
        help="Limit API fetch to the last N days (for example, 120). Leave blank for full load.",
    )

    args = parser.parse_args()

    use_cache = True
    if args.refresh_cache:
        use_cache = False
    elif args.use_cache:
        use_cache = True

    _config.report(
        f"Starting Checkbook pull: use_cache={use_cache}, export_csv={args.export_csv}, start_days_back={args.start_days_back}",
        logger=logger,
    )

    df = cbio.cbio_build_checks_dataframe(
        use_cache=use_cache,
        export_csv=args.export_csv,
        start_days_back=args.start_days_back,
    )

    _config.report(
        f"Finished. Rows: {len(df)}, Columns: {len(df.columns)}",
        logger=logger,
    )


if __name__ == "__main__":
    main()
