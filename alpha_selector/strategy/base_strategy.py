# strategy/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def condition(self, df: pd.DataFrame) -> bool:
        pass

    @abstractmethod
    def score(self, df: pd.DataFrame) -> float:
        pass