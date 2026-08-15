import pandas as pd


def vwap(df: pd.DataFrame):

    data = df.copy()

    data["Date"] = data.index.date

    tp = (
        data["High"] +
        data["Low"] +
        data["Close"]
    ) / 3

    data["TPV"] = tp * data["Volume"]

    cumulative_tpv = data.groupby("Date")["TPV"].cumsum()

    cumulative_volume = data.groupby("Date")["Volume"].cumsum()

    return cumulative_tpv / cumulative_volume