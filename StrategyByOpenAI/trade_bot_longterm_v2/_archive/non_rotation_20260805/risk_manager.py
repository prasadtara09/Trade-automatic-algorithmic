from config import (
    INITIAL_CAPITAL,
    MAX_POSITION_VALUE_PCT,
    RISK_PER_TRADE,
    MAX_OPEN_POSITIONS,
)


class RiskManager:

    def __init__(self):

        self.capital = INITIAL_CAPITAL
        self.risk_per_trade = RISK_PER_TRADE
        self.max_positions = MAX_OPEN_POSITIONS
        self.max_position_value_pct = MAX_POSITION_VALUE_PCT

    def calculate_position_size(
        self,
        entry,
        stoploss,
        available_cash=None,
    ):

        risk_per_share = abs(entry - stoploss)

        if risk_per_share == 0:
            return 0

        capital = self.capital if available_cash is None else available_cash
        risk_amount = capital * self.risk_per_trade

        qty = int(
            risk_amount /
            risk_per_share
        )

        max_by_exposure = int((capital * self.max_position_value_pct) / entry)
        return max(min(qty, max_by_exposure), 0)

    def can_take_trade(
        self,
        portfolio,
    ):

        return (
            len(portfolio.positions)
            < self.max_positions
        )
