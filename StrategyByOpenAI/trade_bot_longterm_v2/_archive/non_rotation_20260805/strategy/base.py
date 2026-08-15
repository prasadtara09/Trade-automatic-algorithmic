from abc import ABC, abstractmethod


class BaseStrategy(ABC):

    name = "Base Strategy"

    @abstractmethod
    def generate_signal(self, df, index):

        pass