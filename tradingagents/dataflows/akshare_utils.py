#!/usr/bin/env python3
"""
AKShare数据源工具
提供AKShare数据获取的统一接口
"""

import pandas as pd
from typing import Optional, Dict, Any
import warnings
from datetime import datetime
import json
import os

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')
warnings.filterwarnings('ignore')

class AKShareProvider:
    """AKShare数据提供器"""

    def __init__(self):
        """初始化AKShare提供器"""
        try:
            import akshare as ak
            self.ak = ak
            self.connected = True
            self.us_symbol_map = {}  # Cache for US symbol mapping
            # Define cache path
            self.cache_dir = os.path.join(os.path.dirname(__file__), 'data_cache')
            os.makedirs(self.cache_dir, exist_ok=True)
            self.symbol_map_path = os.path.join(self.cache_dir, 'us_symbol_map.json')
            self._configure_timeout()
            logger.info(f"✅ AKShare初始化成功")
        except ImportError:
            self.ak = None
            self.connected = False
            logger.error(f"❌ AKShare未安装")

    def _configure_timeout(self):
        """配置AKShare的超时设置"""
        try:
            import requests
            import socket
            socket.setdefaulttimeout(60)
            if hasattr(requests, 'adapters'):
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session = requests.Session()
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                logger.info(f"🔧 AKShare超时配置完成: 60秒超时，3次重试")
        except Exception as e:
            logger.error(f"⚠️ AKShare超时配置失败: {e}")

    def _populate_us_symbol_map(self):
        """Populate the US symbol map from Akshare, with local JSON caching."""
        if self.us_symbol_map:
            return
        if os.path.exists(self.symbol_map_path):
            try:
                with open(self.symbol_map_path, 'r', encoding='utf-8') as f:
                    self.us_symbol_map = json.load(f)
                logger.info(f"✅ 从缓存文件加载美股代码映射表: {self.symbol_map_path}")
                if self.us_symbol_map:
                    return
            except Exception as e:
                logger.warning(f"⚠️ 加载美股代码映射表缓存失败: {e}")
        try:
            logger.info("🔄 正在从网络初始化美股代码映射表...")
            us_spot = self.ak.stock_us_spot_em()
            self.us_symbol_map = {row['代码'].split('.')[-1]: row['代码'] for _, row in us_spot.iterrows() if '.' in row['代码']}
            with open(self.symbol_map_path, 'w', encoding='utf-8') as f:
                json.dump(self.us_symbol_map, f, ensure_ascii=False, indent=4)
            logger.info(f"✅ 美股代码映射表初始化完成并已缓存至 {self.symbol_map_path}")
        except Exception as e:
            logger.error(f"❌ 初始化美股代码映射表失败: {e}")

    def _convert_to_us_hist_symbol(self, symbol: str) -> Optional[str]:
        """Convert a plain US symbol (e.g., AMD) to its prefixed history symbol (e.g., 105.AMD)."""
        self._populate_us_symbol_map()
        plain_symbol = symbol.upper().split('.')[-1]
        return self.us_symbol_map.get(plain_symbol)
    
    def get_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """获取A股历史数据"""
        if not self.connected: return None
        try:
            symbol = symbol.replace('.SZ', '').replace('.SS', '')
            return self.ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''), adjust="")
        except Exception as e:
            logger.error(f"❌ AKShare获取A股数据失败: {e}")
            return None
    
    def get_us_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """获取美股历史数据"""
        if not self.connected: return None
        try:
            hist_symbol = self._convert_to_us_hist_symbol(symbol)
            if not hist_symbol:
                logger.error(f"❌ 无法找到 {symbol} 对应的美股行情代码。")
                return None
            logger.info(f"🔄 转换美股代码 {symbol} -> {hist_symbol} 用于获取历史数据。")
            data = self.ak.stock_us_hist(symbol=hist_symbol, period="daily", start_date=start_date.replace('-', ''), end_date=end_date.replace('-', ''), adjust="")
            if data is None:
                logger.warning(f"⚠️ AKShare为美股 {hist_symbol} 返回了None")
            return data
        except Exception as e:
            logger.error(f"❌ AKShare获取美股数据失败: {e}", exc_info=True)
            return None

    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        if not self.connected: return {}
        try:
            stock_list = self.ak.stock_info_a_code_name()
            stock_info = stock_list[stock_list['code'] == symbol]
            if not stock_info.empty:
                return {'symbol': symbol, 'name': stock_info.iloc[0]['name'], 'source': 'akshare'}
            else:
                return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'akshare'}
        except Exception as e:
            logger.error(f"❌ AKShare获取股票信息失败: {e}")
            return {'symbol': symbol, 'name': f'股票{symbol}', 'source': 'akshare'}

    def get_hk_stock_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """获取港股历史数据"""
        if not self.connected: return None
        try:
            hk_symbol = self._normalize_hk_symbol_for_akshare(symbol)
            logger.info(f"🇭🇰 AKShare获取港股数据: {hk_symbol} ({start_date} 到 {end_date})")
            start_date_formatted = start_date.replace('-', '') if start_date else "20240101"
            end_date_formatted = end_date.replace('-', '') if end_date else "20241231"
            data = self.ak.stock_hk_hist(symbol=hk_symbol, period="daily", start_date=start_date_formatted, end_date=end_date_formatted, adjust="")
            if data is not None and not data.empty:
                data = data.reset_index()
                data['Symbol'] = symbol
                column_mapping = {'日期': 'Date', '开盘': 'Open', '收盘': 'Close', '最高': 'High', '最低': 'Low', '成交量': 'Volume', '成交额': 'Amount'}
                data.rename(columns={k: v for k, v in column_mapping.items() if k in data.columns}, inplace=True)
                logger.info(f"✅ AKShare港股数据获取成功: {symbol}, {len(data)}条记录")
                return data
            else:
                logger.warning(f"⚠️ AKShare港股数据为空: {symbol}")
                return None
        except Exception as e:
            logger.error(f"❌ AKShare获取港股数据失败: {e}")
            return None

    def get_hk_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取港股基本信息"""
        if not self.connected: return {'symbol': symbol, 'name': f'港股{symbol}', 'source': 'akshare_unavailable'}
        try:
            hk_symbol = self._normalize_hk_symbol_for_akshare(symbol)
            logger.info(f"🇭🇰 AKShare获取港股信息: {hk_symbol}")
            spot_data = self.ak.stock_hk_spot_em()
            if not spot_data.empty:
                matching_stocks = spot_data[spot_data['代码'].str.contains(hk_symbol[:5], na=False)]
                if not matching_stocks.empty:
                    stock_info = matching_stocks.iloc[0]
                    return {'symbol': symbol, 'name': stock_info.get('名称', f'港股{symbol}'), 'source': 'akshare'}
            return {'symbol': symbol, 'name': f'港股{symbol}', 'source': 'akshare'}
        except Exception as e:
            logger.error(f"❌ AKShare获取港股信息失败: {e}")
            return {'symbol': symbol, 'name': f'港股{symbol}', 'source': 'akshare_error', 'error': str(e)}

    def _normalize_hk_symbol_for_akshare(self, symbol: str) -> str:
        """标准化港股代码为AKShare格式"""
        clean_symbol = symbol.replace('.HK', '').replace('.hk', '')
        return clean_symbol.zfill(5) if clean_symbol.isdigit() else clean_symbol

    def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取A股财务数据"""
        if not self.connected: return {}
        try:
            logger.info(f"🔍 开始获取{symbol}的AKShare财务数据")
            financial_data = {}
            main_indicators = self.ak.stock_financial_abstract(symbol=symbol)
            if main_indicators is not None and not main_indicators.empty:
                financial_data['main_indicators'] = main_indicators
            lg_indicators = self.ak.stock_a_lg_indicator(symbol=symbol)
            if lg_indicators is not None and not lg_indicators.empty:
                financial_data['lg_indicators'] = lg_indicators
            balance_sheet = self.ak.stock_balance_sheet_by_report_em(symbol=symbol)
            if balance_sheet is not None and not balance_sheet.empty:
                financial_data['balance_sheet'] = balance_sheet
            return financial_data
        except Exception as e:
            logger.error(f"❌ AKShare获取{symbol}财务数据失败: {e}")
            return {}

    def get_us_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取美股财务数据"""
        if not self.connected: return {}
        try:
            financial_symbol = symbol.upper().split('.')[-1]
            logger.info(f"🔍 开始获取{financial_symbol} (美股)的AKShare财务数据")
            financial_data = {}
            indicators = self.ak.stock_financial_us_analysis_indicator_em(symbol=financial_symbol)
            if indicators is not None and not indicators.empty:
                financial_data['main_indicators'] = indicators
            balance_sheet = self.ak.stock_financial_us_report_em(stock=financial_symbol, symbol="资产负债表")
            if balance_sheet is not None and not balance_sheet.empty:
                financial_data['balance_sheet'] = balance_sheet
            return financial_data
        except Exception as e:
            logger.error(f"❌ AKShare获取{symbol}美股财务数据失败: {e}")
            return {}

    def get_hk_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取港股财务数据"""
        if not self.connected: return {}
        try:
            financial_symbol = self._normalize_hk_symbol_for_akshare(symbol)
            logger.info(f"🔍 开始获取{financial_symbol} (港股)的AKShare财务数据")
            financial_data = {}
            indicators = self.ak.stock_financial_hk_analysis_indicator_em(symbol=financial_symbol)
            if indicators is not None and not indicators.empty:
                financial_data['main_indicators'] = indicators
            return financial_data
        except Exception as e:
            logger.error(f"❌ AKShare获取{symbol}港股财务数据失败: {e}")
            return {}

    def _get_china_valuation_indicators(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取A股的实时估值指标，如PE, PB, 总市值等"""
        if not self.connected: return None
        try:
            logger.info(f"🔍 开始获取 {symbol} 的A股实时估值指标...")
            # 获取所有A股的实时行情数据
            spot_df = self.ak.stock_zh_a_spot_em()
            if spot_df is None or spot_df.empty:
                logger.warning(f"⚠️ AKShare未能获取A股实时行情数据。")
                return None
            
            # 筛选出目标股票
            stock_valuation = spot_df[spot_df['代码'] == symbol]
            
            if stock_valuation.empty:
                logger.warning(f"⚠️ 在A股实时行情中未找到 {symbol} 的估值数据。")
                return None

            # 提取并重命名关键估值指标
            valuation_metrics = stock_valuation[[
                '市盈率-动态', '市净率', '总市值', '流通市值'
            ]].copy()
            valuation_metrics.rename(columns={
                '市盈率-动态': 'PE(动态)',
                '市净率': 'PB',
                '总市值': '总市值(元)',
                '流通市值': '流通市值(元)'
            }, inplace=True)
            
            logger.info(f"✅ 成功获取 {symbol} 的估值指标。")
            return valuation_metrics

        except Exception as e:
            logger.error(f"❌ AKShare获取 {symbol} 估值指标数据失败: {e}")
            return None

    def get_china_financial_indicators(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取A股核心财务指标和估值指标"""
        if not self.connected: return None
        try:
            logger.info(f"🔍 开始获取 {symbol} 的A股核心财务与估值指标 (从2024年开始)...")
            
            # 1. 获取财务分析指标
            financial_df = self.ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2024")
            if financial_df is None or financial_df.empty:
                logger.warning(f"⚠️ AKShare未能获取 {symbol} 的财务分析指标数据。")
                # 即使财务指标失败，我们仍然尝试获取估值指标
                return self._get_china_valuation_indicators(symbol)

            # 2. 获取估值指标
            valuation_df = self._get_china_valuation_indicators(symbol)

            # 3. 合并数据
            if valuation_df is not None and not valuation_df.empty:
                logger.info(f"🔄 正在合并 {symbol} 的财务指标和估值指标...")
                # 重置估值df的索引，以便与财务df的每一行进行合并
                valuation_values = valuation_df.iloc[0].to_dict()
                
                # 将估值指标的单个值赋给财务指标df的每一行
                for col, value in valuation_values.items():
                    financial_df[col] = value
                
                logger.info(f"✅ 成功合并指标。")

            logger.info(f"✅ 成功获取 {symbol} 的财务与估值综合指标。")
            return financial_df
            
        except Exception as e:
            logger.error(f"❌ AKShare获取 {symbol} 综合指标数据失败: {e}")
            return None

    def get_china_stock_news(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取A股新闻数据"""
        if not self.connected: return None
        try:
            logger.info(f"🔍 使用akshare获取 {symbol} 的新闻...")
            news_df = self.ak.stock_news_em(symbol=symbol)
            if news_df is None or news_df.empty:
                logger.warning(f"⚠️ Akshare未能获取 {symbol} 的新闻。")
                return None
            logger.info(f"✅ 成功获取 {symbol} 的新闻数据。")
            return news_df
        except Exception as e:
            logger.error(f"❌ AKShare获取 {symbol} 新闻数据失败: {e}")
            return None

# 全局单例
_akshare_provider_instance = None

def get_akshare_provider() -> AKShareProvider:
    """获取AKShareProvider的单例实例"""
    global _akshare_provider_instance
    if _akshare_provider_instance is None:
        logger.info("🔧 [单例模式] 初始化全局AKShareProvider实例...")
        _akshare_provider_instance = AKShareProvider()
    return _akshare_provider_instance

# ... (rest of the file remains the same)