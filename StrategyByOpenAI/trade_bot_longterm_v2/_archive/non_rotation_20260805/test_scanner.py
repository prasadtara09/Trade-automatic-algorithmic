from scanner.scanner import Scanner

from data.universe import NIFTY50

scanner = Scanner()

signals = scanner.scan(NIFTY50)

print()

print("=" * 70)

print("Signals Found:", len(signals))

print("=" * 70)

for signal in signals[:20]:

    print(signal)