#!/usr/bin/env python3
"""
统一新闻分析工具
整合A股、港股、美股等不同市场的新闻获取逻辑到一个工具函数中
让大模型只需要调用一个工具就能获取所有类型股票的新闻数据
"""

import logging
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class UnifiedNewsAnalyzer:
    """统一新闻分析器，整合所有新闻获取逻辑"""

    def __init__(self, toolkit):
        """初始化统一新闻分析器
        
        Args:
            toolkit: 包含各种新闻获取工具的工具包
        """
        self.toolkit = toolkit

    def get_stock_news_unified(self, stock_code: str, max_news: int = 10, model_info: str = "") -> str:
        """
        统一新闻获取接口
        根据股票代码自动识别股票类型并获取相应新闻
        
        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            model_info: 当前使用的模型信息，用于特殊处理
            
        Returns:
            str: 格式化的新闻内容
        """
        logger.info(f"[统一新闻工具] 开始为 {stock_code} 获取新闻...")
        
        stock_type = self._identify_stock_type(stock_code)
        logger.info(f"[统一新闻工具] 识别股票类型为: {stock_type}")

        # 统一调用新的获取逻辑
        result = self._get_news_with_fallback(stock_code, stock_type, model_info)
        
        logger.info(f"[统一新闻工具] 📊 新闻获取完成，结果长度: {len(result)} 字符")
        
        # 如果结果为空或表示失败，记录警告
        if not result or "❌" in result:
            logger.warning(f"[统一新闻工具] ⚠️ 返回结果为空或包含错误信息。")
            logger.warning(f"[统一新闻工具] 📝 完整结果内容: '{result}'")
        
        return result

    def _get_news_with_fallback(self, stock_code: str, stock_type: str, model_info: str) -> str:
        """
        统一的新闻获取逻辑，实现Akshare优先，Google News备用。
        """
        curr_date = datetime.now().strftime("%Y-%m-%d")
        # Local import to avoid circular dependencies at module level
        from tradingagents.dataflows.interface import get_akshare_stock_news_unified, get_google_news

        # 1. 优先使用Akshare
        try:
            logger.info(f"↳ [主数据源] 尝试从Akshare为 {stock_code} 获取新闻...")
            akshare_news = get_akshare_stock_news_unified(stock_code)
            
            if akshare_news and "❌" not in akshare_news and "未能获取" not in akshare_news:
                logger.info(f"✅ [主数据源] Akshare成功返回新闻。")
                return self._format_news_result(akshare_news, "Akshare", model_info)
            else:
                logger.warning(f"⚠️ [主数据源] Akshare未能返回有效新闻，将尝试备用数据源。")

        except Exception as e:
            logger.error(f"❌ [主数据源] Akshare在获取新闻时发生异常: {e}，将尝试备用数据源。")

        # 2. Akshare失败或无数据，回退到Google News
        try:
            logger.info(f"↳ [备用数据源] 尝试从Google News为 {stock_code} 获取新闻...")
            
            if stock_type == "A股":
                query = f"{stock_code} 股票 新闻 财报 业绩"
            elif stock_type == "港股":
                query = f"{stock_code} 港股 香港股票 新闻"
            elif stock_type == "美股":
                query = f"{stock_code} stock news earnings financial"
            else:
                query = f"{stock_code} 新闻"

            logger.info(f"↳ [备用数据源] 使用查询词 '{query}' 在Google News中搜索。")
            google_news = get_google_news(query, curr_date, 7)
            
            if google_news and "未找到相关新闻" not in google_news:
                logger.info(f"✅ [备用数据源] Google News成功返回新闻。")
                return self._format_news_result(google_news, "Google News (备用)", model_info)
            else:
                logger.error(f"❌ [备用数据源] Google News也未能找到相关新闻。")
                return f"❌ 无法获取 {stock_code} 的新闻，所有新闻源均不可用"

        except Exception as e:
            error_msg = f"❌ [备用数据源] Google News在获取新闻时发生异常: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def _identify_stock_type(self, stock_code: str) -> str:
        """识别股票类型"""
        stock_code = stock_code.upper().strip()
        if re.match(r'^(00|30|60|68)\d{4}$', stock_code): return "A股"
        if re.match(r'^(SZ|SH)\d{6}$', stock_code): return "A股"
        if re.match(r'^\d{4,5}\.HK$', stock_code): return "港股"
        if re.match(r'^\d{4,5}$', stock_code) and len(stock_code) <= 5: return "港股"
        if re.match(r'^[A-Z]{1,5}$', stock_code): return "美股"
        if '.' in stock_code and not stock_code.endswith('.HK'): return "美股"
        return "A股"
    
    def _format_news_result(self, news_content: str, source: str, model_info: str = "") -> str:
        """格式化新闻结果"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Simplified formatter
        formatted_result = f"""
=== 📰 新闻数据来源: {source} ===
获取时间: {timestamp}

{news_content}
"""
        return formatted_result.strip()


def create_unified_news_tool(toolkit):
    """创建统一新闻工具函数"""
    analyzer = UnifiedNewsAnalyzer(toolkit)
    
    def get_stock_news_unified(stock_code: str, max_news: int = 100, model_info: str = ""):
        """
        统一新闻获取工具
        
        Args:
            stock_code (str): 股票代码 (支持A股如000001、港股如0700.HK、美股如AAPL)
            max_news (int): 最大新闻数量，默认100
            model_info (str): 当前使用的模型信息，用于特殊处理
        
        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return "❌ 错误: 未提供股票代码"
        
        return analyzer.get_stock_news_unified(stock_code, max_news, model_info)
    
    # 设置工具属性
    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 - 根据股票代码自动获取相应市场的新闻

功能:
- 自动识别股票类型（A股/港股/美股）
- 优先使用 Akshare 作为主要新闻来源
- 如果 Akshare 获取失败或无数据，则自动使用 Google News 作为备用新闻来源
- 返回格式化的新闻内容
"""
    
    return get_stock_news_unified
