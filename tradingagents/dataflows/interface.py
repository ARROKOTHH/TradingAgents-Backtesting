from typing import Annotated, Dict
import time
import os
from .reddit_utils import fetch_top_from_category
from .chinese_finance_utils import get_chinese_social_sentiment
from .googlenews_utils import getNewsData
from .akshare_utils import get_akshare_provider
from .akshare_us_utils import get_us_stock_hist_akshare, get_us_financial_analysis_indicator

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('agents')
logger = setup_dataflow_logging()

# AKShare is now the primary source
AKSHARE_HK_AVAILABLE = True
try:
    import akshare
except ImportError:
    AKSHARE_HK_AVAILABLE = False


def get_google_news(
    query: Annotated[
        str,
        "Query to search with",
    ],
    curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"] = 7,
) -> str:
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    query = query.replace(" ", "+")
    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    logger.info(f"[Google新闻] 开始获取新闻，查询: {query}, 时间范围: {before} 至 {curr_date}")
    news_results = getNewsData(query, before, curr_date)

    news_str = ""
    for news in news_results:
        news_str += f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"

    if not news_results:
        logger.warning(f"[Google新闻] 未找到相关新闻，查询: {query}")
        return ""

    logger.info(f"[Google新闻] 成功获取 {len(news_results)} 条新闻，查询: {query}")
    return f"## {query.replace('+', ' ')} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_reddit_global_news(
    curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"] = 7,
) -> str:
    """Retrieve global news from Reddit within a specified time frame."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before_str = before.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching Reddit global news from {before_str} to {curr_date}")
    # posts = fetch_top_from_category("global_news", ...)
    return f"Placeholder for Reddit global news from {before_str} to {curr_date}"

def get_reddit_company_news(
    ticker: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"] = 7,
) -> str:
    """Retrieve the latest news about a given stock from Reddit."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before_str = before.strftime("%Y-%m-%d")
    
    logger.info(f"Fetching Reddit company news for {ticker} from {before_str} to {curr_date}")
    # posts = fetch_top_from_category("company_news", ticker, ...)
    return f"Placeholder for Reddit company news for {ticker} from {before_str} to {curr_date}"


# ==================== 统一数据源接口 ====================

def get_china_stock_data_unified(
    ticker: Annotated[str, "中国股票代码"],
    start_date: Annotated[str, "开始日期"],
    end_date: Annotated[str, "结束日期"]
) -> str:
    """统一的中国A股数据获取接口 (已重构为仅使用AKShare)"""
    logger.info(f"📊 [统一接口] 开始获取中国股票数据 for {ticker}")
    try:
        from .data_source_manager import get_china_stock_data_unified as manager_get_data
        return manager_get_data(ticker, start_date, end_date)
    except Exception as e:
        logger.error(f"❌ [统一接口] 获取股票数据失败: {e}", exc_info=True)
        return f"❌ 获取{ticker}股票数据失败: {e}"


def get_china_stock_info_unified(
    ticker: Annotated[str, "中国股票代码"]
) -> str:
    """统一的中国A股基本信息获取接口 (已重构为仅使用AKShare)"""
    try:
        from .data_source_manager import get_china_stock_info_unified as manager_get_info
        info = manager_get_info(ticker)
        if info and info.get('name'):
            return f"股票代码: {ticker}\n股票名称: {info.get('name', '未知')}\n所属行业: {info.get('industry', '未知')}"
        else:
            return f"❌ 未能获取{ticker}的基本信息"
    except Exception as e:
        logger.error(f"❌ [统一接口] 获取股票信息失败: {e}", exc_info=True)
        return f"❌ 获取{ticker}股票信息失败: {e}"

def get_hk_stock_data_unified(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """获取港股数据的统一接口 (已重构为仅使用AKShare)"""
    logger.info(f"🇭🇰 获取港股数据: {symbol}")
    if AKSHARE_HK_AVAILABLE:
        from .hk_stock_utils import get_hk_stock_data_akshare
        return get_hk_stock_data_akshare(symbol, start_date, end_date)
    else:
        return f"❌ 无法获取港股{symbol}数据 - AKShare不可用"

def get_hk_stock_info_unified(symbol: str) -> Dict:
    """获取港股信息的统一接口 (已重构为仅使用AKShare)"""
    if AKSHARE_HK_AVAILABLE:
        from .hk_stock_utils import get_hk_stock_info_akshare
        return get_hk_stock_info_akshare(symbol)
    else:
        return {{'symbol': symbol, 'name': f'港股{{symbol}}', 'error': 'AKShare不可用'}}

def get_us_stock_data_akshare(symbol: str, start_date: str, end_date: str) -> str:
    """
    接口层函数，用于获取美股历史行情数据。
    它调用底层的 akshare_us_utils 来执行实际的数据获取。
    """
    logger.info(f"🇺🇸 [接口] 开始获取美股行情数据 for {symbol}")
    try:
        return get_us_stock_hist_akshare(symbol, start_date, end_date)
    except Exception as e:
        logger.error(f"❌ [接口] 获取美股行情数据失败: {e}", exc_info=True)
        return f"❌ 获取美股 {symbol} 行情数据失败: {e}"

def get_us_fundamentals_akshare(symbol: str, curr_date: str) -> str:
    """
    接口层函数，用于获取美股财务指标数据。
    它调用底层的 akshare_us_utils 来执行实际的数据获取。
    """
    logger.info(f"🇺🇸 [接口] 开始获取美股财务数据 for {symbol}")
    try:
        # 注意：curr_date 在底层函数中当前未使用，但保留接口一致性
        return get_us_financial_analysis_indicator(symbol)
    except Exception as e:
        logger.error(f"❌ [接口] 获取美股财务数据失败: {e}", exc_info=True)
        return f"❌ 获取美股 {symbol} 财务数据失败: {e}"

def get_china_financial_indicators_unified(symbol: str) -> str:
    """
    统一的中国A股财务指标获取接口。
    """
    logger.info(f"📊 [统一接口] 开始获取A股财务指标 for {symbol}")
    try:
        provider = get_akshare_provider()
        financial_df = provider.get_china_financial_indicators(symbol)
        if financial_df is not None and not financial_df.empty:
            # 将DataFrame转换为更易于LLM阅读的格式
            return financial_df.to_string()
        else:
            return f"❌ 未能获取 {symbol} 的财务指标数据。"
    except Exception as e:
        logger.error(f"❌ [统一接口] 获取A股财务指标失败: {e}", exc_info=True)
        return f"❌ 获取 {symbol} 财务指标失败: {e}"

def get_akshare_stock_news_unified(symbol: str) -> str:
    """
    统一的股票新闻获取接口 (A股, 港股, 美股)。
    """
    logger.info(f"📰 [统一接口] 开始获取Akshare新闻 for {symbol}")
    try:
        provider = get_akshare_provider()
        news_df = provider.get_china_stock_news(symbol) # 底层函数名暂时不变
        if news_df is not None and not news_df.empty:
            # 筛选并格式化对LLM有用的列
            news_df_filtered = news_df[['新闻标题', '新闻内容', '发布时间', '文章来源']]
            return news_df_filtered.to_string()
        else:
            return f"❌ 未能获取 {symbol} 的新闻数据。"
    except Exception as e:
        logger.error(f"❌ [统一接口] 获取Akshare新闻失败: {e}", exc_info=True)
        return f"❌ 获取 {symbol} 新闻失败: {e}"
