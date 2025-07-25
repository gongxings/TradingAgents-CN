# -*- coding: utf-8 -*-
"""
股票量化回测与选股系统（修复版）
使用 AKShare 获取数据，Backtrader 进行回测
已修复分析器调用错误，数据获取不加前缀
"""

import akshare as ak
import pandas as pd
import backtrader as bt
from datetime import datetime
import numpy as np
import warnings

warnings.filterwarnings('ignore')


# ==================== 1. 数据获取（不加 sh/sz 前缀）====================
def get_stock_data(symbol, start_date, end_date):
    """
    使用 AKShare 获取 A股历史数据（前复权）
    :param symbol: 股票代码，如 '600036'（无需加 sh/sz，akshare 会自动识别）
    :param start_date: '20200101'
    :param end_date: '20231231'
    :return: pd.DataFrame
    """
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                start_date=start_date, end_date=end_date,
                                adjust="qfq")
        if df.empty:
            print(f"{symbol}: 数据为空")
            return None

        # 重命名列
        df.rename(columns={
            '日期': 'datetime',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        }, inplace=True)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        return df
    except Exception as e:
        print(f"获取 {symbol} 数据失败: {e}")
        return None


# ==================== 2. 策略：双均线交叉 ====================
class SMACrossStrategy(bt.Strategy):
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('stop_loss_pct', 0.03),  # 3%止损
        ('take_profit_pct', 0.05),  # 5%止盈
        ('print_log', False),
    )


def __init__(self):
    self.data_close = self.datas[0].close
    self.sma_fast = bt.indicators.SMA(self.data_close, period=self.p.fast_period)
    self.sma_slow = bt.indicators.SMA(self.data_close, period=self.p.slow_period)
    self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)

    self.atr = bt.indicators.ATR(self.datas[0], period=14)
    self.sma_atr = bt.indicators.SMA(self.atr, period=20)
    self.vol_sma = bt.indicators.SMA(self.datas[0].volume, period=20)
    self.vol_ratio = self.datas[0].volume / self.vol_sma

    self.order = None


def log(self, txt):
    if self.p.print_log:
        print(f"{self.datas[0].datetime.date(0)} {txt}")


def notify_order(self, order):
    if order.status in [order.Submitted, order.Accepted]:
        return
    if order.status == order.Completed:
        if order.isbuy():
            self.log(f"买入 @ {order.executed.price:.2f}")
        elif order.issell():
            self.log(f"卖出 @ {order.executed.price:.2f}")
    self.order = None


def next(self):
    if self.order:
        return

    # 过滤条件1：波动率太低（震荡市）
    if self.atr[0] < 0.8 * self.sma_atr[0]:
        return

    # 过滤条件2：成交量不足
    if self.vol_ratio[0] < 1.2:
        return

    # 止损止盈
    if self.position:
        current_price = self.data.close[0]
        buy_price = self.position.price
        if current_price < buy_price * (1 - self.p.stop_loss_pct):
            self.sell()
            self.log(f"止损卖出 @ {current_price:.2f}")
            return
        if current_price > buy_price * (1 + self.p.take_profit_pct):
            self.sell()
            self.log(f"止盈卖出 @ {current_price:.2f}")
            return

    # 交易信号
    if not self.position and self.crossover > 0:
        self.buy()

    elif self.position and self.crossover < 0:
        self.sell()


# ==================== 3. 回测执行（带分析器）====================
def run_backtest(data, strategy, **kwargs):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy, **kwargs)

    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)  # 0.1%
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    # === 添加分析器（关键！不能在外部手动调用）===
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe',
                        riskfreerate=0.01, annualize=True, timeframe=bt.TimeFrame.Days)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print(f'初始资金: {cerebro.broker.getvalue():,.2f}')
    result = cerebro.run()
    print(f'最终资金: {cerebro.broker.getvalue():,.2f}')

    return cerebro, result


# ==================== 4. 绩效分析（从 result 提取）====================
def analyze_performance(cerebro, result):
    strat = result[0]  # 获取策略实例

    # 提取分析器
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()

    roi = returns.get('rnorm100', 0)
    sharpe_ratio = sharpe.get('sharperatio', float('nan'))
    max_drawdown = drawdown.get('max', {}).get('drawdown', 0.0)

    total_trades = trades.get('total', {}).get('total', 0)
    wins = trades.get('won', {}).get('total', 0)
    win_rate = wins / total_trades if total_trades > 0 else 0

    print(f"\n=== 绩效分析 ===")
    print(f"总收益率: {roi:.2f}%")
    # print(f"年化夏普比率: {sharpe_ratio:.3f}")
    print(f"最大回撤: {max_drawdown:.2f}%")
    print(f"交易总数: {total_trades}, 胜率: {win_rate:.2%}")

    return {
        'roi': roi,
        'sharpe': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'total_trades': total_trades,
        'win_rate': win_rate
    }


