import unittest
from datetime import datetime

import pandas as pd

from backtest.engine import BacktestEngine
from config import MIN_LOOKBACK
from execution.risk_manager import RiskManager
from strategy.signal import Signal


class OneSignalStrategy:
    def __init__(self):
        self.calls = 0

    def check_entry(self, symbol, df, index):
        self.calls += 1
        if self.calls != 1:
            return None
        return Signal(
            symbol=symbol,
            timestamp=df.index[index],
            side="BUY",
            score=100,
            entry=float(df.iloc[index]["Close"]),
            stoploss=98.0,
            target=104.0,
            strategy="test",
            atr=2.0,
        )


class OneShortSignalStrategy(OneSignalStrategy):
    def check_entry(self, symbol, df, index):
        signal = super().check_entry(symbol, df, index)
        if signal is None:
            return None
        return Signal(
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            side="SELL",
            score=signal.score,
            entry=signal.entry,
            stoploss=102.0,
            target=96.0,
            strategy=signal.strategy,
            atr=signal.atr,
        )


class BacktestSafetyTests(unittest.TestCase):
    def test_position_size_is_capped_by_exposure(self):
        risk = RiskManager()
        # Risk sizing would request 250 shares, but 20% of 100,000 at 100 is 200.
        self.assertEqual(risk.calculate_position_size(100, 98, 100_000), 200)

    def test_signal_is_filled_on_next_open_not_signal_close(self):
        index = (
            pd.bdate_range("2025-01-01", periods=MIN_LOOKBACK + 2)
            + pd.Timedelta(hours=10)
        )
        df = pd.DataFrame(
            {
                "Open": [100.0] * (MIN_LOOKBACK + 1) + [110.0],
                "High": [101.0] * (MIN_LOOKBACK + 1) + [115.0],
                "Low": [99.0] * (MIN_LOOKBACK + 1) + [109.0],
                "Close": [100.0] * (MIN_LOOKBACK + 2),
            },
            index=index,
        )

        trades = BacktestEngine().run("TEST.NS", df, OneSignalStrategy())

        self.assertEqual(len(trades), 1)
        # Entry price includes the configured slippage, but is based on 110 open.
        self.assertAlmostEqual(trades[0].entry_price, 110.05, places=2)
        self.assertEqual(trades[0].exit_reason, "END_OF_DATA")

    def test_short_trade_uses_sell_entry_and_buy_exit_prices(self):
        index = (
            pd.bdate_range("2025-01-01", periods=MIN_LOOKBACK + 2)
            + pd.Timedelta(hours=10)
        )
        df = pd.DataFrame(
            {
                "Open": [100.0] * (MIN_LOOKBACK + 1) + [110.0],
                "High": [101.0] * (MIN_LOOKBACK + 1) + [111.0],
                "Low": [99.0] * (MIN_LOOKBACK + 1) + [103.0],
                "Close": [100.0] * (MIN_LOOKBACK + 2),
            },
            index=index,
        )

        trades = BacktestEngine().run("TEST.NS", df, OneShortSignalStrategy())

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].side, "SELL")
        self.assertEqual(trades[0].exit_reason, "TARGET")
        self.assertGreater(trades[0].pnl, 0)

    def test_intraday_position_is_squared_off_at_configured_time(self):
        dates = pd.bdate_range("2025-01-01", periods=MIN_LOOKBACK) + pd.Timedelta(hours=10)
        trade_day = pd.Timestamp("2025-03-13")
        index = dates.append(
            pd.DatetimeIndex([
                trade_day.replace(hour=13, minute=15),
                trade_day.replace(hour=13, minute=30),
                trade_day.replace(hour=15, minute=15),
            ])
        )
        df = pd.DataFrame(
            {
                "Open": [100.0] * (MIN_LOOKBACK + 2) + [101.0],
                "High": [101.0] * (MIN_LOOKBACK + 3),
                "Low": [99.0] * (MIN_LOOKBACK + 3),
                "Close": [100.0] * (MIN_LOOKBACK + 3),
            },
            index=index,
        )

        trades = BacktestEngine().run("TEST.NS", df, OneSignalStrategy())

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].exit_reason, "INTRADAY_SQUARE_OFF")
        self.assertEqual(trades[0].exit_time, trade_day.replace(hour=15, minute=15))


if __name__ == "__main__":
    unittest.main()
