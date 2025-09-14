import streamlit as st
import os
import re
import datetime
from pathlib import Path

# 路径处理
import sys
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Backtesting.backtesting import run_backtest

# LangChain 和 LLM Adapter 相关导入
from langchain_core.messages import HumanMessage
from tradingagents.llm_adapters import ChatDashScope, ChatGoogleOpenAI

def get_llm_adapter(config: dict):
    """根据配置返回一个LLM适配器实例"""
    provider = config.get("llm_provider", "dashscope")
    model_name = config.get("llm_model", "qwen-turbo")
    
    # 增加max_tokens参数以生成更长的回复
    if provider == "dashscope":
        return ChatDashScope(model=model_name, max_tokens=8192)
    elif provider == "google":
        return ChatGoogleOpenAI(model=model_name, max_tokens=8192)
    else:
        return ChatDashScope(model=model_name, max_tokens=8192)

def extract_python_code(raw_string: str) -> str:
    """
    从AI返回的原始字符串中提取纯净的Python策略类代码。
    1. 优先寻找 ```python ... ``` 代码块。
    2. 从中移除 if __name__ == '__main__': 测试代码块。
    """
    code = raw_string
    
    # 1. 优先提取 markdown block 的内容
    match = re.search(r'```python\n(.*?)\n```', code, re.DOTALL)
    if match:
        code = match.group(1)

    # 2. 移除 if __name__ == '__main__': block
    main_guard_pos = code.find("if __name__ == '__main__':")
    if main_guard_pos != -1:
        code = code[:main_guard_pos]

    return code.strip()

def initialize_state():
    """初始化会话状态"""
    if 'report_summary' not in st.session_state:
        st.session_state.report_summary = None
    if 'strategy_code' not in st.session_state:
        st.session_state.strategy_code = None
    if 'strategy_filepath' not in st.session_state:
        st.session_state.strategy_filepath = None
    if 'thinking_process' not in st.session_state:
        st.session_state.thinking_process = None
    if 'syntax_error' not in st.session_state:
        st.session_state.syntax_error = None

