from backtest.performance import Performance


class Metrics:
    @staticmethod
    def summary(trades, initial_capital):
        if not trades:
            return {}

        pnl = [trade.pnl for trade in trades]
        winners = [value for value in pnl if value > 0]
        losers = [value for value in pnl if value <= 0]
        equity = Performance.equity_curve(trades, initial_capital)
        daily_pnl = Performance.daily_pnl(trades)
        max_drawdown_pct = Performance.max_drawdown_pct(equity)
        cagr = Performance.cagr(equity, initial_capital)
        holding_hours = [
            (trade.exit_time - trade.entry_time).total_seconds() / 3600
            for trade in trades
        ]

        return {
            "Trades": len(trades),
            "Wins": len(winners),
            "Losses": len(losers),
            "WinRate": round(len(winners) * 100 / len(trades), 2),
            "NetPnL": round(sum(pnl), 2),
            "GrossProfit": round(sum(winners), 2),
            "GrossLoss": round(sum(losers), 2),
            "AverageTrade": round(sum(pnl) / len(pnl), 2),
            "AverageWinner": round(sum(winners) / len(winners), 2) if winners else 0.0,
            "AverageLoser": round(sum(losers) / len(losers), 2) if losers else 0.0,
            "LargestWinner": round(max(pnl), 2),
            "LargestLoser": round(min(pnl), 2),
            "AverageHoldHours": round(sum(holding_hours) / len(holding_hours), 2),
            "ProfitFactor": Performance.profit_factor(trades),
            "Expectancy": Performance.expectancy(trades),
            "MaxDrawdown": Performance.max_drawdown(equity),
            "MaxDrawdownPct": max_drawdown_pct,
            "Sharpe": Performance.sharpe_ratio(daily_pnl, initial_capital),
            "Sortino": Performance.sortino_ratio(daily_pnl, initial_capital),
            "CAGR": cagr,
            "Calmar": Performance.calmar_ratio(cagr, max_drawdown_pct),
            "FinalEquity": round(equity.iloc[-1]["Equity"], 2),
        }
