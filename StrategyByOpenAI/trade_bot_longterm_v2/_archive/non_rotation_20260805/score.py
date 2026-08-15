from config import ADX_MIN, RSI_MAX, RSI_MIN, VOLUME_MULTIPLIER


def calculate_score(row):
    """Score a long setup; the breakout itself is checked by the strategy."""
    score = 0
    details = []

    if row["EMA20"] > row["EMA50"]:
        score += 20
        details.append("LTF_TREND")

    if row["HTF_EMA_FAST"] > row["HTF_EMA_SLOW"]:
        score += 25
        details.append("HTF_TREND")

    if row["Close"] > row["EMA20"]:
        score += 10
        details.append("PRICE_ABOVE_EMA")

    if row["Close"] > row["VWAP"]:
        score += 15
        details.append("ABOVE_VWAP")

    if RSI_MIN <= row["RSI"] <= RSI_MAX:
        score += 10
        details.append("RSI")

    if row["ADX"] >= ADX_MIN:
        score += 10
        details.append("ADX")

    if row["Volume"] >= row["VOL_MA"] * VOLUME_MULTIPLIER:
        score += 10
        details.append("VOLUME_EXPANSION")

    return score, details
