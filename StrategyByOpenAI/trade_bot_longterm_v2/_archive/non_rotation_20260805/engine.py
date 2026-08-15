from dataclasses import replace

from config import ATR_STOP, ATR_TARGET, MIN_LOOKBACK
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

    def run(self, symbol, df, strategy_engine):
        self.completed_trades = []
        pending_signal = None

        # The current candle can create a signal only after it closes.  It is
        # therefore filled at the next candle's open, avoiding close-price
        # look-ahead bias.
        for i in range(MIN_LOOKBACK, len(df)):
            candle = df.iloc[i]

            if self.portfolio.has_position(symbol):
                trade = self.trade_manager.manage_trade(self.portfolio.get(symbol), candle)
                if trade:
                    self.completed_trades.append(trade)

            if not self.portfolio.has_position(symbol) and pending_signal:
                entry = float(candle["Open"])
                pending_signal = replace(
                    pending_signal,
                    timestamp=candle.name,
                    entry=entry,
                    stoploss=round(entry - pending_signal.atr * ATR_STOP, 2),
                    target=round(entry + pending_signal.atr * ATR_TARGET, 2),
                )
                position = self.trade_manager.enter_trade(pending_signal)
                pending_signal = None

                # An order filled at this bar's open can also reach its stop
                # or target within the same bar. Stop is evaluated first by
                # TradeManager, which is the conservative assumption when the
                # intrabar path is unknown.
                if position:
                    trade = self.trade_manager.manage_trade(position, candle)
                    if trade:
                        self.completed_trades.append(trade)

            if not self.portfolio.has_position(symbol) and pending_signal is None and i < len(df) - 1:
                pending_signal = strategy_engine.check_entry(symbol, df, i)

        # Include open positions in reports instead of silently dropping them.
        if self.portfolio.has_position(symbol):
            position = self.portfolio.get(symbol)
            final_candle = df.iloc[-1]
            self.completed_trades.append(
                self.trade_manager.close_trade(
                    position, final_candle["Close"], final_candle.name, "END_OF_DATA"
                )
            )

        return self.completed_trades
