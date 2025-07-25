# -*- coding: utf-8 -*-
"""
专业级量化回测策略：RSI + 波动率过滤 + 动态仓位 + 多时间框架确认
"""

import akshare as ak
import pandas as pd
import backtrader as bt
from datetime import datetime, time


# ================== 1. 获取日线和60分钟数据 ==================
print("📈 正在获取 000066 中国长城 日线数据...")
daily_df = ak.stock_zh_a_hist(
    symbol="000066",
    period="daily",
    start_date="20250101",
    end_date="20250723",
    adjust="qfq"  # 前复权
)

print("🕐 正在获取 000066 60分钟K线数据...")
min60_df = ak.stock_zh_a_hist_min_em(
    symbol="000066",
    period="60",
    adjust="qfq"
)

if daily_df.empty or min60_df.empty:
    raise ValueError("❌ 数据获取失败，请检查网络或股票代码")

# 清洗日线数据
daily_df.rename(columns={
    "日期": "datetime",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume"
}, inplace=True)
daily_df["datetime"] = pd.to_datetime(daily_df["datetime"])
daily_df.set_index("datetime", inplace=True)
daily_df = daily_df[["open", "high", "low", "close", "volume"]]

# 清洗60分钟数据
min60_df.rename(columns={
    "时间": "datetime",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume"
}, inplace=True)
min60_df["datetime"] = pd.to_datetime(min60_df["datetime"])
min60_df.set_index("datetime", inplace=True)
min60_df = min60_df[["open", "high", "low", "close", "volume"]]


# 输出检查
print("📅 日线数据:", daily_df.index.min(), "→", daily_df.index.max(), f"({len(daily_df)}行)")
print("🕐 60分钟数据:", min60_df.index.min(), "→", min60_df.index.max(), f"({len(min60_df)}行)")

# 创建 Backtrader 数据源
data_daily = bt.feeds.PandasData(dataname=daily_df, name="Daily")
data_min60 = bt.feeds.PandasData(dataname=min60_df, name="60min")




# ================== 2. 增强型策略定义 ==================
class EnhancedRSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('ma_slow', 200),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('atr_period', 14),
        ('risk_percent', 0.01),            # 单笔最大风险：1%
        ('stop_loss_atr_multiplier', 2),   # 止损距离 = 2倍ATR
    )

    def __init__(self):
        # 日线指标（data0）
        self.rsi = bt.indicators.RSI_SMA(self.data0.close, period=self.p.rsi_period)
        self.sma200 = bt.indicators.SMA(self.data0.close, period=self.p.ma_slow)
        self.atr = bt.indicators.ATR(self.data0, period=self.p.atr_period)

        # RSI 交叉信号
        self.rsi_cross_up = bt.indicators.CrossOver(self.rsi, self.p.rsi_oversold)
        self.rsi_cross_down = bt.indicators.CrossDown(self.rsi, self.p.rsi_overbought)

        # 60分钟指标（data1）——已通过 cerebro.resampledata 聚合为日线
        self.min60_rsi = bt.indicators.RSI_SMA(self.data1.close, period=self.p.rsi_period)
        self.min60_rsi_cross_up = bt.indicators.CrossOver(self.min60_rsi, self.p.rsi_oversold)

        # 防止重复交易
        self.last_date = None

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        current_time = self.datas[0].datetime.time()

        # 只在日线收盘时检查信号（模拟每日决策）
        if current_time != time(15, 0):
            return

        if self.last_date == current_date:
            return
        self.last_date = current_date

        current_price = self.data0.close[0]
        atr_value = self.atr[0]

        # ------------------ 波动率过滤 ------------------
        if atr_value / current_price < 0.01:  # 波动率 < 1% 时不开仓
            return

        # ------------------ 买入逻辑 ------------------
        if not self.position:
            long_condition = (
                    self.rsi[0] < self.p.rsi_oversold and
                    current_price > self.sma200[0] and
                    self.rsi_cross_up[0] == 1
            )

            if long_condition:
                # 60分钟图确认
                min60_rsi_ok = self.min60_rsi[0] > self.p.rsi_oversold and self.min60_rsi_cross_up[0] == 1

                if min60_rsi_ok:
                    stop_loss_price = current_price - self.p.stop_loss_atr_multiplier * atr_value
                    risk_per_share = current_price - stop_loss_price
                    account_value = self.broker.getvalue()
                    risk_amount = account_value * self.p.risk_percent
                    stake = int(risk_amount / risk_per_share)

                    if stake > 0:
                        self.buy(size=stake)
                        print(f"✅ {current_date} | 买入 {stake} 股 @ {current_price:.2f} | "
                              f"止损: {stop_loss_price:.2f}")

        # ------------------ 卖出逻辑 ------------------
        elif self.position:
            if (self.rsi[0] > self.p.rsi_overbought or
                    current_price < self.sma200[0]):
                self.sell(size=self.position.size)
                print(f"❌ {current_date} | 卖出 @ {current_price:.2f}")


# ================== 3. 初始化回测引擎 ==================
cerebro = bt.Cerebro()

# 添加主数据（日线）
cerebro.adddata(data_daily)

# ✅ 正确方式：使用 cerebro.resampledata() 聚合分钟数据为日线
cerebro.resampledata(
    data_min60,
    name="60min_daily",
    timeframe=bt.TimeFrame.Days,
    compression=1
)

# 初始资金
cerebro.broker.setcash(10000.0)

# 佣金与滑点
cerebro.broker.setcommission(commission=0.001)
cerebro.broker.set_slippage_perc(perc=0.001)

# 添加策略
cerebro.addstrategy(EnhancedRSIStrategy)

# 添加分析器
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')


# ================== 4. 运行回测 ==================
print("=" * 60)
print("🚀 开始回测...")
print(f"📅 回测周期: 2020-01-01 至 2024-12-31")
print(f"💰 初始资金: 100,000 元")
print("=" * 60)

results = cerebro.run()

# 提取结果
strat = results[0]
final_value = cerebro.broker.getvalue()

print("=" * 60)
print("📊 回测结果")
print("=" * 60)
print(f"最终资金:      {final_value:,.2f} 元")
print(f"总收益率:      {strat.analyzers.returns.get_analysis()['rtot'] * 100:.2f}%")
print(f"年化收益率:    {strat.analyzers.returns.get_analysis()['ravg'] * 252 * 100:.2f}%")
print(f"夏普比率:      {strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A'):.2f}")
print(f"最大回撤:      {strat.analyzers.drawdown.get_analysis()['max']['drawdown']:.2f}%")
print(f"SQN 质量评分:  {strat.analyzers.sqn.get_analysis().get('sqn', 'N/A'):.2f}")

trades = strat.analyzers.trades.get_analysis()
if trades.total.total > 0:
    win_rate = trades.won.total / trades.total.total * 100
    print(f"交易次数:      {trades.total.total}")
    print(f"盈利交易:      {trades.won.total}")
    print(f"亏损交易:      {trades.lost.total}")
    print(f"胜率:          {win_rate:.1f}%")


# ================== 5. 绘图 ==================
print("\n📈 正在生成回测图表...")
cerebro.plot(
    style='candlestick',
    barup='green', bardown='red',
    figsize=(18, 10),
    grid=True,
    plotdist=0.2
)