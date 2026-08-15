"""Run the long-only daily swing strategy across cached/downloaded NIFTY stocks."""

import argparse
import json
from pathlib import Path

import pandas as pd
import yfinance as yf

from backtest.swing_portfolio import SwingPortfolioBacktest
from config import (
    SWING_MARKET_FAST_EMA,
    SWING_MARKET_SLOW_EMA,
    SWING_REQUIRE_MARKET_REGIME,
    SWING_REQUIRE_STOCK_LONG_TREND,
)
from data.cache import load_cache, save_cache
from data.downloader import download
from data.universe import NIFTY200
from indicators.ema import ema
from strategy.swing_features import daily_indicators
from strategy.swing_pullback import DailyTrendPullbackStrategy


def _regime_from_close(close):
    data = pd.DataFrame({"Close": close}).dropna()
    data["EMA_FAST"] = ema(data["Close"], SWING_MARKET_FAST_EMA)
    data["EMA_SLOW"] = ema(data["Close"], SWING_MARKET_SLOW_EMA)
    return (
        (data["Close"] > data["EMA_SLOW"])
        & (data["EMA_FAST"] > data["EMA_SLOW"])
        & (data["EMA_FAST"] > data["EMA_FAST"].shift(5))
    )


def _nifty200_breadth_regime(symbols):
    """Fallback broad-market regime from equal-weighted cached NIFTY 200 data."""
    normalized_closes = []
    for symbol in symbols:
        data = load_cache(symbol, "1d")
        if data is None or data.empty or "Close" not in data:
            continue
        close = data["Close"].dropna()
        if not close.empty:
            normalized_closes.append(close / close.iloc[0])
    if not normalized_closes:
        raise RuntimeError("No cached daily candles available for the market-regime fallback")
    breadth_index = pd.concat(normalized_closes, axis=1).mean(axis=1)
    return _regime_from_close(breadth_index)


def load_nifty50_regime(period, symbols):
    """Return a NIFTY 50 regime, with cached NIFTY 200 breadth as fallback."""
    symbol = "^NSEI"
    data = load_cache(symbol, "1d")
    if data is None:
        print("Downloading NIFTY 50 daily benchmark...", flush=True)
        data = yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        if data.empty:
            print("NIFTY 50 download unavailable; using NIFTY 200 breadth regime.", flush=True)
            return _nifty200_breadth_regime(symbols), "NIFTY200_BREADTH"
        data = data.dropna()
        save_cache(data, symbol, "1d")

    return _regime_from_close(data["Close"]), "NIFTY50"


def main():
    parser = argparse.ArgumentParser(description="Long-only daily swing research on NIFTY 200.")
    parser.add_argument("--max-symbols", type=int, default=None, help="Use a small sample first.")
    parser.add_argument("--period", default="2y", help="Daily history period, e.g. 2y or 1y.")
    parser.add_argument("--without-market-filter", action="store_true", help="Compare against entries without the NIFTY 50 regime filter.")
    args = parser.parse_args()

    symbols = NIFTY200[:args.max_symbols] if args.max_symbols else NIFTY200
    if not symbols:
        raise SystemExit("NIFTY 200 list is missing. Run python3 update_universe.py first.")

    strategy = DailyTrendPullbackStrategy()
    frames = {}
    loaded = 0
    use_market_filter = SWING_REQUIRE_MARKET_REGIME and not args.without_market_filter
    if use_market_filter:
        market_regime, market_regime_source = load_nifty50_regime(args.period, symbols)
    else:
        market_regime, market_regime_source = None, "DISABLED"
    for number, symbol in enumerate(symbols, start=1):
        try:
            print(f"[{number}/{len(symbols)}] {symbol}", flush=True)
            data = download(symbol, period=args.period, interval="1d")
            frame = daily_indicators(data)
            if use_market_filter:
                frame["MARKET_BULLISH"] = market_regime.reindex(frame.index, method="ffill").fillna(False)
            else:
                frame["MARKET_BULLISH"] = True
            frames[symbol] = frame
            loaded += 1
        except Exception as error:
            print(f"Skipping {symbol}: {error}")

    if not loaded:
        raise SystemExit(
            "No daily data loaded. Configure FYERS_CLIENT_ID and FYERS_ACCESS_TOKEN "
            "with DATA_PROVIDER=FYERS in .env, then run this command again."
        )

    portfolio = SwingPortfolioBacktest()
    trades, equity = portfolio.run(frames, strategy)
    winners = [trade.pnl for trade in trades if trade.pnl > 0]
    losers = [trade.pnl for trade in trades if trade.pnl <= 0]
    gross_profit = sum(winners)
    gross_loss = -sum(losers)
    summary = {
        "Strategy": "Daily long-only trend pullback",
        "BacktestType": "Portfolio-level",
        "MarketRegimeFilter": use_market_filter,
        "MarketRegimeSource": market_regime_source if use_market_filter else "DISABLED",
        "StockLongTrendFilter": SWING_REQUIRE_STOCK_LONG_TREND,
        "Symbols": loaded,
        "Trades": len(trades),
        "WinRatePct": round(100 * len(winners) / len(trades), 2) if trades else 0.0,
        "NetPnL": round(sum(trade.pnl for trade in trades), 2),
        "ProfitFactor": round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
        "AverageTrade": round(sum(trade.pnl for trade in trades) / len(trades), 2) if trades else 0.0,
    }
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    pd.DataFrame([trade.__dict__ for trade in trades]).to_csv(reports / "swing_daily_trades.csv", index=False)
    equity.to_csv(reports / "swing_daily_equity.csv", index=False)
    (reports / "swing_daily_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print("Saved swing trade, equity, and summary reports in reports/")


if __name__ == "__main__":
    main()
