#!/usr/bin/env python3
"""
股票数据预获取和验证模块 (已重构为仅使用AKShare)
"""

import re
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('stock_validator')


class StockDataPreparationResult:
    """股票数据预获取结果类"""

    def __init__(self, is_valid: bool, stock_code: str, market_type: str = "",
                 stock_name: str = "", error_message: str = "", suggestion: str = "",
                 has_historical_data: bool = False, has_basic_info: bool = False,
                 data_period_days: int = 0, cache_status: str = ""):
        self.is_valid = is_valid
        self.stock_code = stock_code
        self.market_type = market_type
        self.stock_name = stock_name
        self.error_message = error_message
        self.suggestion = suggestion
        self.has_historical_data = has_historical_data
        self.has_basic_info = has_basic_info
        self.data_period_days = data_period_days
        self.cache_status = cache_status

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'stock_name': self.stock_name,
            'error_message': self.error_message,
            'suggestion': self.suggestion,
            'has_historical_data': self.has_historical_data,
            'has_basic_info': self.has_basic_info,
            'data_period_days': self.data_period_days,
            'cache_status': self.cache_status
        }


class StockDataPreparer:
    """股票数据预获取和验证器"""

    def __init__(self, default_period_days: int = 30):
        self.default_period_days = default_period_days

    def prepare_stock_data(self, stock_code: str, market_type: str = "auto",
                          period_days: int = None, analysis_date: str = None) -> StockDataPreparationResult:
        """预获取和验证股票数据"""
        if period_days is None:
            period_days = self.default_period_days
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"📊 [数据准备] 开始准备股票数据: {stock_code} (市场: {market_type}, 时长: {period_days}天)")

        if market_type == "auto":
            market_type = self._detect_market_type(stock_code)

        try:
            from tradingagents.dataflows.akshare_utils import get_akshare_provider
            provider = get_akshare_provider()
            
            end_date = datetime.strptime(analysis_date, '%Y-%m-%d')
            start_date = end_date - timedelta(days=period_days)
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')

            stock_name = stock_code
            info_ok = False
            data_ok = False

            # 1. Get basic info
            info = provider.get_stock_info(stock_code)
            if info and info.get('name'):
                stock_name = info['name']
                info_ok = True

            # 2. Get historical data
            data = None
            if market_type == "A股":
                data = provider.get_stock_data(stock_code, start_date_str, end_date_str)
            elif market_type == "港股":
                data = provider.get_hk_stock_data(stock_code, start_date_str, end_date_str)
            elif market_type == "美股":
                data = provider.get_us_stock_data(stock_code, start_date_str, end_date_str)
            
            if data is not None and not data.empty:
                data_ok = True

            if info_ok and data_ok:
                logger.info(f"🎉 [数据准备] 数据准备完成: {stock_code} - {stock_name}")
                return StockDataPreparationResult(is_valid=True, stock_code=stock_code, market_type=market_type, stock_name=stock_name)
            else:
                error_msg = f"无法为 {stock_code} 获取到完整数据 (info: {info_ok}, data: {data_ok})"
                logger.error(f"❌ {error_msg}")
                return StockDataPreparationResult(is_valid=False, stock_code=stock_code, error_message=error_msg)

        except Exception as e:
            logger.error(f"❌ [数据准备] 数据准备异常: {e}", exc_info=True)
            return StockDataPreparationResult(is_valid=False, stock_code=stock_code, error_message=str(e))

    def _detect_market_type(self, stock_code: str) -> str:
        """自动检测市场类型"""
        stock_code = stock_code.strip().upper()
        if re.match(r'^\d{6}$', stock_code):
            return "A股"
        if re.match(r'^\d{4,5}(\.HK)?$', stock_code):
            return "港股"
        return "美股"

# 全局实例
_stock_preparer = None

def get_stock_preparer(default_period_days: int = 30) -> StockDataPreparer:
    global _stock_preparer
    if _stock_preparer is None:
        _stock_preparer = StockDataPreparer(default_period_days)
    return _stock_preparer

def prepare_stock_data(stock_code: str, market_type: str = "auto",
                      period_days: int = None, analysis_date: str = None) -> StockDataPreparationResult:
    preparer = get_stock_preparer()
    return preparer.prepare_stock_data(stock_code, market_type, period_days, analysis_date)