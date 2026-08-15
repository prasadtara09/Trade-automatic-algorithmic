from dataclasses import replace
from datetime import datetime

from config import (
    ATR_STOP,
    ATR_TARGET,
    INTRADAY_ENTRY_START,
    INTRADAY_LAST_ENTRY,
    INTRADAY_ONLY,
    INTRADAY_SQUARE_OFF,
    MAX_TRADES_PER_SYMBOL_PER_DAY,
    MIN_LOOKBACK,
)
from execution.account import Account
from execution.portfolio import Portfolio
from execution.risk_manager import RiskManager
from execution.trade_manager import TradeManager


class BacktestEngine:
    """Single-symbol OHLC backtest with next-bar fills and conservative exits."""

    def __init__(self):
        self.account = Account()
        self.portfolio = Portfolio()
        self.risk = RiskManager()
        self.trade_manager = TradeManager(self.portfolio, self.risk, self.account)
        self.completed_trades = []
        self.entries_by_day = {}

    @staticmethod
    def _clock(value):
        return datetime.strptime(value, "%H:%M").time()

    def _can_enter(self, timestamp):
        """Allow entries only during the configured intraday session."""
        if not INTRADAY_ONLY:
            return True
        candle_time = timestamp.time()
        return self._clock(INTRADAY_ENTRY_START) <= candle_time <= self._clock(INTRADAY_LAST_ENTRY)

    def _must_square_off(self, timestamp):
        return INTRADAY_ONLY and timestamp.time() >= self._clock(INTRADAY_SQUARE_OFF)

    def _can_open_for_symbol_today(self, timestamp):
        return self.entries_by_day.get(timestamp.date(), 0) < MAX_TRADES_PER_SYMBOL_PER_DAY

    def run(self, symbol, df, strategy_engine):
        self.completed_trades = []
        self.entries_by_day = {}
        pending_signal = None

        # A current candle can create a signal only after it closes. It fills
        # at the next candle's open, avoiding close-price look-ahead bias.
        for i in range(MIN_LOOKBACK, len(df)):
            candle = df.iloc[i]

            if self.portfolio.has_position(symbol):
                position = self.portfolio.get(symbol)
                if self._must_square_off(candle.name):
                    # The 15:15 candle starts at the intended square-off time,
                    # so its open is available without looking ahead.
                    trade = self.trade_manager.close_trade(
                        position, candle["Open"], candle.name, "INTRADAY_SQUARE_OFF"
                    )
                else:
                    trade = self.trade_manager.manage_trade(position, candle)
                if trade:
                    self.completed_trades.append(trade)

            if (
                not self.portfolio.has_position(symbol)
                and pending_signal
                and self._can_enter(candle.name)
                and self._can_open_for_symbol_today(candle.name)
            ):
                entry = float(candle["Open"])
                pending_signal = replace(
                    pending_signal,
                    timestamp=candle.name,
                    entry=entry,
                    stoploss=(
                        round(entry - pending_signal.atr * ATR_STOP, 2)
                        if pending_signal.side == "BUY"
                        else round(entry + pending_signal.atr * ATR_STOP, 2)
                    ),
                    target=(
                        round(entry + pending_signal.atr * ATR_TARGET, 2)
                        if pending_signal.side == "BUY"
                        else round(entry - pending_signal.atr * ATR_TARGET, 2)
                    ),
                )
                position = self.trade_manager.enter_trade(pending_signal)
                pending_signal = None

                # If both levels are reached in this entry bar, TradeManager
                # checks the stop first, which is the conservative assumption.
                if position:
                    day = candle.name.date()
                    self.entries_by_day[day] = self.entries_by_day.get(day, 0) + 1
                    trade = self.trade_manager.manage_trade(position, candle)
                    if trade:
                        self.completed_trades.append(trade)

            # A signal cannot be carried to the next day or past the final
            # entry time in an intraday-only strategy.
            if pending_signal and (
                not self._can_enter(candle.name)
                or not self._can_open_for_symbol_today(candle.name)
            ):
                pending_signal = None

            if (
                not self.portfolio.has_position(symbol)
                and pending_signal is None
                and i < len(df) - 1
                and self._can_enter(candle.name)
                and self._can_open_for_symbol_today(candle.name)
            ):
                pending_signal = strategy_engine.check_entry(symbol, df, i)

        if self.portfolio.has_position(symbol):
            position = self.portfolio.get(symbol)
            final_candle = df.iloc[-1]
            self.completed_trades.append(
                self.trade_manager.close_trade(
                    position, final_candle["Close"], final_candle.name, "END_OF_DATA"
                )
            )

        return self.completed_trades
