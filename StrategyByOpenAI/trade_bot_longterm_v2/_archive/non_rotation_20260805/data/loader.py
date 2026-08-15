from data.cache import load_cache

from data.downloader import download


def get_data(

    symbol,

    period="60d",

    interval="15m",

    cache=True

):

    if cache:

        df = load_cache(symbol, interval)

        if df is not None:

            return df

    return download(

        symbol,

        period,

        interval

    )