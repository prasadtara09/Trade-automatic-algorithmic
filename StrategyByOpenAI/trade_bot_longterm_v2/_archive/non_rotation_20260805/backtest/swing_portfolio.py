"""Portfolio-level, long-only daily swing backtest.

Unlike independent per-symbol backtests, this engine has one cash balance and
enforces the configured simultaneous-holdings and per-position exposure caps.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from backtest.tradebook import Trade
from config import (
    BROKERAGE_PER_ORDER,
    INITIAL_CAPITAL,
    MAX_OPEN_POSITIONS,
    MAX_POSITION_VALUE_PCT,
    RISK_PER_TRADE,
    SLIPPAGE,
)


@dataclass
class SwingPortfolioSettings:
    stop_atr: float = 1.5
    target_atr: float = 3.0
    trail_atr: float = 2.5
    # When set, a move of this many ATRs locks the stop at entry. The stop is
    # only raised after that point and is never lowered again.
    breakeven_trigger_atr: Optional[float] = None
    max_holding_days: int = 10


class SwingPortfolioBacktest:
    def __init__(self, settings=None):
        self.settings = settings or SwingPortfolioSettings()
        self.cash = INITIAL_CAPITAL
        self.positions = {}
        self.trades = []
        self.equity_rows = []

    def _equity(self, rows):
        marked_value = sum(
            float(rows[symbol]["Close"]) * position["quantity"]
            for symbol, position in self.positions.items()
            if symbol in rows
        )
        return self.cash + marked_value

    def _quantity(self, entry, stop, capital):
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            return 0
        risk_quantity = int((capital * RISK_PER_TRADE) / risk_per_share)
        exposure_quantity = int((capital * MAX_POSITION_VALUE_PCT) / entry)
        cash_quantity = int(self.cash / entry)
        return max(0, min(risk_quantity, exposure_quantity, cash_quantity))

    def _close(self, position, price, timestamp, reason):
        exit_price = round(price * (1 - SLIPPAGE), 2)
        proceeds = exit_price * position["quantity"]
        charges = BROKERAGE_PER_ORDER * 2
        self.cash += proceeds - charges
        pnl = (exit_price - position["entry_price"]) * position["quantity"] - charges
        risk = position["entry_price"] - position["initial_stop"]
        self.trades.append(
            Trade(
                symbol=position["symbol"], side="BUY", quantity=position["quantity"],
                entry_time=position["entry_time"], exit_time=timestamp,
                entry_price=position["entry_price"], exit_price=exit_price,
                initial_stoploss=position["initial_stop"], stoploss=position["stop"],
                target=position["target"], pnl=pnl,
                rr=round((exit_price - position["entry_price"]) / risk, 2) if risk else 0,
                exit_reason=reason, atr=position["atr"],
                risk_reward=round((position["target"] - position["entry_price"]) / risk, 2) if risk else 0,
            )
        )
        del self.positions[position["symbol"]]

    def _manage_position(self, position, candle, timestamp):
        if candle["Open"] <= position["stop"]:
            self._close(position, candle["Open"], timestamp, "STOPLOSS_GAP")
            return
        if candle["Low"] <= position["stop"]:
            self._close(position, position["stop"], timestamp, "STOPLOSS")
            return
        if candle["Open"] >= position["target"]:
            self._close(position, candle["Open"], timestamp, "TARGET_GAP")
            return
        if candle["High"] >= position["target"]:
            self._close(position, position["target"], timestamp, "TARGET")
            return
        position["holding_days"] += 1
        if position["holding_days"] >= self.settings.max_holding_days:
            self._close(position, candle["Close"], timestamp, "TIME_EXIT")
            return
        position["highest"] = max(position["highest"], float(candle["High"]))
        if (
            self.settings.breakeven_trigger_atr is not None
            and position["highest"] >= position["entry_price"] + position["atr"] * self.settings.breakeven_trigger_atr
        ):
            position["stop"] = max(position["stop"], position["entry_price"])
        position["stop"] = max(
            position["stop"],
            round(position["highest"] - position["atr"] * self.settings.trail_atr, 2),
        )

    def _enter(self, symbol, candle, atr, timestamp, capital):
        entry_price = round(float(candle["Open"]) * (1 + SLIPPAGE), 2)
        initial_stop = round(entry_price - atr * self.settings.stop_atr, 2)
        quantity = self._quantity(entry_price, initial_stop, capital)
        if not quantity:
            return
        self.cash -= entry_price * quantity
        position = {
            "symbol": symbol,
            "entry_time": timestamp,
            "entry_price": entry_price,
            "quantity": quantity,
            "atr": atr,
            "initial_stop": initial_stop,
            "stop": initial_stop,
            "target": round(entry_price + atr * self.settings.target_atr, 2),
            "highest": entry_price,
            "holding_days": 0,
        }
        self.positions[symbol] = position

        # A newly opened daily position is exposed to the rest of that day's
        # range. Stop-first ordering is intentionally conservative.
        self._manage_position(position, candle, timestamp)

    def run(self, frames, strategy):
        """Backtest a dictionary of symbol -> daily indicator DataFrame."""
        frame_rows = {symbol: {timestamp: row for timestamp, row in frame.iterrows()} for symbol, frame in frames.items()}
        dates = sorted({timestamp for frame in frames.values() for timestamp in frame.index})
        scheduled = {}

        for timestamp in dates:
            rows = {symbol: row_map[timestamp] for symbol, row_map in frame_rows.items() if timestamp in row_map}

            for symbol in list(self.positions):
                if symbol in rows:
                    self._manage_position(self.positions[symbol], rows[symbol], timestamp)

            candidates = sorted(scheduled.pop(timestamp, []), key=lambda item: item[2], reverse=True)
            capital = self._equity(rows)
            for symbol, atr, relative_strength in candidates:
                if len(self.positions) >= MAX_OPEN_POSITIONS:
                    break
                if symbol not in rows or symbol in self.positions:
                    continue
                self._enter(symbol, rows[symbol], atr, timestamp, capital)
                capital = self._equity(rows)

            for symbol, frame in frames.items():
                if timestamp not in frame_rows[symbol]:
                    continue
                index = frame.index.get_loc(timestamp)
                if index >= len(frame) - 1 or symbol in self.positions:
                    continue
                if strategy.should_enter(frame, index):
                    next_timestamp = frame.index[index + 1]
                    scheduled.setdefault(next_timestamp, []).append(
                        (symbol, float(frame.iloc[index]["ATR"]), float(frame.iloc[index]["RS20"]))
                    )

            self.equity_rows.append({"Time": timestamp, "Equity": self._equity(rows), "OpenPositions": len(self.positions)})

        for symbol in list(self.positions):
            frame = frames[symbol]
            last = frame.iloc[-1]
            self._close(self.positions[symbol], last["Close"], last.name, "END_OF_DATA")

        return self.trades, pd.DataFrame(self.equity_rows)
