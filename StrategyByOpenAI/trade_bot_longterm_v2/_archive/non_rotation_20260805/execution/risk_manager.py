from config import (
    INITIAL_CAPITAL,
    MAX_DAILY_LOSS_PCT,
    MAX_OPEN_POSITIONS,
    MAX_POSITION_VALUE_PCT,
    MAX_WEEKLY_LOSS_PCT,
    RISK_PER_TRADE,
)


class RiskManager:
    def __init__(self):
        self.capital = INITIAL_CAPITAL
        self.risk_per_trade = RISK_PER_TRADE
        self.max_positions = MAX_OPEN_POSITIONS
        self.max_position_value_pct = MAX_POSITION_VALUE_PCT
        self.max_daily_loss_pct = MAX_DAILY_LOSS_PCT
        self.max_weekly_loss_pct = MAX_WEEKLY_LOSS_PCT

    def calculate_position_size(self, entry, stoploss, available_cash=None):
        risk_per_share = abs(entry - stoploss)
        if risk_per_share == 0 or entry <= 0:
            return 0

        capital = self.capital if available_cash is None else available_cash
        risk_sized_quantity = int((capital * self.risk_per_trade) / risk_per_share)
        exposure_capped_quantity = int((capital * self.max_position_value_pct) / entry)
        return max(min(risk_sized_quantity, exposure_capped_quantity), 0)

    def can_take_trade(self, portfolio, account=None, timestamp=None):
        if len(portfolio.positions) >= self.max_positions:
            return False
        if account is None or timestamp is None:
            return True

        daily_limit = -account.initial_capital * self.max_daily_loss_pct
        weekly_limit = -account.initial_capital * self.max_weekly_loss_pct
        return account.daily_pnl(timestamp) > daily_limit and account.weekly_pnl(timestamp) > weekly_limit
