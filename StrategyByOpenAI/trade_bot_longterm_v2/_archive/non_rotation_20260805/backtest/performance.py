import math

import pandas as pd


class Performance:
    @staticmethod
    def equity_curve(trades, initial_capital):
        equity = initial_capital
        rows = []
        for trade in trades:
            equity += trade.pnl
            rows.append({"Time": trade.exit_time, "Equity": equity, "PnL": trade.pnl})
        return pd.DataFrame(rows)

    @staticmethod
    def max_drawdown(equity_df):
        if equity_df.empty:
            return 0.0
        return round((equity_df["Equity"] - equity_df["Equity"].cummax()).min(), 2)

    @staticmethod
    def max_drawdown_pct(equity_df):
        if equity_df.empty:
            return 0.0
        peak = equity_df["Equity"].cummax()
        return round((((equity_df["Equity"] - peak) / peak) * 100).min(), 2)

    @staticmethod
    def profit_factor(trades):
        gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
        if gross_loss == 0:
            return 0.0 if gross_profit == 0 else float("inf")
        return round(gross_profit / gross_loss, 2)

    @staticmethod
    def expectancy(trades):
        if not trades:
            return 0.0
        return round(sum(trade.pnl for trade in trades) / len(trades), 2)

    @staticmethod
    def daily_pnl(trades):
        if not trades:
            return pd.DataFrame(columns=["Date", "PnL"])
        frame = pd.DataFrame({"Date": [trade.exit_time.date() for trade in trades], "PnL": [trade.pnl for trade in trades]})
        return frame.groupby("Date", as_index=False)["PnL"].sum()

    @staticmethod
    def monthly_pnl(trades):
        if not trades:
            return pd.DataFrame(columns=["Month", "PnL"])
        frame = pd.DataFrame({"Month": [trade.exit_time.strftime("%Y-%m") for trade in trades], "PnL": [trade.pnl for trade in trades]})
        return frame.groupby("Month", as_index=False)["PnL"].sum()

    @staticmethod
    def sharpe_ratio(daily_pnl, initial_capital):
        if len(daily_pnl) < 2:
            return 0.0
        returns = daily_pnl["PnL"] / initial_capital
        volatility = returns.std(ddof=1)
        if volatility == 0 or pd.isna(volatility):
            return 0.0
        return round((returns.mean() / volatility) * math.sqrt(252), 2)

    @staticmethod
    def sortino_ratio(daily_pnl, initial_capital):
        if len(daily_pnl) < 2:
            return 0.0
        returns = daily_pnl["PnL"] / initial_capital
        downside = returns[returns < 0].std(ddof=1)
        if pd.isna(downside) or downside == 0:
            return 0.0
        return round((returns.mean() / downside) * math.sqrt(252), 2)

    @staticmethod
    def cagr(equity_df, initial_capital):
        if equity_df.empty or len(equity_df) < 2:
            return 0.0
        days = max((equity_df["Time"].iloc[-1] - equity_df["Time"].iloc[0]).total_seconds() / 86400, 1)
        years = days / 365.25
        ending_equity = equity_df["Equity"].iloc[-1]
        if ending_equity <= 0:
            return -100.0
        return round((((ending_equity / initial_capital) ** (1 / years)) - 1) * 100, 2)

    @staticmethod
    def calmar_ratio(cagr_pct, max_drawdown_pct):
        if max_drawdown_pct == 0:
            return 0.0
        return round(cagr_pct / abs(max_drawdown_pct), 2)
