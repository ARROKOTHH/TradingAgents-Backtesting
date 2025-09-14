#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
市场分析师代理模块
负责技术分析和市场数据获取
"""

import functools
import time
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableLambda

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('agents')

# 导入工具类
from tradingagents.agents.utils.agent_utils import Toolkit
from tradingagents.agents.utils.agent_states import AgentState

# 导入股票工具类
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.tools.china_stock_indicator_tool import get_china_stock_indicators


def _get_company_name(ticker: str) -> str:
    """
    根据股票代码获取公司名称
    
    Args:
        ticker: 股票代码
        
    Returns:
        str: 公司名称
    """
    try:
        # 获取市场信息
        market_info = StockUtils.get_market_info(ticker)
        
        if market_info['is_china']:
            # 中国A股：使用统一接口获取股票信息
            from tradingagents.dataflows.interface import get_china_stock_info_unified
            stock_info = get_china_stock_info_unified(ticker)
            
            # 解析股票名称
            if "股票名称:" in stock_info:
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
                logger.debug(f"📊 [DEBUG] 从统一接口获取中国股票名称: {ticker} -> {company_name}")
                return company_name
            else:
                logger.warning(f"⚠️ [DEBUG] 无法从统一接口解析股票名称: {ticker}")
                return f"股票代码{ticker}"
                
        elif market_info['is_hk']:
            # 港股：使用改进的港股工具
            try:
                from tradingagents.dataflows.improved_hk_utils import get_hk_company_name_improved
                company_name = get_hk_company_name_improved(ticker)
                logger.debug(f"📊 [DEBUG] 使用改进港股工具获取名称: {ticker} -> {company_name}")
                return company_name
            except Exception as e:
                logger.debug(f"📊 [DEBUG] 改进港股工具获取名称失败: {e}")
                # 降级方案：生成友好的默认名称
                clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
                return f"港股{clean_ticker}"
                
        elif market_info['is_us']:
            # 美股：使用简单映射或返回代码
            us_stock_names = {
                'AAPL': '苹果公司',
                'TSLA': '特斯拉',
                'NVDA': '英伟达',
                'MSFT': '微软',
                'GOOGL': '谷歌',
                'AMZN': '亚马逊',
                'META': 'Meta',
                'NFLX': '奈飞'
            }
            
            company_name = us_stock_names.get(ticker.upper(), f"美股{ticker}")
            logger.debug(f"📊 [DEBUG] 美股名称映射: {ticker} -> {company_name}")
            return company_name
            
        else:
            return f"股票{ticker}"
            
    except Exception as e:
        logger.error(f"❌ [DEBUG] 获取公司名称失败: {e}")
        return f"股票{ticker}"


def create_market_analyst_react(llm, toolkit):
    """使用ReAct Agent模式的市场分析师（适用于通义千问）"""
    
    @functools.wraps(create_market_analyst_react)
    def market_analyst_react_node(state):
        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点开始 =====")
        
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(f"📈 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}")
        logger.debug(f"📈 [DEBUG] 现有市场报告: {state.get('market_report', 'None')}")
        
        # 检查是否为中国股票
        def is_china_stock(ticker_code):
            import re
            return re.match(r'^\d{6}$', str(ticker_code))
        
        is_china = is_china_stock(ticker)
        logger.debug(f"📈 [DEBUG] 股票类型检查: {ticker} -> 中国A股: {is_china}")
        
        if toolkit.config["online_tools"]:
            # 在线模式，使用ReAct Agent
            if is_china:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析中国股票")
                
                # 创建中国股票数据工具
                from langchain_core.tools import BaseTool
                
                class ChinaStockDataTool(BaseTool):
                    name: str = "get_china_stock_data"
                    description: str = f"获取中国A股股票{ticker}的市场数据和技术指标（优化缓存版本）。直接调用，无需参数。"
                    
                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(f"📈 [DEBUG] ChinaStockDataTool调用，股票代码: {ticker}")
                            # 使用优化的缓存数据获取
                            from tradingagents.dataflows.optimized_china_data import get_china_stock_data_cached
                            return get_china_stock_data_cached(
                                symbol=ticker,
                                start_date='2025-05-28',
                                end_date=current_date,
                                force_refresh=False
                            )
                        except Exception as e:
                            logger.error(f"❌ 优化A股数据获取失败: {e}")
                            # 备用方案：使用原始API
                            try:
                                return toolkit.get_china_stock_data.invoke({
                                    'stock_code': ticker,
                                    'start_date': '2025-05-28',
                                    'end_date': current_date
                                })
                            except Exception as e2:
                                return f"获取股票数据失败: {str(e2)}"
                
                tools = [ChinaStockDataTool()]
                query = f"""请对中国A股股票{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_china_stock_data工具获取股票市场数据
2. 基于获取的真实数据进行深入的技术指标分析
3. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析

报告格式应包含：
## 股票基本信息
## 技术指标分析
## 价格趋势分析
## 市场情绪分析
## 投资建议"""
            else:
                logger.info(f"📈 [市场分析师] 使用ReAct Agent分析美股/港股")
                
                # 创建美股数据工具
                from langchain_core.tools import BaseTool
                
                class USStockDataTool(BaseTool):
                    name: str = "get_us_stock_data"
                    description: str = f"获取美股/港股{ticker}的市场数据和技术指标（优化缓存版本）。直接调用，无需参数。"
                    
                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(f"📈 [DEBUG] USStockDataTool调用，股票代码: {ticker}")
                            # 使用优化的缓存数据获取
                            from tradingagents.dataflows.optimized_us_data import get_us_stock_data_cached
                            return get_us_stock_data_cached(
                                symbol=ticker,
                                start_date='2025-05-28',
                                end_date=current_date,
                                force_refresh=False
                            )
                        except Exception as e:
                            logger.error(f"❌ 优化美股数据获取失败: {e}")
                            # 备用方案：使用原始API
                            try:
                                return toolkit.get_YFin_data.invoke({
                                    'symbol': ticker,
                                    'start_date': '2025-05-28',
                                    'end_date': current_date
                                })
                            except Exception as e2:
                                return f"获取股票数据失败: {str(e2)}"
                
                class FinnhubNewsTool(BaseTool):
                    name: str = "get_finnhub_news"
                    description: str = f"获取美股{ticker}的最新新闻和市场情绪（通过FINNHUB API）。直接调用，无需参数。"
                    
                    def _run(self, query: str = "") -> str:
                        try:
                            logger.debug(f"📈 [DEBUG] FinnhubNewsTool调用，股票代码: {ticker}")
                            return toolkit.get_finnhub_news.invoke({
                                'ticker': ticker,
                                'start_date': '2025-06-01',
                                'end_date': current_date
                            })
                        except Exception as e:
                            return f"获取新闻数据失败: {str(e)}"
                
                tools = [USStockDataTool(), FinnhubNewsTool()]
                query = f"""请对美股{ticker}进行详细的技术分析。

执行步骤：
1. 使用get_us_stock_data工具获取股票市场数据和技术指标（通过FINNHUB API）
2. 使用get_finnhub_news工具获取最新新闻和市场情绪
3. 基于获取的真实数据进行深入的技术指标分析
4. 直接输出完整的技术分析报告内容

重要要求：
- 必须输出完整的技术分析报告内容，不要只是描述报告已完成
- 报告必须基于工具获取的真实数据进行分析
- 报告长度不少于800字
- 包含具体的数据、指标数值和专业分析
- 结合新闻信息分析市场情绪

报告格式应包含：
## 股票基本信息
## 技术指标分析
## 价格趋势分析
## 成交量分析
## 新闻和市场情绪分析
## 投资建议"""
            
            try:
                # 创建ReAct Agent
                from langchain import hub
                from langchain.agents import create_react_agent, AgentExecutor
                
                prompt = hub.pull("hwchase17/react")
                agent = create_react_agent(llm, tools, prompt)
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True,
                    max_iterations=10,  # 增加到10次迭代，确保有足够时间完成分析
                    max_execution_time=180  # 增加到3分钟，给更多时间生成详细报告
                )
                
                logger.debug(f"📈 [DEBUG] 执行ReAct Agent查询...")
                result = agent_executor.invoke({'input': query})
                
                report = result['output']
                logger.info(f"📈 [市场分析师] ReAct Agent完成，报告长度: {len(report)}")
                
            except Exception as e:
                logger.error(f"❌ [DEBUG] ReAct Agent失败: {str(e)}")
                report = f"ReAct Agent市场分析失败: {str(e)}"
        else:
            # 离线模式，使用原有逻辑
            report = "离线模式，暂不支持"
        
        logger.debug(f"📈 [DEBUG] ===== ReAct市场分析师节点结束 =====")
        
        return {
            "messages": [("assistant", report)],
            "market_report": report,
        }
    
    return market_analyst_react_node


