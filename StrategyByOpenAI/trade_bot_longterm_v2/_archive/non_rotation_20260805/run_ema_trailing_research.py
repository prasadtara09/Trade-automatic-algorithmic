"""Test EMA-pullback exits with and without a break-even trailing stop."""

import argparse
from pathlib import Path

import pandas as pd

from backtest.swing_portfolio import SwingPortfolioBacktest, SwingPortfolioSettings
from data.downloader import download
from data.universe import NIFTY200
from strategy.swing_features import daily_indicators
from strategy.swing_variants import EmaPullbackEntry


PROFILES = {
    "EMA baseline": SwingPortfolioSettings(),
    "EMA breakeven trail (1 ATR)": SwingPortfolioSettings(breakeven_trigger_atr=1.0),
}


def _period_frames(frames, start=None, end=None):
    result = {}
    for symbol, frame in frames.items():
        subset = frame
        if start is not None:
            subset = subset[subset.index >= start]
        if end is not None:
            subset = subset[subset.index <= end]
        if len(subset) >= 60:
            result[symbol] = subset
    return result


def _result(frames, settings):
    portfolio = SwingPortfolioBacktest(settings)
    trades, _ = portfolio.run(frames, EmaPullbackEntry())
    winners = [trade.pnl for trade in trades if trade.pnl > 0]
    losers = [trade.pnl for trade in trades if trade.pnl <= 0]
    return {
        "Trades": len(trades),
        "WinRatePct": round(100 * len(winners) / len(trades), 2) if trades else 0.0,
        "NetPnL": round(sum(trade.pnl for trade in trades), 2),
        "ProfitFactor": round(sum(winners) / -sum(losers), 2) if losers else 0.0,
        "FinalEquity": round(portfolio.cash, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="Compare EMA trailing-stop variants.")
    parser.add_argument("--max-symbols", type=int, default=None, help="Use a small sample first.")
    parser.add_argument("--period", default="2y", help="Daily history period for missing cache files.")
    args = parser.parse_args()

    symbols = NIFTY200[:args.max_symbols] if args.max_symbols else NIFTY200
    frames = {}
    for number, symbol in enumerate(symbols, start=1):
        try:
            print(f"[{number}/{len(symbols)}] {symbol}", flush=True)
            frames[symbol] = daily_indicators(download(symbol, period=args.period, interval="1d"))
        except Exception as error:
            print(f"Skipping {symbol}: {error}")
    if not frames:
        raise SystemExit("No daily candles were available.")

    all_dates = sorted({timestamp for frame in frames.values() for timestamp in frame.index})
    split_date = all_dates[int(len(all_dates) * 0.70)]
    earlier = _period_frames(frames, end=split_date)
    later = _period_frames(frames, start=split_date)

    rows = []
    for name, settings in PROFILES.items():
        print(f"Testing {name}...", flush=True)
        full = _result(frames, settings)
        first = _result(earlier, settings)
        holdout = _result(later, settings)
        rows.append({
            "Profile": name,
            **{f"Full{key}": value for key, value in full.items()},
            **{f"Earlier{key}": value for key, value in first.items()},
            **{f"Later{key}": value for key, value in holdout.items()},
        })

    report = pd.DataFrame(rows).sort_values(["LaterProfitFactor", "LaterNetPnL"], ascending=False)
    Path("reports").mkdir(exist_ok=True)
    report.to_csv("reports/ema_trailing_comparison.csv", index=False)
    print("\n" + report.to_string(index=False))
    print("Saved reports/ema_trailing_comparison.csv")


if __name__ == "__main__":
    main()
