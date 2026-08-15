from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:

    symbol: str

    side: str

    quantity: int

    entry_price: float

    stoploss: float

    target: float

    atr: float

    entry_time: datetime

    highest_price: float

    lowest_price: float

    initial_stoploss: float

    rr: float

    active: bool = True

    exit_price: float = 0

    exit_time: datetime = None

    pnl: float = 0

    exit_reason: str = ""