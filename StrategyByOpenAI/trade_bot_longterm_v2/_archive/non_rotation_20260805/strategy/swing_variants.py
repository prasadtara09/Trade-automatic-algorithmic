"""Long-only daily swing entry rules used by the research comparison."""


class _LongOnlyBase:
    @staticmethod
    def _bull_market(row):
        return row["Close"] > row["SMA200"] and row["SMA50"] > row["SMA200"]


class EmaPullbackEntry(_LongOnlyBase):
    name = "EMA pullback"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["EMA20"] > row["EMA50"]
            and row["Low"] <= row["EMA20"] + row["ATR"] * 0.25
            and row["Close"] > row["EMA20"]
            and row["Close"] > previous["High"]
            and row["Close"] > row["Open"]
            and 45 <= row["RSI"] <= 65
            and row["ADX"] >= 20
            and row["Volume"] >= row["VOL_MA"]
        )


class RsiMeanReversionEntry(_LongOnlyBase):
    name = "RSI(2) mean reversion"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["RSI2"] < 10
            and row["Close"] > row["SMA50"]
            and row["Close"] > row["Open"]
            and row["Close"] > previous["Close"]
        )


class BollingerReversionEntry(_LongOnlyBase):
    name = "Bollinger mean reversion"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["Close"] < row["BB_LOWER"]
            and row["RSI"] < 45
            and row["Close"] > row["Open"]
            and row["Close"] > previous["Close"]
        )


class MaCrossoverEntry(_LongOnlyBase):
    name = "EMA/SMA crossover"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and previous["EMA20"] <= previous["SMA50"]
            and row["EMA20"] > row["SMA50"]
            and 50 <= row["RSI"] <= 70
            and row["ADX"] >= 20
        )


class SmaBreakoutEntry(_LongOnlyBase):
    name = "SMA trend breakout"

    def should_enter(self, df, index):
        row = df.iloc[index]
        return bool(
            self._bull_market(row)
            and row["Close"] > row["HH20"]
            and row["Close"] > row["SMA20"]
            and 55 <= row["RSI"] <= 70
            and row["ADX"] >= 20
            and row["Volume"] >= row["VOL_MA"]
        )


class TrendStrengthBreakoutEntry(_LongOnlyBase):
    """Long-only breakout for stocks already showing sustained strength."""

    name = "Relative-strength trend breakout"

    def should_enter(self, df, index):
        row = df.iloc[index]
        return bool(
            self._bull_market(row)
            and row["SMA50"] > df.iloc[index - 10]["SMA50"]
            and row["RS60"] >= 0.08
            and row["Close"] > row["HH55"]
            and 55 <= row["RSI"] <= 72
            and row["ADX"] >= 20
            and row["Volume"] >= row["VOL_MA"]
        )


class RelativeStrengthPullbackEntry(_LongOnlyBase):
    """Buy a resumption after a shallow pullback in a strong stock trend."""

    name = "Relative-strength EMA pullback"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["EMA20"] > row["EMA50"]
            and row["RS60"] >= 0.08
            and row["Low"] <= row["EMA20"] + row["ATR"] * 0.35
            and row["Close"] > row["EMA20"]
            and row["Close"] > previous["High"]
            and 42 <= row["RSI"] <= 62
            and row["ADX"] >= 18
            and row["Volume"] >= row["VOL_MA"]
        )


class Rsi2StrongTrendDipEntry(_LongOnlyBase):
    """Buy a short-term oversold dip only inside a strong medium-term trend."""

    name = "RSI(2) strong-trend dip"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["RS60"] >= 0.05
            and row["Close"] > row["EMA50"]
            and row["RSI2"] <= 10
            and row["Close"] > row["Open"]
            and row["Close"] > previous["Close"]
        )


class BollingerStrongTrendDipEntry(_LongOnlyBase):
    """Buy a lower-Bollinger reversal only in a strong relative-strength trend."""

    name = "Bollinger strong-trend dip"

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]
        return bool(
            self._bull_market(row)
            and row["RS60"] >= 0.05
            and row["Close"] < row["BB_LOWER"]
            and row["RSI2"] <= 20
            and row["Close"] > row["Open"]
            and row["Close"] > previous["Close"]
        )
