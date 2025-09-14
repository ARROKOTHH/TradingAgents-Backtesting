"""
AkShare 美股数据获取工具
使用 AkShare API 获取美股历史行情和分时数据
"""
import akshare as ak
import pandas as pd
import stockstats
from datetime import datetime

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('agents')

def get_us_stock_min_akshare(symbol: str) -> str:
    """
    使用 AkShare 获取美股分时行情数据。

    Args:
        symbol: 标准美股代码 (e.g., "AAPL")

    Returns:
        格式化的分时行情字符串报告，如果失败则返回错误信息。
    """
    logger.info(f"  [akshare_us] 正在获取 {symbol} 的分时行情数据...")
    try:
        # 导入AkShare提供器以获取代码转换功能
        from .akshare_utils import get_akshare_provider
        provider = get_akshare_provider()
        
        # 转换为AkShare行情数据所需的格式
        hist_symbol = provider._convert_to_us_hist_symbol(symbol)
        
        min_data = ak.stock_us_hist_min_em(symbol=hist_symbol)
        if min_data.empty:
            logger.warning(f"  [akshare_us] 未获取到 {symbol} 的分时行情数据。")
            return "\n## 实时分时行情\n未获取到实时分时行情数据.\n"

        # 格式化报告
        report = "\n## 实时分时行情\n"
        report += f"- 最新价格: {min_data['收盘'].iloc[-1]}\n"
        report += f"- 更新时间: {min_data['时间'].iloc[-1]}\n"
        report += "#### 最近5条分时数据:\n"
        report += "```\n"
        report += min_data.tail().to_string(index=False)
        report += "\n```\n"
        
        logger.info(f"  [akshare_us] 成功获取并格式化 {symbol} 的分时行情数据。")
        return report

    except Exception as e:
        logger.error(f"❌ [akshare_us] 调用 akshare.stock_us_hist_min_em 获取 {symbol} 分时行情失败: {e}")
        return f"\n## 实时分时行情\n获取分时行情数据失败: {e}\n"