def create_market_analyst(llm, toolkit):
    """创建市场分析师节点"""
    
    def market_analyst_node(state):
        logger.debug(f"📈 [DEBUG] ===== 市场分析师节点开始 =====")
        
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(f"📈 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}")
        logger.debug(f"📈 [DEBUG] 现有市场报告: {state.get('market_report', 'None')}")
        
        # 根据股票代码格式选择数据源
        market_info = StockUtils.get_market_info(ticker)
        
        logger.debug(f"📈 [DEBUG] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})")
        
        # 获取公司名称
        company_name = _get_company_name(ticker)
        logger.debug(f"📈 [DEBUG] 公司名称: {ticker} -> {company_name}")
        
        if toolkit.config["online_tools"]:
            # 使用统一的市场数据工具，工具内部会自动识别股票类型
            logger.info(f"📊 [市场分析师] 使用统一市场数据工具，自动识别股票类型")
            # 如果是中国A股，添加技术指标工具
            if market_info.get('is_china', False):
                tools = [toolkit.get_stock_market_data_unified, toolkit.get_china_stock_indicators]
            else:
                tools = [toolkit.get_stock_market_data_unified]
            # 安全地获取工具名称用于调试
            tool_names_debug = []
            for tool in tools:
                if hasattr(tool, 'name'):
                    tool_names_debug.append(tool.name)
                elif hasattr(tool, '__name__'):
                    tool_names_debug.append(tool.__name__)
                else:
                    tool_names_debug.append(str(tool))
            logger.debug(f"📊 [DEBUG] 选择的工具: {tool_names_debug}")
            logger.debug(f"📊 [DEBUG] 🔧 统一工具将自动处理: {market_info['market_name']}")
        else:
            tools = [
                toolkit.get_YFin_data,
                toolkit.get_stockstats_indicators_report,
            ]
        
        # 如果是中国A股，则获取技术指标
        technical_indicators_summary = ""
        if market_info.get('is_china', False):
            logger.info(f"📊 [市场分析师] 正在为A股 {ticker} 获取技术指标...")
            indicators = get_china_stock_indicators(ticker)
            if indicators:
                technical_indicators_summary = f'''
====================================================
【重要】以下是我们预先为您计算的技术指标数据：
====================================================

【基本信息】
  股票代码: {ticker}
  数据日期: {indicators.get('date', 'N/A')}
  最新收盘价: {indicators.get('close', 'N/A')}

【MACD指标】
  MACD值: {indicators.get('MACD', {}).get('MACD', 'N/A')}
  信号线: {indicators.get('MACD', {}).get('MACD_signal', 'N/A')}
  柱状图: {indicators.get('MACD', {}).get('MACD_hist', 'N/A')}

【RSI指标】
  RSI(6): {indicators.get('RSI', {}).get('RSI_6', 'N/A')}
  RSI(12): {indicators.get('RSI', {}).get('RSI_12', 'N/A')}

【KDJ指标】
  K值: {indicators.get('KDJ', {}).get('K', 'N/A')}
  D值: {indicators.get('KDJ', {}).get('D', 'N/A')}
  J值: {indicators.get('KDJ', {}).get('J', 'N/A')}

【DMA指标】
  DMA: {indicators.get('DMA', {}).get('DMA', 'N/A')}
  AMA: {indicators.get('DMA', {}).get('AMA', 'N/A')}

【TRIX指标】
  TRIX: {indicators.get('TRIX', {}).get('TRIX', 'N/A')}
  MATRIX: {indicators.get('TRIX', {}).get('MATRIX', 'N/A')}

====================================================
请务必在您的技术分析中使用以上真实数据，不要再说无法计算技术指标！

此外，您还有一个名为get_china_stock_indicators的工具，必须在分析时调用以获取最新的技术指标数据。
====================================================
'''
            else:
                logger.warning(f"⚠️ [市场分析师] 未能获取 {ticker} 的技术指标。")
                technical_indicators_summary = """注意：未能预先计算技术指标，请依赖工具获取数据进行分析。"""

        # 统一的系统提示，适用于所有股票类型
        system_message = (
            f"""你是一位专业的股票技术分析师。你必须对{company_name}（股票代码：{ticker}）进行详细的技术分析。

{technical_indicators_summary}
**股票信息：**
- 公司名称：{company_name}
- 股票代码：{ticker}
- 所属市场：{market_info['market_name']}
- 计价货币：{market_info['currency_name']}（{market_info['currency_symbol']}）

**工具调用指令：**
你有一个工具叫做get_stock_market_data_unified，你必须立即调用这个工具来获取{company_name}（{ticker}）的市场数据。
如果是中国A股，你还有一个工具叫做get_china_stock_indicators，必须调用这个工具来获取详细的技术指标数据。
不要说你将要调用工具，直接调用工具。

**分析要求：**
1. 必须首先参考并使用上面提供的技术指标数据进行分析
2. 基于这些真实的技术指标数据进行专业的技术分析
3. 不要再说无法计算技术指标，因为这些指标已经提供给你了
4. 分析移动平均线、MACD、RSI、布林带等技术指标
5. 考虑{market_info['market_name']}市场特点进行分析
6. 提供具体的数值和专业分析
7. 给出明确的投资建议
8. 所有价格数据使用{market_info['currency_name']}（{market_info['currency_symbol']}）表示

**输出格式：**
## 📊 股票基本信息
- 公司名称：{company_name}
- 股票代码：{ticker}
- 所属市场：{market_info['market_name']}

## 📈 技术指标分析
## 📉 价格趋势分析
## 💭 投资建议

请使用中文，基于真实数据进行分析。确保在分析中正确使用公司名称"{company_name}"和股票代码"{ticker}"."""
        )
        
        # 创建提示词模板
        prompt_messages = [
            ("system", 
             "你是一位专业的股票技术分析师，与其他分析师协作。\n"
             "使用提供的工具来获取和分析股票数据。\n"
             "如果你无法完全回答，没关系；其他分析师会从不同角度继续分析。\n"
             "执行你能做的技术分析工作来取得进展。\n"
             "如果你有明确的技术面投资建议：**买入/持有/卖出**，\n"
             "请在你的回复中明确标注，但不要使用'最终交易建议'前缀，因为最终决策需要综合所有分析师的意见。\n"
             "你可以使用以下工具：{tool_names}。\n\n"
             "{system_message}\n"
             "供你参考，当前日期是{current_date}。\n"
             "我们要分析的是{company_name}（股票代码：{ticker}）。\n"
             "请确保所有分析都使用中文，并在分析中正确区分公司名称和股票代码。"),
            MessagesPlaceholder(variable_name="messages"),
        ]
        
        market_analyst_prompt_template = ChatPromptTemplate.from_messages(prompt_messages)
        
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        
        # 正确地填充模板参数
        market_analyst_prompt_template = market_analyst_prompt_template.partial(
            tool_names=", ".join(tool_names),
            current_date=current_date,
            ticker=ticker,
            company_name=company_name,
            system_message=system_message
        )
        
        chain = market_analyst_prompt_template | llm.bind_tools(tools)
        
        result = chain.invoke(state["messages"])
        
        # 处理市场分析报告
        if len(result.tool_calls) == 0:
            # 没有工具调用，直接使用LLM的回复
            report = result.content
            logger.info(f"📊 [市场分析师] 直接回复，长度: {len(report)}")
        else:
            # 有工具调用，执行工具并生成完整分析报告
            logger.info(f"📊 [市场分析师] 工具调用: {[call.get('name', 'unknown') for call in result.tool_calls]}")
            
            try:
                # 执行工具调用
                from langchain_core.messages import ToolMessage, HumanMessage
                
                tool_messages = []
                for tool_call in result.tool_calls:
                    tool_name = tool_call.get('name')
                    tool_args = tool_call.get('args', {})
                    tool_id = tool_call.get('id')
                    
                    logger.debug(f"📊 [DEBUG] 执行工具: {tool_name}, 参数: {tool_args}")
                    
                    # 找到对应的工具并执行
                    tool_result = None
                    for tool in tools:
                        # 安全地获取工具名称进行比较
                        current_tool_name = None
                        if hasattr(tool, 'name'):
                            current_tool_name = tool.name
                        elif hasattr(tool, '__name__'):
                            current_tool_name = tool.__name__
                        
                        if current_tool_name == tool_name:
                            try:
                                if tool_name == "get_china_stock_data":
                                    # 中国股票数据工具
                                    tool_result = tool.invoke(tool_args)
                                else:
                                    # 其他工具
                                    tool_result = tool.invoke(tool_args)
                                logger.debug(f"📊 [DEBUG] 工具执行成功，结果长度: {len(str(tool_result))}")
                                break
                            except Exception as tool_error:
                                logger.error(f"❌ [DEBUG] 工具执行失败: {tool_error}")
                                tool_result = f"工具执行失败: {str(tool_error)}"
                    
                    if tool_result is None:
                        tool_result = f"未找到工具: {tool_name}"
                    
                    # 创建工具消息
                    tool_message = ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_id
                    )
                    tool_messages.append(tool_message)
                
                # 基于工具结果生成完整分析报告
                analysis_prompt = f"""现在请基于上述工具获取的数据，生成详细的技术分析报告。

要求：
1. 报告必须基于工具返回的真实数据进行分析
2. 包含具体的技术指标数值和专业分析
3. 提供明确的投资建议和风险提示
4. 报告长度不少于800字
5. 使用中文撰写

请分析股票{ticker}的技术面情况，包括：
- 价格趋势分析
- 技术指标解读
- 支撑阻力位分析
- 成交量分析
- 投资建议"""
                
                # 构建完整的消息序列
                messages = state["messages"] + [result] + tool_messages + [HumanMessage(content=analysis_prompt)]
                
                # 生成最终分析报告
                final_result = llm.invoke(messages)
                report = final_result.content
                
                logger.info(f"📊 [市场分析师] 生成完整分析报告，长度: {len(report)}")
                
                # 返回包含工具调用和最终分析的完整消息序列
                return {
                    "messages": [result] + tool_messages + [final_result],
                    "market_report": report,
                }
                
            except Exception as e:
                logger.error(f"❌ [市场分析师] 工具执行或分析生成失败: {e}")
                import traceback
                traceback.print_exc()
                
                # 降级处理：返回工具调用信息
                report = f"市场分析师调用了工具但分析生成失败: {[call.get('name', 'unknown') for call in result.tool_calls]}"
                
                return {
                    "messages": [result],
                    "market_report": report,
                }
        
        return {
            "messages": [result],
            "market_report": report,
        }
    
    return market_analyst_node
