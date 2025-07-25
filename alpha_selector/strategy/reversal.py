# strategy/reversal.py
from .base_strategy import BaseStrategy


class ReversalStrategy(BaseStrategy):
    def name(self):
        return "超跌反弹"

    def condition(self, df):
        if len(df) < 5: return False
        recent = df.tail(5)
        is_declining = all(recent['pct_change'].iloc[i] < 0 for i in range(3))
        is_shrinking = all(recent['volume'].iloc[i] <= recent['volume'].iloc[i + 1] for i in range(3))
        is_last_up = recent['pct_change'].iloc[-1] > 2 and recent['volume'].iloc[-1] > recent['volume'].iloc[-2] * 1.5
        return is_declining and is_shrinking and is_last_up

    def score(self, df):
        return df['pct_change'].iloc[-1]
