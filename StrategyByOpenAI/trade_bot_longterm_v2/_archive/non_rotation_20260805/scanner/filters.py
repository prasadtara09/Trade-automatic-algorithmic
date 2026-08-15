def basic_filter(df):

    row = df.iloc[-1]

    if row["Close"] < 100:
        return False

    if row["Volume"] < 100000:
        return False

    if row["ATR"] < 1:
        return False

    return True