
import pandas as pd
from datetime import datetime, timedelta
from tradingagents.dataflows.akshare_utils import AKShareProvider
from tradingagents.utils.logging_manager import get_logger
import stockstats

logger = get_logger('agents')

def get_china_stock_indicators(symbol: str, date: str = None) -> dict:
    """
    获取A股的技术指标

    :param symbol: 股票代码
    :param date: 日期
    :return: 技术指标
    """
    try:
        # 1. 确定日期范围
        end_date_obj = datetime.strptime(date, '%Y-%m-%d') if date else datetime.now()
        start_date_obj = end_date_obj - timedelta(days=365)
        
        start_date_str = start_date_obj.strftime('%Y%m%d')
        end_date_str = end_date_obj.strftime('%Y%m%d')

        # 2. 获取数据
        provider = AKShareProvider()
        logger.info(f"正在为 {symbol} 获取 {start_date_str} 到 {end_date_str} 的数据以计算技术指标...")
        stock_data = provider.get_stock_data(symbol, start_date=start_date_str, end_date=end_date_str)

        if stock_data is None or stock_data.empty:
            logger.warning(f"无法获取 {symbol} 的股票数据")
            return {}

        # 2. 数据预处理
        stock_data.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }, inplace=True)
        
        # 确保 'date' 列存在并转换为 datetime 对象
        if 'date' in stock_data.columns:
            stock_data['date'] = pd.to_datetime(stock_data['date'])
        else:
            # 如果没有日期列，添加一个索引作为日期
            stock_data['date'] = pd.to_datetime(stock_data.index)
        
        # 将DataFrame转换为StockDataFrame
        stock_df = stockstats.StockDataFrame.retype(stock_data)

        # 3. 计算技术指标
        # 计算 MACD
        _ = stock_df['macd']
        # 计算 RSI
        _ = stock_df['rsi_6']
        _ = stock_df['rsi_12']
        # 计算 KDJ
        _ = stock_df['kdjk']
        _ = stock_df['kdjd']
        _ = stock_df['kdjj']
        # 计算 DMA
        _ = stock_df['dma']
        # 计算 TRIX
        _ = stock_df['trix']
        
        # 提取最新的指标
        latest_indicators = stock_df.iloc[-1]

        # 确保所有需要的列都存在
        required_columns = ['close', 'macd', 'macds', 'macdh', 'rsi_6', 'rsi_12', 
                           'kdjk', 'kdjd', 'kdjj', 'dma', 'trix']
        
        # 检查缺失的列并记录警告
        missing_columns = [col for col in required_columns if col not in latest_indicators.index]
        if missing_columns:
            logger.warning(f"指标计算中缺少以下列: {missing_columns}")
            
        def safe_format(value, format_str="{:.2f}"):
            """安全地格式化数值，处理NaN和None"""
            if pd.isna(value) or value is None:
                return "N/A"
            try:
                return format_str.format(float(value))
            except (ValueError, TypeError):
                return "N/A"
                
        # 获取日期（从索引中）
        date_str = 'N/A'
        if hasattr(latest_indicators.name, 'strftime'):
            try:
                date_str = latest_indicators.name.strftime('%Y-%m-%d')
            except:
                date_str = str(latest_indicators.name)
                
        indicators = {
            "symbol": symbol,
            "date": date_str,
            "close": safe_format(latest_indicators.get('close')),
            "MACD": {
                "MACD": safe_format(latest_indicators.get('macd')),
                "MACD_signal": safe_format(latest_indicators.get('macds')),
                "MACD_hist": safe_format(latest_indicators.get('macdh')),
            },
            "RSI": {
                "RSI_6": safe_format(latest_indicators.get('rsi_6')),
                "RSI_12": safe_format(latest_indicators.get('rsi_12')),
            },
            "KDJ": {
                "K": safe_format(latest_indicators.get('kdjk')),
                "D": safe_format(latest_indicators.get('kdjd')),
                "J": safe_format(latest_indicators.get('kdjj')),
            },
            "DMA": {
                "DMA": safe_format(latest_indicators.get('dma')),
                "AMA": safe_format(latest_indicators.get('ama', latest_indicators.get('dma'))),  # 使用dma作为备选
            },
            "TRIX": {
                "TRIX": safe_format(latest_indicators.get('trix')),
                "MATRIX": safe_format(latest_indicators.get('trix_9_sma', latest_indicators.get('trix'))),  # 使用trix作为备选
            }
        }
        
        logger.info(f"成功计算 {symbol} 的技术指标")
        return indicators

    except Exception as e:
        logger.error(f"计算 {symbol} 的技术指标时出错: {e}")
        return {}