# ==================== 5. 参数优化 ====================
def optimize_strategy(symbol, start_date, end_date):
    data = get_stock_data(symbol, start_date, end_date)
    if data is None or len(data) < 100:
        print(f"{symbol} 数据不足，跳过优化。")
        return None

    cerebro = bt.Cerebro(optreturn=True)
    cerebro.optstrategy(
        SMACrossStrategy,
        fast_period=range(5, 21, 5),
        slow_period=range(30, 61, 10)
    )

    data_feed = bt.feeds.PandasData(dataname=data)
    cerebro.adddata(data_feed)
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)

    # 添加分析器用于优化评估
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

    print(f"正在对 {symbol} 进行参数优化...")
    results = cerebro.run(maxcpus=1)

    opt_results = []
    for result in results:
        p = result[0].params
        opt_results.append({
            'symbol': symbol,
            'fast': p.fast_period,
            'slow': p.slow_period,
            'sharpe': result[0].analyzers.sharpe.get_analysis()['sharperatio'],
            'return': result[0].analyzers.returns.get_analysis()['rnorm100'],
            'max_drawdown': result[0].analyzers.drawdown.get_analysis()['max']['drawdown']
        })

    df = pd.DataFrame(opt_results)
    best = df.loc[df['sharpe'].idxmax()]
    print(f"✅ 最优参数: fast={best['fast']}, slow={best['slow']}, 夏普={best['sharpe']:.3f}")
    return best.to_dict()


# ==================== 6. 股票筛选 ====================
def screen_stocks_for_strategy(stock_list, start_date, end_date):
    selected = []
    print("\n🔍 正在筛选符合条件的股票...")

    for symbol in stock_list:
        data = get_stock_data(symbol, start_date, end_date)
        if data is None or len(data) < 30:
            continue

        close = data['close'].iloc[-1]
        sma10 = data['close'].rolling(10).mean().iloc[-1]
        sma30 = data['close'].rolling(30).mean().iloc[-1]

        # 多头排列
        if close > sma10 > sma30:
            # 检查最近是否发生金叉
            fast_ma = data['close'].rolling(10).mean()
            slow_ma = data['close'].rolling(30).mean()
            cross = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
            if cross.iloc[-3:].any():  # 最近3天内
                selected.append({
                    '股票代码': symbol,
                    '当前价': round(close, 2),
                    'SMA10': round(sma10, 2),
                    'SMA30': round(sma30, 2),
                    '偏离度(%)': round((close - sma10) / sma10 * 100, 2)
                })

    if selected:
        df_selected = pd.DataFrame(selected)
        df_selected.sort_values('偏离度(%)', inplace=True)
        print(f"\n✅ 共筛选出 {len(df_selected)} 只股票：")
        print(df_selected.to_string(index=False))
        df_selected.to_csv('selected_stocks.csv', index=False, encoding='utf_8_sig')
        print("\n📊 推荐股票已保存至 'selected_stocks.csv'")
        return df_selected
    else:
        print("❌ 未找到符合条件的股票。")
        return pd.DataFrame()


# ==================== 7. 主函数 ====================
def main():
    # 股票代码直接写数字，如 '600036'，akshare 会自动识别市场
    STOCK_POOL = ['600036', '000858', '600519', '601318', '002594']  # 招行、五粮液、茅台、平安、比亚迪
    START_DATE = '20200101'
    END_DATE = '20231231'

    print("🚀 股票回测与选股系统启动...\n")

    # 示例1：回测招商银行
    print("📈 示例1：对 招商银行(600036) 进行回测")
    data = get_stock_data('600036', START_DATE, END_DATE)
    if data is not None:
        cerebro, result = run_backtest(data, SMACrossStrategy, fast_period=15, slow_period=30)
        performance = analyze_performance(cerebro, result)
        print(performance)

    # # 示例2：参数优化
    # print("\n⚙️ 示例2：对 茅台(600519) 进行参数优化")
    # best = optimize_strategy('600519', START_DATE, END_DATE)
    # print(best)
    #
    # # 示例3：选股
    # print("\n🎯 示例3：筛选当前符合策略的股票")
    # candidates = screen_stocks_for_strategy(STOCK_POOL, '20231001', END_DATE)
    # print(candidates)


if __name__ == '__main__':
    main()
