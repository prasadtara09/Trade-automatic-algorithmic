"""Compare several long-only daily swing entry rules on one capped portfolio."""

import argparse
from pathlib import Path

import pandas as pd

from backtest.swing_portfolio import SwingPortfolioBacktest
from data.downloader import download
from data.universe import NIFTY200
from strategy.swing_features import daily_indicators
from strategy.swing_variants import (
    BollingerReversionEntry,
    BollingerStrongTrendDipEntry,
    EmaPullbackEntry,
    MaCrossoverEntry,
    RsiMeanReversionEntry,
    Rsi2StrongTrendDipEntry,
    RelativeStrengthPullbackEntry,
    SmaBreakoutEntry,
)


STRATEGIES = (
    EmaPullbackEntry(),
    RsiMeanReversionEntry(),
    BollingerReversionEntry(),
    MaCrossoverEntry(),
    SmaBreakoutEntry(),
    RelativeStrengthPullbackEntry(),
    Rsi2StrongTrendDipEntry(),
    BollingerStrongTrendDipEntry(),
)


def _result(strategy, frames):
    portfolio = SwingPortfolioBacktest()
    trades, equity = portfolio.run(frames, strategy)
    winners = [trade.pnl for trade in trades if trade.pnl > 0]
    losers = [trade.pnl for trade in trades if trade.pnl <= 0]
    gross_profit = sum(winners)
    gross_loss = -sum(losers)
    return {
        "Trades": len(trades),
        "WinRatePct": round(100 * len(winners) / len(trades), 2) if trades else 0.0,
        "NetPnL": round(sum(trade.pnl for trade in trades), 2),
        "ProfitFactor": round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
        "AverageTrade": round(sum(trade.pnl for trade in trades) / len(trades), 2) if trades else 0.0,
        "FinalEquity": round(portfolio.cash, 2),
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


def summary(strategy, frames, split_date):
    full = _result(strategy, frames)
    earlier = _result(strategy, _period_frames(frames, end=split_date))
    later = _result(strategy, _period_frames(frames, start=split_date))
    return {
        "Strategy": strategy.name,
        **{f"Full{key}": value for key, value in full.items()},
        **{f"Earlier{key}": value for key, value in earlier.items()},
        **{f"Later{key}": value for key, value in later.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Compare long-only swing strategies fairly.")
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
    print(f"Holdout begins on {split_date.date()} (latest 30% of available dates).", flush=True)

    results = []
    for strategy in STRATEGIES:
        print(f"Testing {strategy.name}...", flush=True)
        results.append(summary(strategy, frames, split_date))

    report = pd.DataFrame(results).sort_values(["LaterProfitFactor", "LaterNetPnL"], ascending=False)
    Path("reports").mkdir(exist_ok=True)
    report.to_csv("reports/swing_strategy_comparison.csv", index=False)
    print("\n" + report.to_string(index=False))
    print("Saved reports/swing_strategy_comparison.csv")


if __name__ == "__main__":
    main()
