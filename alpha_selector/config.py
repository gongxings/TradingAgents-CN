# config.py
import datetime


class Config:
    START_DATE = "20250101"
    END_DATE = datetime.datetime.now().strftime("%Y%m%d")
    MIN_MARKET_VALUE = 3_000_000_000
    EXCLUDE_ST = True
    EXCHANGE_PREFIXES = ['00', '60']
