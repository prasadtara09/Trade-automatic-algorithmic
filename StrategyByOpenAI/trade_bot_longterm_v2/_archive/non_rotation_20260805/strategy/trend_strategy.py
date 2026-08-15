from config import (
    ATR_STOP,
    ATR_TARGET,
    BREAKOUT_MAX_ATR,
    BREAKOUT_MIN_ATR,
    MIN_CANDLE_BODY_PCT,
    MIN_SIGNAL_SCORE,
    RETEST_CLOSE_BUFFER_ATR,
    RETEST_LOOKBACK,
    RETEST_TOLERANCE_ATR,
)
from strategy.base import BaseStrategy
from strategy.score import calculate_score
from strategy.signal import Signal


class TrendStrategy(BaseStrategy):
    """Trend-aligned resistance/support breakout strategy for intraday research."""

    name = "Confirmed Multi-Timeframe Breakout"

    @staticmethod
    def _confirmed_retest(df, index, side, current_atr):
        """Return the broken level only after a valid breakout is retested.

        This avoids entering the initial breakout spike.  A long setup must
        hold above old resistance after retesting it; a short setup must hold
        below old support after retesting it.
        """
        start = max(0, index - RETEST_LOOKBACK)
        for previous_index in range(index - 1, start - 1, -1):
            previous = df.iloc[previous_index]
            level_column = "HH_BREAKOUT" if side == "BUY" else "LL_BREAKOUT"
            level = float(previous[level_column])
            breakout_distance = (
                float(previous["Close"] - level)
                if side == "BUY"
                else float(level - previous["Close"])
            )
            prior_range = float(previous["High"] - previous["Low"])
            prior_body = abs(float(previous["Close"] - previous["Open"]))
            prior_body_ratio = prior_body / prior_range if prior_range > 0 else 0
            valid_initial_break = (
                previous["Close"] > level if side == "BUY" else previous["Close"] < level
            ) and (
                previous["ATR"] * BREAKOUT_MIN_ATR
                <= breakout_distance
                <= previous["ATR"] * BREAKOUT_MAX_ATR
            ) and prior_body_ratio >= MIN_CANDLE_BODY_PCT
            if not valid_initial_break:
                continue

            if side == "BUY":
                retested = df.iloc[index]["Low"] <= level + current_atr * RETEST_TOLERANCE_ATR
                held_level = df.iloc[index]["Close"] >= level + current_atr * RETEST_CLOSE_BUFFER_ATR
            else:
                retested = df.iloc[index]["High"] >= level - current_atr * RETEST_TOLERANCE_ATR
                held_level = df.iloc[index]["Close"] <= level - current_atr * RETEST_CLOSE_BUFFER_ATR
            if retested and held_level:
                return level
        return None

    def generate_signal(self, df, index):
        row = df.iloc[index]
        atr = float(row["ATR"])
        candle_range = float(row["High"] - row["Low"])
        if atr <= 0 or candle_range <= 0:
            return None

        body_ratio = abs(float(row["Close"] - row["Open"])) / candle_range
        if body_ratio < MIN_CANDLE_BODY_PCT:
            return None

        candidates = (
            ("BUY", row["Close"] > row["SUPERTREND"]),
            ("SELL", row["Close"] < row["SUPERTREND"]),
        )
        for side, supertrend_ok in candidates:
            level = self._confirmed_retest(df, index, side, atr)
            if not supertrend_ok or level is None:
                continue

            score, reasons = calculate_score(row, side)
            if score < MIN_SIGNAL_SCORE:
                continue

            entry = float(row["Close"])
            stop = entry - atr * ATR_STOP if side == "BUY" else entry + atr * ATR_STOP
            target = entry + atr * ATR_TARGET if side == "BUY" else entry - atr * ATR_TARGET
            return Signal(
                symbol=row["Symbol"],
                timestamp=row.name,
                side=side,
                score=score,
                entry=entry,
                stoploss=round(stop, 2),
                target=round(target, 2),
                strategy=self.name,
                atr=atr,
                remarks=",".join(reasons + ["BREAKOUT_RETEST", "CANDLE_QUALITY"]),
            )

        return None
