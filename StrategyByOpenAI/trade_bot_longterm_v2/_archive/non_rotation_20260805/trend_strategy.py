from strategy.base import BaseStrategy

from strategy.signal import Signal

from strategy.score import calculate_score

from config import (
    ATR_STOP,
    ATR_TARGET,
    MIN_SIGNAL_SCORE,
)


class TrendStrategy(BaseStrategy):

    name = "Multi-Timeframe Trend Volume Breakout"

    def generate_signal(

        self,

        df,

        index

    ):

        row = df.iloc[index]

        score, reasons = calculate_score(row)

        if score < MIN_SIGNAL_SCORE:
            return None

        breakout = row["Close"] > row["HH_BREAKOUT"]

        if not breakout:

            return None

        entry = float(row["Close"])
        atr = float(row["ATR"])

        stop = round(entry - atr * ATR_STOP, 2)
        target = round(entry + atr * ATR_TARGET, 2)

        return Signal(

            symbol=row["Symbol"],

            timestamp=row.name,

            side="BUY",

            score=score,

            entry=entry,

            stoploss=stop,

            target=target,

            strategy=self.name,

            atr=atr,

            remarks=",".join(reasons)

        )
