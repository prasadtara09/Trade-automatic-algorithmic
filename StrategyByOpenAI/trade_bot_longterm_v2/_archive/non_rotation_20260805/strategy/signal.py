from dataclasses import dataclass
from datetime import datetime


@dataclass
class Signal:

    symbol: str

    timestamp: datetime

    side: str

    score: float

    entry: float

    stoploss: float

    target: float

    strategy: str

    atr: float

    remarks: str = ""

"""
    Example Usage:
    
    Signal(

    symbol="RELIANCE",

    timestamp=...,

    side="BUY",

    score=92,

    entry=1450,

    stoploss=1442,

    target=1466,

    strategy="Trend Strategy",

    atr=8.2

)
"""