def get_us_stock_hist_akshare(symbol: str, start_date: str, end_date: str) -> str:
    """
    使用 AkShare 获取美股历史日K线数据，并格式化为报告。
    严格按照akshare官方文档进行调用。

    Args:
        symbol: 标准美股代码 (e.g., "AAPL")
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        格式化的历史行情字符串报告，如果失败则返回错误信息。
    """
    logger.info(f"📈 [akshare_us] 开始获取 {symbol} 的历史日K线数据 ({start_date} to {end_date})...")
    try:
        # 导入AkShare提供器以获取代码转换功能
        from .akshare_utils import get_akshare_provider
        provider = get_akshare_provider()
        
        # 转换为AkShare行情数据所需的格式
        hist_symbol = provider._convert_to_us_hist_symbol(symbol)
        
        # AkShare 的日期格式为 YYYYMMDD
        start_date_ak = start_date.replace("-", "")
        end_date_ak = end_date.replace("-", "")

        logger.debug(f"  [akshare_us] 调用 ak.stock_us_hist(symbol='{hist_symbol}', start_date='{start_date_ak}', end_date='{end_date_ak}', adjust='qfq')")
        
        # 严格按照官方文档调用，增加 period 和 adjust 参数
        hist_data = ak.stock_us_hist(
            symbol=hist_symbol, 
            period="daily",
            start_date=start_date_ak, 
            end_date=end_date_ak, 
            adjust="qfq" # hfq:后复权 qfq:前复权
        )

        if hist_data.empty:
            logger.error(f"❌ [akshare_us] AkShare 未返回 {symbol} 的历史数据。")
            return f"❌ 错误: AkShare 未返回股票代码 {symbol} 在 {start_date} 到 {end_date} 期间的任何历史数据。"

        # 数据重命名和预处理
        hist_data.rename(columns={
            '日期': 'Date', '开盘': 'Open', '收盘': 'Close', 
            '最高': 'High', '最低': 'Low', '成交量': 'Volume'
        }, inplace=True)
        hist_data['Date'] = pd.to_datetime(hist_data['Date'])
        hist_data.set_index('Date', inplace=True)

        # --- 数据格式化，模仿旧版逻辑 ---
        latest_price = hist_data['Close'].iloc[-1]
        price_change = hist_data['Close'].iloc[-1] - hist_data['Close'].iloc[0]
        price_change_pct = (price_change / hist_data['Close'].iloc[0]) * 100 if hist_data['Close'].iloc[0] != 0 else 0

        # --- 使用 stockstats 计算完整的技术指标 ---
        # stockstats 需要特定的列名: open, high, low, close, volume
        hist_data_for_stats = hist_data.copy()
        hist_data_for_stats.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}, inplace=True)
        stock_df = stockstats.StockDataFrame.retype(hist_data_for_stats)
        
        # 计算常用指标 (必须先访问列来触发计算)
        _ = stock_df['close_5_sma']
        _ = stock_df['close_10_sma']
        _ = stock_df['close_20_sma']
        _ = stock_df['macd']
        _ = stock_df['rsi_14']
        _ = stock_df['kdjk']
        _ = stock_df['kdjd']
        _ = stock_df['kdjj']
        _ = stock_df['boll']
        _ = stock_df['boll_ub']
        _ = stock_df['boll_lb']
        
        latest_indicators = stock_df.iloc[-1]

        # 构建报告
        report = f"# {symbol} 美股数据分析 (AkShare)\n\n"
        report += f"## 📊 基本信息\n"
        report += f"- 股票代码: {symbol}\n"
        report += f"- 数据期间: {start_date} 至 {end_date}\n"
        report += f"- 数据条数: {len(hist_data)}条\n"
        report += f"- 最新价格: ${latest_price:.2f}\n"
        report += f"- 期间涨跌: ${price_change:+.2f} ({price_change_pct:+.2f}%)\n\n"

        report += f"## 📈 价格统计\n"
        report += f"- 期间最高: ${hist_data['High'].max():.2f}\n"
        report += f"- 期间最低: ${hist_data['Low'].min():.2f}\n"
        report += f"- 平均成交量: {hist_data['Volume'].mean():,.0f}\n\n"

        report += f"## 🔍 技术指标 (最新值)\n"
        report += f"- **MA5 / MA10 / MA20**: ${latest_indicators.get('close_5_sma', 0):.2f} / ${latest_indicators.get('close_10_sma', 0):.2f} / ${latest_indicators.get('close_20_sma', 0):.2f}\n"
        report += f"- **MACD**: {latest_indicators.get('macd', 0):.2f} (Signal: {latest_indicators.get('macds', 0):.2f}, Hist: {latest_indicators.get('macdh', 0):.2f})\n"
        report += f"- **RSI(14)**: {latest_indicators.get('rsi_14', 0):.2f}\n"
        report += f"- **KDJ**: K={latest_indicators.get('kdjk', 0):.2f}, D={latest_indicators.get('kdjd', 0):.2f}, J={latest_indicators.get('kdjj', 0):.2f}\n"
        report += f"- **布林带**: 上轨={latest_indicators.get('boll_ub', 0):.2f}, 中轨={latest_indicators.get('boll', 0):.2f}, 下轨={latest_indicators.get('boll_lb', 0):.2f}\n\n"

        report += f"## 📋 最近5日数据\n"
        report += "```\n"
        report += hist_data[['Open', 'High', 'Low', 'Close', 'Volume']].tail().to_string()
        report += "\n```\n"

        # 调用函数获取分时行情并附加到报告中
        min_report = get_us_stock_min_akshare(symbol)
        report += min_report

        report += f"\n数据来源: AkShare API\n"
        report += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        logger.info(f"✅ [akshare_us] 成功获取并格式化 {symbol} 的历史行情报告。")
        return report

    except Exception as e:
        logger.error(f"❌ [akshare_us] 调用 akshare.stock_us_hist 获取 {symbol} 历史数据失败: {e}")
        return f"❌ 错误: 调用AkShare获取股票 {symbol} 数据时发生错误: {e}"