def render_strategy_backtesting_page():
    """渲染策略生成与回测页面"""
    st.header("📈 策略生成与回测 (三步流程)")
    st.markdown("通过透明化的三个步骤，将分析报告转化为可回测的交易策略。" )
    
    initialize_state()

    # --- 1. 选择分析报告 ---
    st.markdown("---")
    st.subheader("第一步: 选择并解析分析报告")
    report_dir = project_root / "analysis reports"
    try:
        report_files = sorted([f for f in os.listdir(report_dir) if f.endswith('.md')], reverse=True)
        if not report_files:
            st.warning("⚠️ 在 `analysis reports` 目录中未找到任何分析报告 (.md) 文件。" )
            return
        selected_report = st.selectbox("选择一份分析报告以生成策略：", options=report_files, index=0, key="selected_report_file")
    except FileNotFoundError:
        st.error(f"❌ 目录不存在: `{report_dir}`。请确保已创建该目录。" )
        return

    if st.button("1. 解析报告", key="parse_report_button"):
        with st.spinner("正在调用AI分析师解析报告，请稍候..."):
            try:
                report_path = report_dir / selected_report
                with open(report_path, 'r', encoding='utf-8') as f:
                    report_content = f.read()
                
                if not report_content.strip():
                    st.error("错误: 读取的报告文件内容为空。" )
                    return

                if 'config' not in st.session_state:
                    st.error("无法获取AI模型配置，请先在'股票分析'页面进行一次分析以初始化配置。" )
                    return

                prompt = f"""
您是一位顶级的量化策略设计师。您的任务是结合基本面、新闻和技术分析，将一份复杂的分析报告转化为一个通用的、可长期回测的交易策略。

**【第一步：策略风格诊断】**
首先，通读并理解整个报告。根据综合信息，判断最适合的【策略风格】（例如：积极趋势型, 稳健趋势型, 均值回归型等）。

**【第二步：策略风险偏好】**
- **读取报告的最终结论**: 首先，找到报告中最明确的投资建议（例如“买入”、“强烈买入”等）。
- **设定风险等级**: 根据这个结论，设定一个风险等级（高、中、低）。
- **在你的回答中明确指出【策略风格】和【风险偏好】及其理由。**

**【第三步：量化规则构建】**
在确定了风格和风险偏好后，构建具体的、可量化的交易规则。

**【盈利性与风险要求】**
- **目标**: 规则的设计目标是在回测中使 **Profit Factor（盈利因子）大于3**。
- **风险匹配**: 所有规则都必须与你在上面设定的【风险偏好】相匹配。例如，“高风险偏好”应对应更积极的入场和仓位管理逻辑。
- **“B计划”规则 (必须提供)**: 必须提供一个比主要规则更宽松的“B计划”入场规则。
- **让利润奔跑**: 在趋势明确的牛市中，**必须优先使用追踪止损或趋势衰竭信号作为止盈方式**，而不是设定一个固定的、较小的止盈目标。

**您的摘要必须包含以下几个部分:**
1.  **策略风格与风险偏好**: [明确指出，并说明理由]
2.  **核心逻辑**: [策略的核心思想]
3.  **趋势判断规则**: [判断市场的总体趋势的方法]
4.  **入场条件**: 
    - **主要规则**: [描述主要规则]
    - **B计划规则**: [描述B计划规则，并解释理由]
5.  **出场条件（止盈）**: [描述清晰的、最好是追踪性质的止盈规则]
6.  **出场条件（止损）**: [描述清晰的止损规则]
7.  **(可选) 仓位管理**: [是否有加仓或分批止盈的逻辑]

**分析报告全文:**
---
{report_content}
---

请现在开始您的工作。
"""
                messages = [HumanMessage(content=prompt)]
                llm = get_llm_adapter(st.session_state.config)
                result = llm.invoke(messages)
                
                st.session_state.report_summary = result.content
                st.session_state.strategy_code = None
                st.session_state.strategy_filepath = None
                st.session_state.thinking_process = None
                st.session_state.syntax_error = None

            except Exception as e:
                st.error(f"❌ 解析报告时发生错误: {e}")
                st.exception(e)

    if st.session_state.report_summary:
        st.markdown("#### AI分析师的报告摘要:")
        st.info(st.session_state.report_summary)

        # --- Manual Override for Risk Appetite ---
        st.markdown("#### 核心参数调整 (可选)")
        
        def get_suggested_risk(summary_text):
            if "高风险偏好" in summary_text:
                return "高"
            if "低风险偏好" in summary_text:
                return "低"
            return "中等"

        risk_options = ["低", "中等", "高"]
        suggested_risk = get_suggested_risk(st.session_state.report_summary)
        try:
            default_index = risk_options.index(suggested_risk)
        except ValueError:
            default_index = 1

        final_risk_appetite = st.selectbox(
            "根据您的判断，手动覆盖最终的风险偏好等级：",
            options=risk_options,
            index=default_index,
            key="final_risk_appetite"
        )
        st.info(f"AI分析师的建议是“{suggested_risk}”，但最终将以您选择的“{final_risk_appetite}”等级生成策略。" )

    # --- 2. 生成策略代码 ---
    st.markdown("---")
    st.subheader("第二步: 生成策略代码 (AI自我修正)")
    if st.button("2. 生成策略", key="generate_code_button", disabled=not st.session_state.report_summary):
        with st.spinner("正在调用AI工程师生成代码，AI将自动修正语法错误..."):
            try:
                if 'config' not in st.session_state:
                    st.error("无法获取AI模型配置。" )
                    return

                max_retries = 3
                error_message = ""
                
                for i in range(max_retries):
                    st.write(f"正在进行第 {i + 1}/{max_retries} 次代码生成尝试...")

                    if i == 0:
                        prompt = f"""
您是一位顶级的量化策略工程师。您的任务是根据以下策略摘要和【最终风险偏好】，编写一个完整的、可执行的`backtrader`策略文件。

**【最终风险偏好】**: **{st.session_state.final_risk_appetite}**

**【重要指令】**
- **最重要**: 你的所有代码逻辑，特别是参数选择，都必须严格遵循上面指定的【最终风险偏好】，而不是策略摘要里原有的建议。
- 你的回复**必须**包含一个Python代码块，以 ```python 开始，并以 ``` 结束。
- 类名**必须**为 `CustomStrategy`。
- **不要**包含 `if __name__ == '__main__':` 测试代码块。
- **必须**在策略的 `__init__` 方法中初始化 `self.daily_values = []`。
- **必须**在 `next` 方法的末尾处添加 `self.daily_values.append(self.broker.getvalue())`。
- **不要**在`next`方法中修改`self.daily_values`的初始化方式或数据结构。
- **除了这个代码块，不要包含任何其他文字**。

**要实现的策略摘要:** 
---
{st.session_state.report_summary}
---

请现在开始您的工作。
"""
                    else:
                        prompt = f"""
您上次的代码有语法错误，请修正。原始策略要求和最终风险偏好不变。

**【最终风险偏好】**: **{st.session_state.final_risk_appetite}**

**【有问题的代码】:**
---
{st.session_state.strategy_code}
---

**【语法错误】:**
---
{error_message}
---

**【原始策略要求】:**
---
{st.session_state.report_summary}
---

**【重要指令】**
- 你的回复**必须**只包含修正后的Python代码块，以 ```python 开始，并以 ``` 结束。
- 类名**必须**为 `CustomStrategy`。
- **不要**包含 `if __name__ == '__main__':` 测试代码块。
- **必须**在策略的 `__init__` 方法中初始化 `self.daily_values = []`。
- **必须**在 `next` 方法的末尾处添加 `self.daily_values.append(self.broker.getvalue())`。
- **不要**在`next`方法中修改`self.daily_values`的初始化方式或数据结构。
- **除了代码块，不要有任何其他文字**。
"""

                    with st.expander(f"第 {i + 1} 次尝试的AI通信细节 (调试用)", expanded=False):
                        st.write("**Prompt Sent to AI:**")
                        st.text(prompt)
                        messages = [HumanMessage(content=prompt)]
                        llm = get_llm_adapter(st.session_state.config)
                        result = llm.invoke(messages)
                        st.write("**Raw Result from AI:**")
                        st.write(result)

                    st.session_state.strategy_code = extract_python_code(result.content)
                    st.session_state.thinking_process = "（AI自我修正模式）"

                    try:
                        compile(st.session_state.strategy_code, 'generated_strategy', 'exec')
                        st.success(f"✅ AI在第 {i + 1} 次尝试后生成了通过语法检查的代码。" )
                        
                        symbol_match = re.search(r'(\d+\..+?)_', selected_report) or re.search(r'(.*?)', selected_report)
                        stock_symbol = "UNKNOWN"
                        if symbol_match:
                            stock_symbol = symbol_match.group(1).replace(".", "_")
                        
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        strategy_dir = project_root / "Strategy"
                        strategy_dir.mkdir(exist_ok=True)
                        strategy_filename = f"strategy_{{stock_symbol}}_{timestamp}.py"
                        strategy_filepath = strategy_dir / strategy_filename
                        
                        with open(strategy_filepath, 'w', encoding='utf-8') as f:
                            f.write(st.session_state.strategy_code)
                        
                        st.session_state.strategy_filepath = str(strategy_filepath)
                        st.session_state.syntax_error = None
                        st.success(f"代码已成功生成并保存为: `{strategy_filename}`")
                        break

                    except SyntaxError as e:
                        error_message = str(e)
                        st.session_state.syntax_error = error_message
                        st.session_state.strategy_filepath = None
                        st.warning(f"第 {i + 1} 次尝试失败: {error_message}")
                        if i == max_retries - 1:
                            st.error(f"❌ AI在 {max_retries} 次尝试后仍无法生成语法正确的代码。" )

            except Exception as e:
                st.error(f"❌ 生成策略时发生严重错误: {e}")
                st.exception(e)

    if st.session_state.get('strategy_code'):
        st.markdown("#### AI生成的最终代码:")
        st.code(st.session_state.strategy_code, language='python')

        if st.session_state.get('syntax_error'):
            st.error(f"❌ 最终代码存在语法错误: {st.session_state.syntax_error}")
        elif st.session_state.get('strategy_filepath'):
            st.success("✅ 代码已成功生成并保存，可以进行回测。" )

    # --- 3. 运行回测 ---
    st.markdown("---")
    st.subheader("第三步: 配置并运行回测")

    default_symbol = ""
    if st.session_state.get("selected_report_file"):
        try:
            symbol_match = re.search(r'(\d+\..+?)_', st.session_state.selected_report_file) or re.search(r'(.*?)', st.session_state.selected_report_file)
            default_symbol = symbol_match.group(1) if symbol_match else ""
        except IndexError:
            default_symbol = ""

    col1, col2, col3 = st.columns(3)
    with col1:
        backtest_symbol = st.text_input("回测股票代码 (例如: 600519, sh600519, AAPL)", value=default_symbol, key="backtest_symbol")
        start_date = st.date_input("回测开始日期", datetime.date(2022, 1, 1))
    with col2:
        end_date = st.date_input("回测结束日期", datetime.date.today())
    with col3:
        initial_cash = st.number_input("初始资金", min_value=1000, value=100000, step=1000)

    if st.button("3. 运行回测", key="run_backtest_button", disabled=not st.session_state.strategy_filepath):
        with st.spinner("正在运行回测，请稍候..."):
            try:
                symbol = st.session_state.backtest_symbol
                if not symbol:
                    st.error("回测股票代码不能为空。" )
                    return

                market = "A股" if symbol.isdigit() else "美股"

                plot_fig, summary_md = run_backtest(
                    use_akshare=True,
                    symbol=symbol,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    source=market,
                    use_custom_strategy=True,
                    strategy_file=st.session_state.strategy_filepath,
                    initial_cash=initial_cash
                )
                
                st.markdown("#### 回测结果:")
                st.pyplot(plot_fig)
                st.markdown(summary_md)

            except Exception as e:
                st.error(f"❌ 运行回测时发生错误: {e}")
                st.exception(e)