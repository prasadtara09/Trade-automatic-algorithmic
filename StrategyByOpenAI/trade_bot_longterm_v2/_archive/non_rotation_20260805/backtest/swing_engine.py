"""Long-only daily swing backtest with next-day fills and realistic exits."""

from dataclasses import dataclass

from backtest.tradebook import Trade
from config import (
    BROKERAGE_PER_ORDER,
    INITIAL_CAPITAL,
    MAX_POSITION_VALUE_PCT,
    RISK_PER_TRADE,
    SLIPPAGE,
)


@dataclass
class SwingSettings:
    stop_atr: float = 1.5
    target_atr: float = 3.0
    trail_atr: float = 2.5
    max_holding_days: int = 10


class SwingBacktestEngine:
    """Research-only daily, long-only engine. It never places broker orders."""

    def __init__(self, settings=None):
        self.settings = settings or SwingSettings()

    @staticmethod
    def _quantity(entry, stop):
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            return 0
        risk_quantity = int((INITIAL_CAPITAL * RISK_PER_TRADE) / risk_per_share)
        exposure_quantity = int((INITIAL_CAPITAL * MAX_POSITION_VALUE_PCT) / entry)
        return max(0, min(risk_quantity, exposure_quantity))

    @staticmethod
    def _close(position, price, timestamp, reason):
        exit_price = round(price * (1 - SLIPPAGE), 2)
        pnl = (exit_price - position["entry_price"]) * position["quantity"] - (BROKERAGE_PER_ORDER * 2)
        risk = position["entry_price"] - position["initial_stop"]
        return Trade(
            symbol=position["symbol"],
            side="BUY",
            quantity=position["quantity"],
            entry_time=position["entry_time"],
            exit_time=timestamp,
            entry_price=position["entry_price"],
            exit_price=exit_price,
            initial_stoploss=position["initial_stop"],
            stoploss=position["stop"],
            target=position["target"],
            pnl=pnl,
            rr=round((exit_price - position["entry_price"]) / risk, 2) if risk else 0,
            exit_reason=reason,
            atr=position["atr"],
            risk_reward=round((position["target"] - position["entry_price"]) / risk, 2) if risk else 0,
        )

    def run(self, symbol, df, strategy, min_lookback=60):
        trades = []
        pending = False
        position = None

        for index in range(min_lookback, len(df)):
            candle = df.iloc[index]

            if position:
                # Existing stop/target are evaluated before this bar can move
                # the trailing stop, avoiding same-day OHLC look-ahead bias.
                if candle["Low"] <= position["stop"]:
                    trades.append(self._close(position, position["stop"], candle.name, "STOPLOSS"))
                    position = None
                elif candle["High"] >= position["target"]:
                    trades.append(self._close(position, position["target"], candle.name, "TARGET"))
                    position = None
                elif index - position["entry_index"] >= self.settings.max_holding_days:
                    trades.append(self._close(position, candle["Close"], candle.name, "TIME_EXIT"))
                    position = None
                else:
                    position["highest"] = max(position["highest"], float(candle["High"]))
                    position["stop"] = max(
                        position["stop"],
                        round(position["highest"] - position["atr"] * self.settings.trail_atr, 2),
                    )

            if position is None and pending:
                entry = float(candle["Open"])
                atr = float(df.iloc[index - 1]["ATR"])
                stop = round(entry - atr * self.settings.stop_atr, 2)
                quantity = self._quantity(entry, stop)
                if quantity:
                    entry_price = round(entry * (1 + SLIPPAGE), 2)
                    position = {
                        "symbol": symbol,
                        "entry_time": candle.name,
                        "entry_index": index,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "atr": atr,
                        "initial_stop": stop,
                        "stop": stop,
                        "target": round(entry + atr * self.settings.target_atr, 2),
                        "highest": entry,
                    }
                pending = False

            if position is None and not pending and index < len(df) - 1:
                pending = strategy.should_enter(df, index)

        if position is not None:
            last = df.iloc[-1]
            trades.append(self._close(position, last["Close"], last.name, "END_OF_DATA"))
        return trades
