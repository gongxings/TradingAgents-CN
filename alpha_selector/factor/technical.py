# factor/technical.py
def add_technical_factors(df):
    try:
        df = df.copy()
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(6).mean()
        loss = -delta.where(delta < 0, 0).rolling(6).mean()
        rs = gain / (loss + 1e-6)
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        df['high_5d'] = df['high'].rolling(5).max().shift(1)

        print("✅ 技术指标计算完成")
        return df
    except Exception as e:
        print(f"技术指标计算失败: {e}")
        return df
