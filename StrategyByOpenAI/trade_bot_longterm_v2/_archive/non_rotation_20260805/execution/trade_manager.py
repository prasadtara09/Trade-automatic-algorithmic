from execution.position import Position
from backtest.tradebook import Trade

from config import (
    BROKERAGE_PER_ORDER,
    SLIPPAGE,
)


class TradeManager:

    def __init__(self, portfolio, risk_manager, account):
        self.portfolio = portfolio
        self.risk = risk_manager
        self.account = account

    def enter_trade(self, signal):
        if self.portfolio.has_position(signal.symbol):
            return None

        if not self.risk.can_take_trade(
            self.portfolio,
            self.account,
            signal.timestamp,
        ):
            return None

        qty = self.risk.calculate_position_size(
            signal.entry,
            signal.stoploss,
            self.account.cash,
        )

        if qty == 0:
            return None

        risk = abs(signal.entry - signal.stoploss)
        reward = abs(signal.target - signal.entry)

        rr = round(reward / risk, 2) if risk != 0 else 0

        position = Position(
            symbol=signal.symbol,
            side=signal.side,
            quantity=qty,
            entry_price=round(
                signal.entry * (1 + SLIPPAGE if signal.side == "BUY" else 1 - SLIPPAGE),
                2,
            ),
            stoploss=signal.stoploss,
            initial_stoploss=signal.stoploss,
            target=signal.target,
            atr=signal.atr,
            entry_time=signal.timestamp,
            highest_price=signal.entry,
            lowest_price=signal.entry,
            rr=rr,
        )

        self.portfolio.add(position)
        return position

    def manage_trade(self, position, candle):
        # First evaluate stops/targets that existed at the *start* of this
        # candle. Updating a trailing stop from this candle's high and then
        # testing it against this candle's low assumes an unknowable price
        # order inside the bar and creates look-ahead bias.
        stop_hit = candle["Low"] <= position.stoploss if position.side == "BUY" else candle["High"] >= position.stoploss
        target_hit = candle["High"] >= position.target if position.side == "BUY" else candle["Low"] <= position.target

        if stop_hit:

            trailing = position.stoploss > position.initial_stoploss if position.side == "BUY" else position.stoploss < position.initial_stoploss
            if trailing:
                reason = "TRAILING_STOP"
            else:
                reason = "INITIAL_STOPLOSS"

            return self.close_trade(
                position,
                position.stoploss,
                candle.name,
                reason,
            )

        if target_hit:
            return self.close_trade(
                position,
                position.target,
                candle.name,
                "TARGET",
            )

        # A newly observed high can tighten the stop only for later candles.
        if candle["High"] > position.highest_price:
            position.highest_price = candle["High"]

        if candle["Low"] < position.lowest_price:
            position.lowest_price = candle["Low"]

        self.update_trailing_stop(position)

        return None

    def update_trailing_stop(self, position):
        if position.side == "BUY":
            new_stop = position.highest_price - (position.atr * 2.5)
            if new_stop > position.stoploss:
                position.stoploss = round(new_stop, 2)
        else:
            new_stop = position.lowest_price + (position.atr * 2.5)
            if new_stop < position.stoploss:
                position.stoploss = round(new_stop, 2)

    def close_trade(self, position, exit_price, exit_time, reason):
        position.exit_price = round(
            exit_price * (1 - SLIPPAGE if position.side == "BUY" else 1 + SLIPPAGE),
            2,
        )
        position.exit_time = exit_time
        position.exit_reason = reason

        direction = 1 if position.side == "BUY" else -1
        position.pnl = direction * (position.exit_price - position.entry_price) * position.quantity

        brokerage = BROKERAGE_PER_ORDER * 2

        position.pnl -= brokerage

        risk = abs(position.entry_price - position.initial_stoploss)
        reward = direction * (position.exit_price - position.entry_price)

        position.rr = (
            round(reward / risk, 2)
            if risk != 0
            else 0
        )

        # Update account balance
        self.account.book_profit(position.pnl, exit_time)

        # These lines were incorrectly indented outside the function previously
        position.active = False
        self.portfolio.remove(position.symbol)

        trade = Trade(
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=position.exit_time,
            entry_price=position.entry_price,
            exit_price=position.exit_price,
            initial_stoploss=position.initial_stoploss,
            stoploss=position.stoploss,
            target=position.target,
            pnl=position.pnl,
            rr=position.rr,
            exit_reason=position.exit_reason,
            atr=position.atr,
            risk_reward=round(
                abs(position.target - position.entry_price)
                / abs(position.entry_price - position.initial_stoploss),
                2,
            ),
        )

        return trade
