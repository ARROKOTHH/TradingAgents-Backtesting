from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
import json
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.dataflows.interface import get_china_stock_data_unified, get_china_stock_info_unified, get_china_financial_indicators_unified, get_akshare_stock_news_unified
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage

# 导入统一日志系统和工具日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_tool_call, log_analysis_step

# 导入A股技术指标工具
from tradingagents.tools.china_stock_indicator_tool import get_china_stock_indicators

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]
        
        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]
        
        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")
        
        return {"messages": removal_operations + [placeholder]}
    
    return delete_messages


class Toolkit:
    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    @staticmethod
    @tool
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """
        
        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    @tool
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    @tool
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company, e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    @tool
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        获取中国社交媒体和财经平台上关于特定股票的情绪分析和讨论热度。
        整合雪球、东方财富股吧、新浪财经等中国本土平台的数据。
        Args:
            ticker (str): 股票代码，如 AAPL, TSM
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含中国投资者情绪分析、讨论热度、关键观点的格式化报告
        """
        try:
            # 这里可以集成多个中国平台的数据
            chinese_sentiment_results = interface.get_chinese_social_sentiment(ticker, curr_date)
            return chinese_sentiment_results
        except Exception as e:
            # 如果中国平台数据获取失败，回退到原有的Reddit数据
            return interface.get_reddit_company_news(ticker, curr_date, 7, 5)

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None
    ) -> str:
        """
        统一的股票新闻获取工具
        使用akshare stock_news_em接口，可同时处理A股、港股、美股。

        Args:
            ticker: 股票代码（如：000001、00700.HK、AAPL）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 相关新闻列表
        """
        logger.info(f"📰 [统一新闻工具] 使用akshare获取新闻 for: {ticker}")
        try:
            # 直接调用统一接口，不再需要按市场进行判断
            return get_akshare_stock_news_unified(ticker)
        except Exception as e:
            error_msg = f"统一新闻工具执行失败: {str(e)}"
            logger.error(f"❌ [统一新闻工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None
    ) -> str:
        """
        统一的股票基本面分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的Akshare数据源。

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """
        logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")

            # 设置默认日期
            if not curr_date:
                curr_date = datetime.now().strftime('%Y-%m-%d')

            result_data = []

            if is_china:
                logger.info(f"🇨🇳 [统一基本面工具] 处理A股财务指标...")
                try:
                    china_fundamentals = get_china_financial_indicators_unified(ticker)
                    result_data.append(f"## A股财务指标\n{china_fundamentals}")
                except Exception as e:
                    result_data.append(f"## A股财务指标\n获取失败: {e}")

            elif is_hk:
                logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据...")
                # 港股逻辑待实现或调用相应接口
                result_data.append(f"## 港股基本面数据\n功能待实现")

            else: # is_us
                logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据 (Akshare)...")
                try:
                    from tradingagents.utils.stock_utils import StockUtils
                    standardized_ticker = StockUtils.standardize_us_symbol(ticker)
                    logger.info(f"🔧 [统一基本面工具] 美股代码标准化: {ticker} -> {standardized_ticker}")
                    
                    from tradingagents.dataflows.interface import get_us_fundamentals_akshare
                    us_financials = get_us_fundamentals_akshare(standardized_ticker, curr_date)
                    result_data.append(f"## 美股财务指标 (AkShare源)\n{us_financials}")
                except Exception as e:
                    result_data.append(f"## 美股财务指标 (AkShare源)\n获取失败: {e}")

            combined_result = f"# {ticker} 基本面分析数据\n\n{chr(10).join(result_data)}\n\n---"
            logger.info(f"📊 [统一基本面工具] 数据获取完成。")
            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一基本面工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"]
    ) -> str:
        """
        统一的股票市场数据工具
        自动识别股票类型（A股、港股、美股）并调用相应的Akshare数据源。

        Args:
            ticker: 股票代码（如：000001、0700.HK、105.AMD）
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）

        Returns:
            str: 市场数据和技术分析报告
        """
        logger.info(f"📈 [统一市场工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info['is_china']
            is_hk = market_info['is_hk']
            is_us = market_info['is_us']

            logger.info(f"📈 [统一市场工具] 股票类型: {market_info['market_name']}")
            result_data = []

            if is_china:
                logger.info(f"🇨🇳 [统一市场工具] 处理A股市场数据...")
                try:
                    china_data = get_china_stock_data_unified(ticker, start_date, end_date)
                    result_data.append(f"## A股市场数据\n{china_data}")
                    
                    # 获取并附加技术指标
                    try:
                        logger.info(f"📈 [统一市场工具] 计算A股技术指标...")
                        indicators = get_china_stock_indicators(ticker, end_date)
                        # 使用json.dumps美化输出，确保LLM能更好地解析
                        indicators_str = json.dumps(indicators, indent=2, ensure_ascii=False)
                        result_data.append(f"## A股技术指标\n```json\n{indicators_str}\n```")
                        logger.info(f"✅ [统一市场工具] 已成功附加技术指标ảng。")
                    except Exception as e:
                        logger.warning(f"⚠️ [统一市场工具] 计算技术指标失败: {e}")
                        result_data.append(f"## A股技术指标\n获取失败: {e}")

                except Exception as e:
                    result_data.append(f"## A股市场数据\n获取失败: {e}")

            elif is_hk:
                logger.info(f"🇭🇰 [统一市场工具] 处理港股市场数据...")
                # 港股逻辑待实现或调用相应接口
                result_data.append(f"## 港股市场数据\n功能待实现")

            else: # is_us
                logger.info(f"🇺🇸 [统一市场工具] 处理美股市场数据(AkShare)...")
                try:
                    from tradingagents.dataflows.interface import get_us_stock_data_akshare
                    us_data = get_us_stock_data_akshare(ticker, start_date, end_date)
                    result_data.append(f"## 美股市场数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股市场数据\n获取失败: {e}")

            combined_result = f"# {ticker} 市场数据分析\n\n{chr(10).join(result_data)}\n\n---"
            logger.info(f"📈 [统一市场工具] 数据获取完成。")
            return combined_result

        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            logger.error(f"❌ [统一市场工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_china_stock_indicators", log_args=True)
    def get_china_stock_indicators(
        symbol: Annotated[str, "A股股票代码"],
        date: Annotated[str, "日期，格式：YYYY-MM-DD"] = None
    ) -> dict:
        """
        获取A股的技术指标

        :param symbol: 股票代码
        :param date: 日期
        :return: 技术指标
        """
        return get_china_stock_indicators(symbol, date)
