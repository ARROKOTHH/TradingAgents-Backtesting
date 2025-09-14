
import akshare as ak
import pandas as pd
import stockstats
from typing import Dict, Union

def get_us_stock_indicators(symbol: str) -> Dict[str, Union[str, float]]:
    """
    获取美股的常用技术指标，包括MACD和布林带。

    Args:
        symbol (str): 美股代码, 例如 "AAPL"。

    Returns:
        Dict[str, Union[str, float]]: 包含最新技术指标值的字典。
                                      如果获取数据失败，则返回包含错误信息的字典。
    """
    try:
        # 1. 使用 akshare 获取美股历史数据（前复权）
        stock_hist_df = ak.stock_us_hist(symbol=symbol, adjust="qfq")

        if stock_hist_df.empty:
            return {"error": f"无法获取股票代码 {symbol} 的历史数据。"}

        # 2. 重命名列名以兼容 stockstats
        stock_hist_df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }, inplace=True)

        # 3. 将 pandas.DataFrame 转换为 stockstats.StockDataFrame
        stock_df = stockstats.StockDataFrame.retype(stock_hist_df)

        # 4. 计算 MACD 和布林带指标
        # stockstats 会自动计算并在列中提供这些值
        # MACD 相关: macd(macd线), macds(信号线), macdh(柱状图)
        # 布林带相关: boll(中轨), boll_ub(上轨), boll_lb(下轨)
        
        # 提取最新的指标值
        latest_indicators = stock_df.iloc[-1]

        result = {
            "symbol": symbol,
            "date": latest_indicators['date'],
            "close": latest_indicators['close'],
            "macd": latest_indicators.get('macd'),
            "macd_signal": latest_indicators.get('macds'),
            "macd_hist": latest_indicators.get('macdh'),
            "bollinger_upper": latest_indicators.get('boll_ub'),
            "bollinger_middle": latest_indicators.get('boll'),
            "bollinger_lower": latest_indicators.get('boll_lb'),
        }
        
        return result

    except Exception as e:
        return {"error": f"计算指标时发生错误: {str(e)}"}

if __name__ == '__main__':
    # 模块自测试代码
    # 测试苹果公司的股票
    aapl_indicators = get_us_stock_indicators("AAPL")
    print("AAPL 技术指标:")
    print(aapl_indicators)

    # 测试一个不存在的股票
    invalid_indicators = get_us_stock_indicators("INVALIDSTOCK")
    print("\n无效股票代码测试:")
    print(invalid_indicators)
