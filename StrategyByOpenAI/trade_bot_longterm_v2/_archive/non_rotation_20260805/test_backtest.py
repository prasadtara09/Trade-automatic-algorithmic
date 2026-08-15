from data.loader import get_data
from indicators.indicator_engine import apply_indicators

from strategy.strategy_engine import StrategyEngine
from backtest.engine import BacktestEngine

symbol = "RELIANCE.NS"

df = get_data(symbol)
df = apply_indicators(df)

strategy = StrategyEngine()

engine = BacktestEngine()

trades = engine.run(
    symbol,
    df,
    strategy
)

print(trades)