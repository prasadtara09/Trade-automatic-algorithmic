class Portfolio:

    def __init__(self):

        self.positions = {}

    def add(self, position):

        self.positions[position.symbol] = position

    def remove(self, symbol):

        if symbol in self.positions:
            del self.positions[symbol]

    def has_position(self, symbol):

        return symbol in self.positions

    def get(self, symbol):

        return self.positions.get(symbol)

    def all_positions(self):

        return list(self.positions.values())

    def count(self):

        return len(self.positions)