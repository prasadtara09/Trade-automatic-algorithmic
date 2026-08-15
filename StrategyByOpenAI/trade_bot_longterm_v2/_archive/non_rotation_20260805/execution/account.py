from config import INITIAL_CAPITAL


class Account:
    def __init__(self):
        self.initial_capital = INITIAL_CAPITAL
        self.cash = INITIAL_CAPITAL
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.daily_realized_pnl = {}
        self.weekly_realized_pnl = {}

    @property
    def equity(self):
        return self.cash + self.unrealized_pnl

    def book_profit(self, pnl, timestamp=None):
        self.cash += pnl
        self.realized_pnl += pnl

        if timestamp is not None:
            day_key = timestamp.date()
            iso_year, iso_week, _ = timestamp.isocalendar()
            week_key = (iso_year, iso_week)
            self.daily_realized_pnl[day_key] = self.daily_realized_pnl.get(day_key, 0.0) + pnl
            self.weekly_realized_pnl[week_key] = self.weekly_realized_pnl.get(week_key, 0.0) + pnl

    def daily_pnl(self, timestamp):
        return self.daily_realized_pnl.get(timestamp.date(), 0.0)

    def weekly_pnl(self, timestamp):
        iso_year, iso_week, _ = timestamp.isocalendar()
        return self.weekly_realized_pnl.get((iso_year, iso_week), 0.0)

    def reset_unrealized(self):
        self.unrealized_pnl = 0.0

    def add_unrealized(self, pnl):
        self.unrealized_pnl += pnl
