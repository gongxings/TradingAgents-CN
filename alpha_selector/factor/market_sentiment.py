# factor/market_sentiment.py
import akshare as ak

def get_hot_industries(top_k=3):
    try:
        df = ak.stock_sector_fund_flow_ths()
        df = df[['行业', '涨跌幅', '主力净流入']]
        df['score'] = df['涨跌幅'] * 0.6 + (df['主力净流入'] / 1e8) * 0.4
        return df.nlargest(top_k, 'score')['行业'].tolist()
    except Exception as e:
        print(f"技术指标计算失败: {e}")
        return ['未知']


def get_hot_industries_by_concept(top_k=3):
    """使用概念板块涨幅榜作为热度参考"""
    try:
        df = ak.stock_board_concept_summary_ths()
        df = df[['板块名称', '涨跌幅', '净流入资金']]
        df = df.rename(columns={'板块名称': '行业', '净流入资金': '主力净流入'})
        df['score'] = df['涨跌幅'] * 0.6 + (df['主力净流入'] / 1e8) * 0.4
        return df.nlargest(top_k, 'score')['行业'].tolist()
    except Exception as e:
        print(f"概念板块接口失败: {e}")
        return None


if __name__ == '__main__':
    df = get_hot_industries_by_concept()
    print(df)