def get_us_financial_analysis_indicator(symbol: str) -> str:
    """
    使用 AkShare 获取美股主要财务指标，并格式化为报告。

    Args:
        symbol: 标准美股代码 (e.g., "AAPL")

    Returns:
        格式化的财务指标字符串报告，如果失败则返回错误信息。
    """
    logger.info(f"📊 [akshare_us] 开始获取 {symbol} 的财务分析指标...")
    try:
        # 获取所有单季报
        financial_df = ak.stock_financial_us_analysis_indicator_em(symbol=symbol, indicator="单季报")

        # --- 健壮性检查 ---
        if financial_df is None or financial_df.empty:
            logger.error(f"❌ [akshare_us] AkShare 未返回 {symbol} 的财务指标数据。")
            return f"❌ 错误: AkShare 未返回股票代码 {symbol} 的任何财务指标数据。"

        # --- 专注于最新的单季报 ---
        latest_report = financial_df.iloc[0]

        # 构建Markdown报告
        report = f"# {symbol} 最新季度财务指标分析 (AkShare)\n\n"
        report += f"## 📅 报告信息\n"
        # 使用 .get() 方法确保即使键不存在也不会报错
        report += f"- 报告日期: {latest_report.get('REPORT_DATE', 'N/A')}\n"
        report += f"- 会计准则: {latest_report.get('ACCOUNTING_STANDARDS', 'N/A')}\n\n"

        report += f"## 盈利能力\n"
        report += f"- **营业收入**: {latest_report.get('OPERATE_INCOME', 'N/A'):,.2f}\n"
        report += f"- **营收同比增长**: {latest_report.get('OPERATE_INCOME_YOY', 'N/A'):.2f}%\n"
        report += f"- **毛利润**: {latest_report.get('GROSS_PROFIT', 'N/A'):,.2f}\n"
        report += f"- **净利润**: {latest_report.get('PARENT_HOLDER_NETPROFIT', 'N/A'):,.2f}\n"
        report += f"- **净利同比增长**: {latest_report.get('PARENT_HOLDER_NETPROFIT_YOY', 'N/A'):.2f}%\n"
        report += f"- **每股收益(EPS)**: {latest_report.get('BASIC_EPS', 'N/A')}\n"
        report += f"- **毛利率**: {latest_report.get('GROSS_PROFIT_RATIO', 'N/A'):.2f}%\n"
        report += f"- **净利率**: {latest_report.get('NET_PROFIT_RATIO', 'N/A'):.2f}%\n"
        report += f"- **净资产收益率(ROE)**: {latest_report.get('ROE_AVG', 'N/A'):.2f}%\n"
        report += f"- **总资产报酬率(ROA)**: {latest_report.get('ROA', 'N/A'):.2f}%\n\n"

        report += f"## 偿债能力\n"
        report += f"- **流动比率**: {latest_report.get('CURRENT_RATIO', 'N/A'):.2f}\n"
        report += f"- **速动比率**: {latest_report.get('SPEED_RATIO', 'N/A'):.2f}\n"
        report += f"- **资产负债率**: {latest_report.get('DEBT_ASSET_RATIO', 'N/A'):.2f}%\n\n"

        report += f"## 营运能力\n"
        report += f"- **应收账款周转率**: {latest_report.get('ACCOUNTS_RECE_TR', 'N/A'):.2f}\n"
        report += f"- **存货周转率**: {latest_report.get('INVENTORY_TR', 'N/A'):.2f}\n"
        report += f"- **总资产周转率**: {latest_report.get('TOTAL_ASSETS_TR', 'N/A'):.2f}\n\n"
        
        report += f"\n数据来源: AkShare (东方财富源)\n"
        report += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        logger.info(f"✅ [akshare_us] 成功获取并格式化 {symbol} 的最新季度财务指标报告。")
        return report

    except Exception as e:
        logger.error(f"❌ [akshare_us] 调用 akshare.stock_financial_us_analysis_indicator_em 获取 {symbol} 财务指标失败: {e}")
        return f"❌ 错误: 调用AkShare获取股票 {symbol} 财务指标时发生错误: {e}"
