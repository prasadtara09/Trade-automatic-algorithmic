from pathlib import Path

import pandas as pd

from config import SCANNER_CACHE_ONLY, SCANNER_MAX_SIGNALS
from data.universe import NIFTY200, UNIVERSE
from scanner.scanner import Scanner


def main():
    if not NIFTY200:
        print("Official NIFTY 200 list is not refreshed; scanning the bundled development watchlist.")
        print("Run `python update_universe.py` before a full NIFTY 200 scan.")
    scanner = Scanner()
    signals = scanner.scan_latest(UNIVERSE, limit=SCANNER_MAX_SIGNALS)
    rows = [
        {
            "Symbol": signal.symbol,
            "Timestamp": signal.timestamp,
            "Side": signal.side,
            "Score": signal.score,
            "Entry": signal.entry,
            "Stoploss": signal.stoploss,
            "Target": signal.target,
            "Strategy": signal.strategy,
            "Remarks": signal.remarks,
        }
        for signal in signals
    ]
    columns = [
        "Symbol", "Timestamp", "Side", "Score", "Entry", "Stoploss",
        "Target", "Strategy", "Remarks",
    ]
    report = pd.DataFrame(rows, columns=columns)
    Path("reports").mkdir(exist_ok=True)
    report.to_csv("reports/latest_signals.csv", index=False)

    stats = scanner.last_scan_stats
    print(
        f"Scan summary: {stats['scanned']} scanned, {stats['missing_data']} missing data, "
        f"{stats['filtered_out']} filtered out, {stats['outside_entry_window']} outside the entry window, "
        f"{stats['errors']} errors out of {stats['requested']} symbols."
    )
    if SCANNER_CACHE_ONLY and stats["missing_data"]:
        print("Cache-only mode is active; download or fetch broker candles before those symbols can be scanned.")

    if report.empty:
        print("No current signals met every configured filter.")
    else:
        print(report.to_string(index=False))


if __name__ == "__main__":
    main()
