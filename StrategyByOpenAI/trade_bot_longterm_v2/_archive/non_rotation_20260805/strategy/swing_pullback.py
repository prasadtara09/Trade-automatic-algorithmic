"""Long-only daily trend-pullback entry rule for swing research."""

from config import SWING_REQUIRE_MARKET_REGIME, SWING_REQUIRE_STOCK_LONG_TREND


class DailyTrendPullbackStrategy:
    """Buy a bullish resumption after a controlled pullback in a daily uptrend."""

    def should_enter(self, df, index):
        row = df.iloc[index]
        previous = df.iloc[index - 1]

        uptrend = (
            row["Close"] > row["EMA50"]
            and row["EMA20"] > row["EMA50"]
            and row["EMA50"] > df.iloc[index - 5]["EMA50"]
        )
        controlled_pullback = row["Low"] <= row["EMA20"] + row["ATR"] * 0.25
        bullish_resumption = row["Close"] > row["EMA20"] and row["Close"] > previous["High"] and row["Close"] > row["Open"]
        momentum_ok = 45 <= row["RSI"] <= 65 and row["ADX"] >= 20
        volume_ok = row["Volume"] >= row["VOL_MA"]
        market_ok = bool(row.get("MARKET_BULLISH", True)) if SWING_REQUIRE_MARKET_REGIME else True
        long_term_ok = (
            row["Close"] > row["EMA200"] and row["EMA50"] > row["EMA200"]
            if SWING_REQUIRE_STOCK_LONG_TREND else True
        )
        return bool(uptrend and controlled_pullback and bullish_resumption and momentum_ok and volume_ok and market_ok and long_term_ok)
