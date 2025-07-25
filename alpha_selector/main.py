# main.py
from config import Config
from data_loader import get_a_share_list, get_stock_daily, get_stock_industry
from factor.technical import add_technical_factors
from factor.volume_price import add_volume_price_factors
from factor.market_sentiment import get_hot_industries
from strategy.trend_breakout import TrendBreakoutStrategy
from strategy.reversal import ReversalStrategy
from strategy.ma_cross import MAGoldenCrossStrategy
import pandas as pd
import matplotlib.pyplot as plt


def load_data_with_factors(symbol):
    df = get_stock_daily(symbol, Config.START_DATE, Config.END_DATE)
    if df is None or len(df) < 20: return None
    df = add_technical_factors(df)
    df = add_volume_price_factors(df)
    return df


def main():
    print("🚀 启动 AlphaSelector v3.1 - 多策略智能选股系统")

    stock_df = get_a_share_list()
    print(f"✅ 加载股票池：{len(stock_df)} 只股票")

    # hot_industries = get_hot_industries()
    # print(f"🔥 当前热门板块：{hot_industries}")

    strategies = [
        TrendBreakoutStrategy(),
        ReversalStrategy(),
        MAGoldenCrossStrategy()
    ]

    results = []
    for strategy in strategies:
        count = 0
        for _, row in stock_df.head(50).iterrows():
            df = load_data_with_factors(row['代码'])
            if df is None: continue
            if strategy.condition(df):
                industry = get_stock_industry(row['代码'])
                in_hot = any(ind in row['名称'] or ind in industry for ind in hot_industries)
                results.append({
                    '代码': row['代码'],
                    '名称': row['名称'],
                    '行业': industry,
                    '策略': strategy.name(),
                    '评分': round(strategy.score(df), 3),
                    '股价': round(df['close'].iloc[-1], 2),
                    '热点': '是' if in_hot else '否'
                })
                count += 1
        print(f"✅ [{strategy.name()}] 选出 {count} 只")

    if results:
        results_df = pd.DataFrame(results)
        print("\n" + "=" * 70)
        print("🎯 多策略选股结果（按策略分组）")
        print("=" * 70)
        print(results_df.to_string(index=False))

        # 统计
        summary = results_df.groupby('策略').agg(
            数量=('代码', 'size'),
            平均评分=('评分', 'mean')
        ).round(3)
        print("\n📊 策略表现对比：")
        print(summary)

        # 可视化
        summary['数量'].plot(kind='bar', title="各策略选股数量", rot=0, color=['skyblue', 'lightgreen', 'salmon'])
        plt.ylabel("数量")
        plt.grid(axis='y', alpha=0.3)
        plt.show()
    else:
        print("❌ 未选出符合条件的股票")


if __name__ == "__main__":
    main()
