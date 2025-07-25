# data_loader.py
from logutils.logger import get_logger
import akshare as ak
import pandas as pd

logger = get_logger("data_loader")


def get_a_share_list():
    logger.info("正在获取A股股票列表...")
    try:
        df = ak.stock_zh_a_spot_em()
        df = df[df['代码'].str.startswith(('00', '60'))]
        df = df[~df['名称'].str.contains('ST')]
        df = df[df['流通市值'] >= 3_000_000_000]
        logger.info(f"✅ 成功加载 {len(df)} 只股票")
        return df[['代码', '名称']]
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return pd.DataFrame(columns=['代码', '名称'])


def get_stock_daily(symbol, start_date, end_date):
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily",
                                start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or df.empty:
            logger.warning(f"⚠️ {symbol} 无行情数据")
            return None

        df.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount',
                      'amplitude', 'pct_change', 'change', 'turnover']
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        logger.debug(f"📈 {symbol} 获取 {len(df)} 天数据")
        return df.sort_index()
    except Exception as e:
        logger.error(f"❌ 获取 {symbol} 数据失败: {e}")
        return None


def get_stock_industry(symbol):
    try:
        info = ak.stock_individual_info_em(symbol=symbol)
        industry = info[info['item'] == '所属行业']['value'].iloc[0]
        return industry
    except Exception as e:
        logger.warning(f"⚠️ 获取 {symbol} 行业信息失败: {e}")
        return "未知"
