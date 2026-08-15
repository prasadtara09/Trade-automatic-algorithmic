"""Compare a few pre-defined intraday breakout profiles on cached candles.

This is a research utility, not an optimiser and not an order-placement tool.
It deliberately compares a small number of understandable profiles to reduce
the risk of fitting parameters to a short historical sample.
"""

from pathlib import Path
import argparse

import pandas as pd

import backtest.engine as engine_module
import config
import strategy.score as score_module
import strategy.trend_strategy as trend_module
from backtest.engine import BacktestEngine
from indicators.indicator_engine import apply_indicators
from strategy.strategy_engine import StrategyEngine


PROFILES = {
    "balanced_retest": {
        "INTRADAY_ENTRY_START": "09:45",
        "INTRADAY_LAST_ENTRY": "14:00",
        "RSI_MIN": 55.0,
        "RSI_MAX": 72.0,
        "SHORT_RSI_MIN": 28.0,
        "SHORT_RSI_MAX": 45.0,
        "ADX_MIN": 22.0,
        "VOLUME_MULTIPLIER": 1.5,
        "MIN_SIGNAL_SCORE": 85,
        "MIN_CANDLE_BODY_PCT": 0.50,
        "RETEST_LOOKBACK": 3,
        "RETEST_TOLERANCE_ATR": 0.20,
        "RETEST_CLOSE_BUFFER_ATR": 0.05,
    },
    "trend_retest": {
        "INTRADAY_ENTRY_START": "10:00",
        "INTRADAY_LAST_ENTRY": "13:45",
        "RSI_MIN": 57.0,
        "RSI_MAX": 70.0,
        "SHORT_RSI_MIN": 30.0,
        "SHORT_RSI_MAX": 43.0,
        "ADX_MIN": 25.0,
        "VOLUME_MULTIPLIER": 1.5,
        "MIN_SIGNAL_SCORE": 90,
        "MIN_CANDLE_BODY_PCT": 0.55,
        "RETEST_LOOKBACK": 3,
        "RETEST_TOLERANCE_ATR": 0.20,
        "RETEST_CLOSE_BUFFER_ATR": 0.10,
    },
    "selective_retest": {
        "INTRADAY_ENTRY_START": "10:00",
        "INTRADAY_LAST_ENTRY": "13:45",
        "RSI_MIN": 58.0,
        "RSI_MAX": 68.0,
        "SHORT_RSI_MIN": 32.0,
        "SHORT_RSI_MAX": 42.0,
        "ADX_MIN": 25.0,
        "VOLUME_MULTIPLIER": 1.75,
        "MIN_SIGNAL_SCORE": 90,
        "MIN_CANDLE_BODY_PCT": 0.60,
        "RETEST_LOOKBACK": 2,
        "RETEST_TOLERANCE_ATR": 0.15,
        "RETEST_CLOSE_BUFFER_ATR": 0.10,
    },
}


def activate_profile(settings):
    """Apply a profile to modules that import configuration constants."""
    for name, value in settings.items():
        setattr(config, name, value)
        for module in (engine_module, score_module, trend_module):
            if hasattr(module, name):
                setattr(module, name, value)


def profile_summary(name, frames):
    trades = []
    for symbol, frame in frames:
        trades.extend(BacktestEngine().run(symbol, frame, StrategyEngine()))

    winners = [trade.pnl for trade in trades if trade.pnl > 0]
    losers = [trade.pnl for trade in trades if trade.pnl <= 0]
    gross_profit = sum(winners)
    gross_loss = -sum(losers)
    return {
        "Profile": name,
        "Symbols": len(frames),
        "Trades": len(trades),
        "WinRatePct": round(100 * len(winners) / len(trades), 2) if trades else 0.0,
        "NetPnL": round(sum(trade.pnl for trade in trades), 2),
        "ProfitFactor": round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
        "AverageTrade": round(sum(trade.pnl for trade in trades) / len(trades), 2) if trades else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Compare intraday strategy profiles on cached candles.")
    parser.add_argument(
        "--max-symbols", type=int, default=None,
        help="Limit the number of cached symbols for a quick smoke test.",
    )
    args = parser.parse_args()

    paths = sorted(Path("cache").glob("*_15m.parquet"))
    if not paths:
        raise SystemExit("No cached candles found. Run the scanner/data download first.")
    if args.max_symbols is not None:
        paths = paths[:args.max_symbols]
    Path("reports").mkdir(exist_ok=True)

    frames = []
    for path in paths:
        try:
            frames.append((f"{path.stem}.NS", apply_indicators(pd.read_parquet(path))))
        except Exception as error:
            print(f"Skipping {path.name}: {error}")

    print(f"Loaded {len(frames)} cached symbols. Comparing {len(PROFILES)} profiles...", flush=True)

    summaries = []
    for name, settings in PROFILES.items():
        print(f"Running {name}...", flush=True)
        activate_profile(settings)
        summaries.append(profile_summary(name, frames))

        # Preserve partial work if the full-universe run is interrupted.
        pd.DataFrame(summaries).to_csv("reports/profile_comparison.csv", index=False)

    report = pd.DataFrame(summaries).sort_values(
        ["ProfitFactor", "NetPnL"], ascending=False
    )
    report.to_csv("reports/profile_comparison.csv", index=False)
    print(report.to_string(index=False))
    print("\nSaved comparison to reports/profile_comparison.csv")


if __name__ == "__main__":
    main()
