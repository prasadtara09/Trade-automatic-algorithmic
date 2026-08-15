from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:

    symbol: str

    timestamp: datetime

    open: float

    high: float

    low: float

    close: float

    volume: int


@dataclass
class Signal:

    symbol: str

    side: str

    strategy: str

    score: float

    entry: float

    stoploss: float

    target: float


@dataclass
class Position:

    symbol: str

    quantity: int

    entry_price: float

    stoploss: float

    target: float

    pnl: float = 0

    highest_price: float = 0

    active: bool = True


@dataclass
class Trade:

    symbol: str

    entry_time: datetime

    exit_time: datetime

    side: str

    quantity: int

    entry_price: float

    exit_price: float

    pnl: float