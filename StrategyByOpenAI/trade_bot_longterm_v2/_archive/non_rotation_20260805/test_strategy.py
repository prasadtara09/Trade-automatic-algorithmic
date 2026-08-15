from data.loader import get_data

from indicators.indicator_engine import apply_indicators

from strategy.strategy_engine import StrategyEngine

df = get_data("RELIANCE.NS")

print(df.columns)
print(type(df["High"]))

df = apply_indicators(df)

engine = StrategyEngine()

signals = engine.scan(

    "RELIANCE.NS",

    df

)

print()

print("Signals:", len(signals))

print()

for s in signals[:5]:

    print(s)