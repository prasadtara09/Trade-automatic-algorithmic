"""Print a paper-trading target basket for the validated swing rotation model.

This script does not place broker orders.  It is intended to be run after the
final daily candle is complete, normally after Friday's market close, with any
changes executed no earlier than the next trading session's open.
"""

import argparse
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from config import MAX_OPEN_POSITIONS, S3_BUCKET, S3_TARGETS_KEY, s3_targets_enabled, upload_s3_targets
from data.downloader import download
from data.universe import NIFTY200
from data.yahoo_history import YahooHistoryClient, YahooHistoryError
from strategy.momentum_rotation import MODEL_NAME, select_rotation_targets
from strategy.swing_features import daily_indicators


TARGET_COLUMNS = [
    "Rank",
    "Symbol",
    "AsOf",
    "Close",
    "RS20Pct",
    "SMA50",
    "SMA200",
    "MaxAllocationPct",
    "Model",
]


def main():
    parser = argparse.ArgumentParser(description="Create paper-only weekly swing rotation targets.")
    parser.add_argument(
        "--show-any-day",
        action="store_true",
        help="Show the current ranking even when the completed session is not Friday.",
    )
    parser.add_argument(
        "--refresh-current",
        action="store_true",
        help="Refresh the latest daily candles before calculating targets.",
    )
    args = parser.parse_args()

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    # A cache made before the close can contain a partial daily candle.  On a
    # Friday after the close safeguard, refresh only the latest 40 sessions
    # and merge them into the cached two-year history.  This keeps the weekly
    # signal based on Friday's final candle without re-downloading all history.
    refresh_current = args.refresh_current or (
        now.weekday() == 4 and now.time() >= time(15, 45)
    )
    history_client = YahooHistoryClient() if refresh_current else None
    frames = {}
    refresh_failures = []
    for number, symbol in enumerate(NIFTY200, start=1):
        try:
            print(f"[{number}/{len(NIFTY200)}] {symbol}", flush=True)
            raw = download(symbol, period="2y", interval="1d")
            if history_client is not None:
                try:
                    latest = history_client.fetch_daily(symbol, days=40)
                    raw = pd.concat([raw, latest]).sort_index()
                    raw = raw[~raw.index.duplicated(keep="last")]
                except YahooHistoryError as error:
                    refresh_failures.append((symbol, str(error)))
            frames[symbol] = daily_indicators(raw)
        except Exception as error:
            print(f"Skipping {symbol}: {error}")
    if not frames:
        raise SystemExit("No daily candles were available.")

    as_of, targets = select_rotation_targets(frames, max_positions=MAX_OPEN_POSITIONS)
    # Keep the header even if no symbol qualifies. An empty Friday basket is
    # an intentional instruction to hold no new positions, never a reason to
    # keep a stale basket in the stream container.
    report = pd.DataFrame(targets, columns=TARGET_COLUMNS)
    Path("reports").mkdir(exist_ok=True)
    target_path = Path("reports/swing_rotation_targets.csv")
    report.to_csv(target_path, index=False)

    print(f"\nModel: {MODEL_NAME}")
    print(f"Completed session used: {as_of.date()}")
    print("Orders are paper-only and must use the next trading session's open; never the signal close.")
    if refresh_current:
        if refresh_failures:
            print(f"Warning: {len(refresh_failures)} latest-candle refreshes failed; no order should be placed until rerun cleanly.")
            return
        print("Friday daily candles were refreshed before ranking.")
    if as_of.weekday() != 4 and not args.show_any_day:
        print("This is not a Friday close, so no weekly rebalance order is due. Use --show-any-day only to inspect rankings.")
        return
    if report.empty:
        print("No stocks currently meet the model's long-only trend and momentum filters; saved an empty basket.")
    else:
        print(report.to_string(index=False))
        print("Saved reports/swing_rotation_targets.csv")

    # Inspection and catch-up runs must never replace the production basket.
    # Only the intended Friday-after-close job publishes selected holdings or
    # an explicit empty basket for the stream container to consume.
    publish_to_s3 = (
        not args.show_any_day
        and now.weekday() == 4
        and now.time() >= time(15, 45)
        and as_of.weekday() == 4
    )
    if publish_to_s3 and s3_targets_enabled():
        upload_s3_targets(target_path)
        print(f"Uploaded target basket to s3://{S3_BUCKET}/{S3_TARGETS_KEY}")


if __name__ == "__main__":
    main()
