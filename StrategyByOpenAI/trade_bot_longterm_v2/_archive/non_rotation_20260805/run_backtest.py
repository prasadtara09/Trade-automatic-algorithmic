from config import INITIAL_CAPITAL
from data.loader import get_data
from strategy.strategy_engine import StrategyEngine
from backtest.engine import BacktestEngine
from backtest.metrics import Metrics
from backtest.report import export
from indicators.indicator_engine import apply_indicators

symbol = "ASHOKLEY.NS"

print("Loading Data...")

df = get_data(symbol)

df = apply_indicators(df)

print("Running Backtest...")

engine = BacktestEngine()

strategy = StrategyEngine()

trades = engine.run(

    symbol,

    df,

    strategy,

)

print()

report = export(trades, INITIAL_CAPITAL)

print(report)

print()

summary = Metrics.summary(

    trades,

    INITIAL_CAPITAL,

)

print("============== SUMMARY ==============")

for key, value in summary.items():

    print(f"{key:20}: {value}")
