# strategy/ma_cross.py
from .base_strategy import BaseStrategy

class MAGoldenCrossStrategy(BaseStrategy):
    def name(self):
        return "均线金叉"

    def condition(self, df):
        if len(df) < 2: return False
        last = df.iloc[-1]
        prev = df.iloc[-2]
        return (prev['ma5'] <= prev['ma10']
                and last['ma5'] > last['ma10']
                and last['volume_ratio'] > 1.3)

    def score(self, df):
        return df['volume_ratio'].iloc[-1]