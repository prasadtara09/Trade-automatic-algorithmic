import pandas as pd

from config import (
    ADX_PERIOD, ATR_PERIOD, BREAKOUT_LOOKBACK, EMA_FAST, EMA_SLOW,
    HIGHER_TIMEFRAME, HTF_EMA_FAST, HTF_EMA_SLOW, RSI_PERIOD,
    VOLUME_LOOKBACK,
)
from indicators.adx import adx
from indicators.atr import atr
from indicators.ema import ema
from indicators.rsi import rsi
from indicators.supertrend import supertrend
from indicators.vwap import vwap


def apply_indicators(df):
    """Add indicator values that were available when each candle closed."""
    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Market data must use a DatetimeIndex")

    df["EMA20"] = ema(df["Close"], EMA_FAST)
    df["EMA50"] = ema(df["Close"], EMA_SLOW)
    df["RSI"] = rsi(df["Close"], RSI_PERIOD)
    df["ATR"] = atr(df["High"], df["Low"], df["Close"], ATR_PERIOD)
    df["ADX"] = adx(df["High"], df["Low"], df["Close"], ADX_PERIOD)
    df["VWAP"] = vwap(df)
    df["SUPERTREND"] = supertrend(df)
    df["VOL_MA"] = df["Volume"].rolling(VOLUME_LOOKBACK).mean()
    df["HH_BREAKOUT"] = df["High"].rolling(BREAKOUT_LOOKBACK).max().shift(1)
    df["LL_BREAKOUT"] = df["Low"].rolling(BREAKOUT_LOOKBACK).min().shift(1)

    higher = df.resample(HIGHER_TIMEFRAME, label="right", closed="right").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna()
    higher["HTF_EMA_FAST"] = ema(higher["Close"], HTF_EMA_FAST)
    higher["HTF_EMA_SLOW"] = ema(higher["Close"], HTF_EMA_SLOW)

    # A lower-timeframe signal must not inspect the still-forming higher bar.
    completed_higher = higher[["HTF_EMA_FAST", "HTF_EMA_SLOW"]].shift(1)
    df = df.join(completed_higher.reindex(df.index, method="ffill"))
    return df.dropna()
