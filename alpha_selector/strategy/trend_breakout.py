# strategy/trend_breakout.py
from .base_strategy import BaseStrategy


class TrendBreakoutStrategy(BaseStrategy):
    def name(self):
        return "趋势突破"

    def condition(self, df):
        if len(df) < 2: return False
        last = df.iloc[-1]
        prev = df.iloc[-2]
        return (last['close'] > prev['high_5d']
                and last['volume_ratio'] > 1.8
                and last['ma5'] > last['ma10'])

    def score(self, df):
        last = df.iloc[-1]
        return last['volume_ratio'] * 0.7 + (last['close'] / last['ma5'] - 1) * 0.3
