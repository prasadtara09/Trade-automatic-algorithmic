import json
from pathlib import Path

import pandas as pd

from backtest.metrics import Metrics
from backtest.performance import Performance


REPORTS_DIR = Path("reports")


def export(trades, initial_capital):
    """Write trade, equity, monthly, and summary artifacts for one backtest."""
    REPORTS_DIR.mkdir(exist_ok=True)
    rows = [
        {
            "Symbol": trade.symbol,
            "Side": trade.side,
            "Entry Time": trade.entry_time,
            "Exit Time": trade.exit_time,
            "Entry": trade.entry_price,
            "Exit": trade.exit_price,
            "Qty": trade.quantity,
            "PnL": trade.pnl,
            "Exit Reason": trade.exit_reason,
            "RR": trade.rr,
            "ATR": trade.atr,
        }
        for trade in trades
    ]
    trade_frame = pd.DataFrame(rows)
    trade_frame.to_csv(REPORTS_DIR / "trades.csv", index=False)

    equity = Performance.equity_curve(trades, initial_capital)
    equity.to_csv(REPORTS_DIR / "equity_curve.csv", index=False)
    Performance.monthly_pnl(trades).to_csv(REPORTS_DIR / "monthly_returns.csv", index=False)

    summary = Metrics.summary(trades, initial_capital)
    with (REPORTS_DIR / "metrics.json").open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2, allow_nan=False)

    return trade_frame
