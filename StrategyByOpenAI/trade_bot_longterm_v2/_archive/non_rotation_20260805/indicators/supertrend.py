import pandas as pd

from indicators.atr import atr


def supertrend(
    df,
    period=10,
    multiplier=3
):

    data = df.copy()

    atr_value = atr(
        data["High"],
        data["Low"],
        data["Close"],
        period
    )

    hl2 = (
        data["High"] +
        data["Low"]
    ) / 2

    upper = hl2 + multiplier * atr_value

    lower = hl2 - multiplier * atr_value

    trend = [True]

    st = [lower.iloc[0]]

    for i in range(1, len(data)):

        if data["Close"].iloc[i] > upper.iloc[i - 1]:

            trend.append(True)

        elif data["Close"].iloc[i] < lower.iloc[i - 1]:

            trend.append(False)

        else:

            trend.append(trend[-1])

        st.append(

            lower.iloc[i]

            if trend[-1]

            else upper.iloc[i]

        )

    return pd.Series(
        st,
        index=data.index
    )