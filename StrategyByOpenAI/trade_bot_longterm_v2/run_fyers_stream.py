"""Stream live FYERS prices for the current swing basket or a supplied watchlist.

This script subscribes to market data only. It never submits orders.
"""

from __future__ import annotations

import argparse
import csv
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import pandas as pd

from broker.websocket import FyersDataStream, MarketTick
from config import (
    FYERS_WS_LITE_MODE,
    S3_BUCKET,
    S3_TARGETS_KEY,
    download_s3_targets,
    s3_targets_enabled,
)
from data.universe import NIFTY200


DEFAULT_TARGETS = Path("reports/swing_rotation_targets.csv")


def _target_symbols(path: Path) -> list[str]:
    if not path.exists():
        raise ValueError(
            f"{path} was not found. Run python3 run_swing_rotation_targets.py first, or pass --symbols."
        )
    targets = pd.read_csv(path)
    if "Symbol" not in targets.columns:
        raise ValueError(f"{path} does not contain a Symbol column.")
    return targets["Symbol"].dropna().astype(str).tolist()


def _symbols_from_csv(value: str) -> list[str]:
    return [symbol.strip() for symbol in value.split(",") if symbol.strip()]


def _tick_time(tick: MarketTick) -> str:
    if tick.timestamp is None:
        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")
    return datetime.fromtimestamp(tick.timestamp, ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")


def _append_tick(writer: csv.DictWriter | None, file_handle, tick: MarketTick) -> None:
    if writer is None:
        return
    row = asdict(tick)
    row["raw"] = str(row["raw"])
    writer.writerow(row)
    file_handle.flush()


def _resolve_symbols(args: argparse.Namespace) -> Iterable[str]:
    if args.symbols:
        return _symbols_from_csv(args.symbols)
    if args.nifty200:
        return NIFTY200
    if s3_targets_enabled():
        # Do not fall back to a possibly stale image-local CSV: a configured
        # S3 bucket is the source of truth shared by the scan and stream jobs.
        download_s3_targets(args.targets)
        print(f"Downloaded target basket from s3://{S3_BUCKET}/{S3_TARGETS_KEY}")
    return _target_symbols(args.targets)


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor live FYERS DataSocket prices without trading.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--symbols", help="Comma-separated FYERS or Yahoo symbols, e.g. NSE:TCS-EQ,INFY.NS")
    source.add_argument("--nifty200", action="store_true", help="Subscribe to the local NIFTY 200 universe.")
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS, help="Target-basket CSV used when no source is supplied.")
    parser.add_argument(
        "--lite",
        action="store_true",
        default=None,
        help="Use LTP-only mode instead of full SymbolUpdate messages.",
    )
    parser.add_argument("--duration", type=float, help="Optional number of seconds before the stream stops.")
    parser.add_argument("--output", type=Path, help="Optional CSV file to append live ticks to.")
    args = parser.parse_args()

    symbols = list(_resolve_symbols(args))
    output_handle = None
    writer = None
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        output_handle = args.output.open("w", newline="")
        writer = csv.DictWriter(output_handle, fieldnames=list(MarketTick.__dataclass_fields__))
        writer.writeheader()

    def on_tick(tick: MarketTick) -> None:
        print(f"{_tick_time(tick)}  {tick.symbol:<24} LTP={tick.ltp}", flush=True)
        _append_tick(writer, output_handle, tick)

    def on_status(status: str) -> None:
        print(status, flush=True)

    lite_mode = FYERS_WS_LITE_MODE if args.lite is None else args.lite
    stream = FyersDataStream(symbols, lite_mode=lite_mode, on_tick=on_tick, on_status=on_status)
    print(f"Starting FYERS data stream for {len(stream.symbols)} symbols. No orders will be sent.")
    try:
        stream.start()
        started = time.monotonic()
        while args.duration is None or time.monotonic() - started < args.duration:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping FYERS data stream.")
    finally:
        stream.stop()
        if output_handle:
            output_handle.close()


if __name__ == "__main__":
    main()
