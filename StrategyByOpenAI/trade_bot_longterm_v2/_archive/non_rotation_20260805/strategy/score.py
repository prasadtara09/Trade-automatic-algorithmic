"""Directional quality score for the intraday breakout strategy."""

from config import (
    ADX_MIN,
    RSI_MAX,
    RSI_MIN,
    SHORT_RSI_MAX,
    SHORT_RSI_MIN,
    VOLUME_MULTIPLIER,
)


def calculate_score(row, side):
    """Return a score and reasons for either a BUY or SELL setup."""
    is_long = side == "BUY"
    score = 0
    details = []

    def directional(above):
        return above if is_long else not above

    if directional(row["EMA20"] > row["EMA50"]):
        score += 20
        details.append("LTF_TREND")
    if directional(row["HTF_EMA_FAST"] > row["HTF_EMA_SLOW"]):
        score += 25
        details.append("HTF_TREND")
    if directional(row["Close"] > row["EMA20"]):
        score += 10
        details.append("PRICE_VS_EMA")
    if directional(row["Close"] > row["VWAP"]):
        score += 15
        details.append("PRICE_VS_VWAP")

    rsi_ok = RSI_MIN <= row["RSI"] <= RSI_MAX if is_long else SHORT_RSI_MIN <= row["RSI"] <= SHORT_RSI_MAX
    if rsi_ok:
        score += 10
        details.append("RSI")
    if row["ADX"] >= ADX_MIN:
        score += 10
        details.append("ADX")
    if row["Volume"] >= row["VOL_MA"] * VOLUME_MULTIPLIER:
        score += 10
        details.append("VOLUME_EXPANSION")

    return score, details
