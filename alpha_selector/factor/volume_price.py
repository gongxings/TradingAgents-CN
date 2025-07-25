# factor/volume_price.py
def add_volume_price_factors(df):
    df = df.copy()
    df['volume_ma5'] = df['volume'].rolling(5).mean()
    df['volume_ratio'] = df['volume'] / (df['volume_ma5'] + 1e-6)
    return df