from strategy.trend_strategy import TrendStrategy

from strategy.ranking import rank

from config import MIN_LOOKBACK


class StrategyEngine:

    def __init__(self):

        self.strategies = [

            TrendStrategy()

        ]

    def scan(

        self,

        symbol,

        df

    ):

        signals = []

        df = df.copy()

        df["Symbol"] = symbol

        for strategy in self.strategies:

            for i in range(MIN_LOOKBACK, len(df)):

                signal = strategy.generate_signal(

                    df,

                    i

                )

                if signal:

                    signals.append(signal)

        return rank(signals)



    def check_entry(self, symbol, df, index):

        df["Symbol"] = symbol

        for strategy in self.strategies:

            signal = strategy.generate_signal(df, index)

            if signal:
                return signal

        return None