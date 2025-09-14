# 导入仍然使用的模块
from .googlenews_utils import getNewsData
from .reddit_utils import fetch_top_from_category

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入核心的统一接口
from .interface import (
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    get_hk_stock_data_unified,
    get_hk_stock_info_unified,
)

__all__ = [
    "get_google_news",
    "get_reddit_global_news",
    "get_reddit_company_news",
    "get_china_stock_data_unified",
    "get_china_stock_info_unified",
    "get_hk_stock_data_unified",
    "get_hk_stock_info_unified",
]
