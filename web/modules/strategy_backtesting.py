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
from tradingagents.config import config_manager
from tradingagents.llm_adapters.openai_compatible_base import create_openai_compatible_llm
from tradingagents.llm_adapters.google_openai_adapter import create_google_openai_llm

def auto_correct_backtrader_code(code: str) -> str:
    """
    自动修正Backtrader代码中常见的.lines属性访问错误。
    """
    # 规则：(错误模式, 正确模式)
    # 使用正则表达式确保只替换属性访问，避免替换字符串内容
    correction_rules = [
        (r'(\.histo)', r'.lines.histo'),
        (r'(\.DIp)', r'.lines.DIp'),
        (r'(\.DIm)', r'.lines.DIm'),
        (r'(\.DIplus)', r'.lines.DIp'),
        (r'(\.DIminus)', r'.lines.DIm'),
        (r'(\.adx)', r'.lines.adx'),
        (r'(\.top)', r'.lines.top'),
        (r'(\.mid)', r'.lines.mid'),
        (r'(\.bot)', r'.lines.bot'),
        (r'(\.signal)', r'.lines.signal'),
        (r'(\.macd)', r'.lines.macd'),
    ]
    
    corrected_code = code
    for pattern, replacement in correction_rules:
        # 使用负向先行断言来避免重复替换, e.g., .lines.histo
        regex = r'(?<!\.lines)' + pattern
        corrected_code = re.sub(regex, replacement, corrected_code)
        
    return corrected_code

def get_llm_instance(llm_config: dict):
    """根据传入的完整LLM配置，创建并返回一个LLM实例"""
    provider = llm_config.get("llm_provider")
    # 优先使用深度思考模型，如果不存在则使用快速思考模型
    model_name = llm_config.get("deep_think_llm") or llm_config.get("quick_think_llm")
    
    if not provider or not model_name:
        raise ValueError("LLM provider or model name is missing in the configuration.")

    # 统一使用工厂函数创建实例
    # 注意：这里我们传递整个llm_config，因为它包含了如max_tokens等您需要的参数
    if provider == "google":
        return create_google_openai_llm(model=model_name, **llm_config)
    else:
        # 对于所有其他兼容OpenAI的提供商
        return create_openai_compatible_llm(provider=provider, model=model_name, **llm_config)

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

def render_strategy_backtesting_page(llm_config: dict):
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

                if not llm_config:
                    st.error("无法获取AI模型配置，请返回主页签并选择模型。" )
                    return

                prompt = f"""
您是一位顶级的量化策略设计师。您的任务是基于一份分析报告中的【原始分析模块】，独立形成判断，并构建一个结构清晰、逻辑严谨、可长期回测的`backtrader`交易策略蓝图。

**【核心指令：信息聚焦 (Core Instruction: Information Focus)】**
1.  **信息源白名单**: 您的分析和策略设计 **必须且只能** 基于报告中的以下几个原始分析模块：
    *   **投资决策摘要 (Investment Decision Summary)**
    *   **市场技术分析 (Market Technical Analysis)**
    *   **基本面分析 (Fundamentals Analysis)**
    *   **新闻事件分析 (News Event Analysis)**
    *   **市场情绪分析 (Market Sentiment Analysis)**
2.  **信息源黑名单**: 您 **必须完全忽略** 报告中所有后续的、包含二次解读和多方辩论的模块，包括但不限于：
    *   风险评估（所有风险分析师的观点）
    *   研究团队决策（多头/空头研究员的辩论）
    *   交易团队计划
    *   风险管理团队决策
3.  **决策主导思想**: 以【投资决策摘要】中的“投资建议”（如‘买入’、‘持有’）作为您构建策略的**核心指导方向**（即，构建一个做多策略、中性策略还是规避策略）。您的角色是基于原始分析，为这个大方向设计出最合理的量化执行方案。

**【重要约束条件】**
- **数据源限制**: 策略只能基于OHLCV数据。
- **指标库限制**: 策略只能使用`backtrader`内置的常见指标。

**【核心设计哲学】**
- **逻辑优先**: 所有规则的设计必须优先考虑其经济学或市场行为学上的合理解释。
- **稳健性**: 规则应具备一定的普适性，避免使用过于复杂的指标组合。
- **可触发性**: 确保入场规则的组合在真实市场中是合理且有机会触发的。

**您的策略蓝图必须严格遵循以下结构:**

1.  **策略画像**:
    *   **策略风格**: [明确指出，并说明理由]
    *   **风险偏好**: [明确指出，并说明理由]

2.  **核心参数 (Parameters)**:
    *   [列出所有策略参数及其建议的默认值。]

3.  **量化趋势过滤器 (Trend Filter)**:
    *   [定义1-2个具体的、可编码的规则来判断市场趋势。]

4.  **量化入场信号 (Entry Signal)**:
    *   **主要规则 (Plan A)**: 
        *   [定义1-3个清晰的、可编码的买入信号组合。]
        *   **信号组合最佳实践**: 当组合多个指标时，应避免使用在时间上存在滞后矛盾的条件。例如，不要将一个早期的反转信号（如RSI刚上穿低位）与一个需要趋势确认的滞后信号（如MACD柱状图为正）作为同一天的触发条件。
    *   **备用规则 (Plan B)**: [提供一个比主要规则更宽松或基于不同逻辑的备用入场规则。]

5.  **量化出场逻辑 (Exit Logic)**:
    *   **止盈/止损规则**: [描述清晰的止盈止损规则，强烈推荐使用基于ATR的追踪止损。]

6.  **量化风险管理 (Risk Management)**:
    *   **仓位规模**: [描述清晰的仓位管理逻辑，强烈推荐使用固定风险百分比模型。]

**分析报告全文:**
---
{report_content}
---

请现在开始您的工作。
"""
                messages = [HumanMessage(content=prompt)]
                llm = get_llm_instance(llm_config)
                result = llm.invoke(messages)
                
                st.session_state.report_summary = result.content
                st.session_state.strategy_code = None
                st.session_state.strategy_filepath = None
                st.session_state.thinking_process = None
                st.session_state.syntax_error = None

            except Exception as e:
                st.error(f"❌ 解析报告时发生错误: {{e}}")
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
        st.info(f"AI分析师的建议是“{{suggested_risk}}”，但最终将以您选择的“{{final_risk_appetite}}”等级生成策略。" )

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
                    st.write(f"正在进行第 {{i + 1}}/{{max_retries}} 次代码生成尝试...")

                    if i == 0:
                        prompt = f"""
您是一位顶级的、精通`backtrader`框架的量化策略工程师。您的任务是根据策略摘要和最终风险偏好，编写一个完整的、高质量的、可立即执行的`backtrader`策略文件。

**【最终风险偏好】**: **{{st.session_state.final_risk_appetite}}**

---
**【Backtrader 编码核心准则】**
您必须严格遵守以下所有准则，否则代码将无法运行：

1.  **参数定义 (Parameter Definition)**:
    *   **必须遵循**: 参数**必须**在 `__init__` 方法之外，作为类级别的 `params` 字典或元组来定义。这为策略提供了可调整的默认值。
    *   **动态调整**: 如果需要根据风险偏好等条件动态调整参数，**必须**在 `__init__` 方法的**最开始**，通过修改 `self.p.parameter_name` 的值来完成。
    *   **禁止模式**: 严禁在 `__init__` 中调用一个独立的辅助函数来定义或返回参数字典。所有参数的修改都应直接作用于 `self.p`。
    *   **正确示例**:
      ```python
      class CustomStrategy(bt.Strategy):
          params = (('fast_ma', 10), ('slow_ma', 20)) # 默认值

          def __init__(self):
              # 如果风险偏好是激进型，则覆盖默认值
              if "{st.session_state.final_risk_appetite}" == '激进型':
                  self.p.fast_ma = 5
                  self.p.slow_ma = 15
              
              # 然后再初始化指标
              self.fast_ma_ind = bt.ind.SMA(period=self.p.fast_ma)
              # ...
      ```

2.  **仓位检查**: 在执行任何 `self.buy()` 操作前，**必须**先通过 `if not self.position:` 或 `if self.position.size == 0:` 来检查当前是否为空仓。
3.  **数据访问**:
    *   访问当前K线数据，**必须**使用 `[0]` 索引，例如 `self.data.close[0]`。
    *   访问上一根K线数据，**必须**使用 `[-1]` 索引，例如 `self.data.close[-1]`。
4.  **多线指标访问 (最重要)**:
    *   当使用有多个输出线的指标时（如MACD, 布林带, ADX/DMI等），**必须**通过其 `.lines` 属性来访问具体的线。
    *   **正确示例**: `self.macd.lines.histo`, `self.bband.lines.top`, `self.adx.lines.adx`, `self.dmi.lines.DIp` (用于DI+), `self.dmi.lines.DIm` (用于DI-)。
    *   **错误示例**: `self.macd.histo`, `self.bband.top`, `self.dmi.DIplus`。
5.  **交叉信号**:
    *   对于“上穿”或“下穿”逻辑，**强烈建议**使用 `backtrader` 内置的 `bt.indicators.CrossOver` 或 `CrossDown` 指标。
6.  **多步信号状态管理**:
    *   如果策略逻辑包含多个步骤（例如，“条件A发生后，等待条件B”），**必须**使用实例变量（如 `self.condition_A_met = False`）来跟踪状态。
---

**【新增核心准则：诊断日志 (Diagnostic Logging)】**
- **强制要求 (最重要)**: 为了诊断策略为何不交易，您**必须**在 `next` 方法的逻辑判断部分，加入 `print()` 语句来输出关键信息。这是强制性的，如果缺失，任务将被视为失败。
- **日志内容**:
    - **每日关键指标 (必须打印)**: 在 `next` 方法的开头，打印当天的日期、收盘价以及策略中用到的所有关键指标的当前值。例如: `print(f"Date: {{self.datas[0].datetime.date(0)}}, Close: {{self.data.close[0]:.2f}}, RSI: {{self.rsi[0]:.2f}}, MACD Hist: {{self.macd.lines.histo[0]:.2f}}")`。
    - **入场条件判断 (必须打印)**: 在 `if not self.position:` 块内部，计算买入条件后，**必须**打印该条件的最终布尔值结果。例如: `buy_condition = self.rsi[0] < 30 and self.macd.lines.histo[0] > 0`, `print(f"Buy Condition Met: {{buy_condition}}")`。
- **目的**: 这些日志是分析策略行为的关键，必须无条件包含。

---
**【新增核心准-则：避免逻辑矛盾 (Avoiding Logical Contradictions)】**
- **问题场景**: 很多策略因为买入条件互相矛盾而从不触发。例如，同时要求`RSI < 30`（超卖，通常发生在下跌趋势中）和`MACD > 0`（上涨趋势确认）。
- **解决方案**:
    - **使用“或”逻辑**: 如果有多个独立的买入信号，使用 `or` 连接它们，而不是 `and`。
    - **设计分步逻辑**: 设计更现实的交易场景，例如“首先等待价格回调（如RSI进入低位），然后在趋势确认后（如MACD金叉）再买入”。这需要使用状态变量（如 `self.waiting_for_confirmation = True`）来管理。
    - **考虑成交量**: 将成交量放大作为确认信号，可以有效过滤伪信号。

---
**【新增核心准-则：扩展指标库 (Indicator Toolbox)】**
- **打破局限**: 请不要只使用简单的移动平均线。
- **强烈建议**: 在设计策略时，从以下列表中选择和组合指标来构建更强大的逻辑：`RSI`, `MACD`, `Stochastic`, `Bollinger Bands`, `ADX`, `Volume`。

---
**【其他重要指令】**
- 你的所有代码逻辑，特别是参数选择，都必须严格遵循上面指定的【最终风险偏好】。
- 你的回复**必须**只包含一个Python代码块，以 ```python 开始，并以 ``` 结束。
- 类名**必须**为 `CustomStrategy`。
- **不要**包含 `if __name__ == '__main__':` 测试代码块。
- **必须**在策略的 `__init__` 方法中初始化 `self.daily_values = []`。
- **必须**在 `next` 方法的末尾处添加 `self.daily_values.append(self.broker.getvalue())`。
- **除了这个代码块，不要包含任何其他文字**。

**要实现的策略摘要:**
---
{{st.session_state.report_summary}}
---

请现在开始您的工作。
"""
                    else:
                        prompt = f"""
您上次的代码有语法错误，请修正。原始策略要求和最终风险偏好不变。

**【最终风险偏好】**: **{{st.session_state.final_risk_appetite}}**

**【有问题的代码】:**
---
{{st.session_state.strategy_code}}
---

**【语法错误】:**
---
{{error_message}}
---

**【原始策略要求】:**
---
{{st.session_state.report_summary}}
---

---
**【Backtrader 编码核心准则】**
请再次检查您的代码，确保它严格遵守了以下所有准则：

1.  **仓位检查**: 在执行任何 `self.buy()` 操作前，**必须**先通过 `if not self.position:` 或 `if self.position.size == 0:` 来检查当前是否为空仓。
2.  **数据访问**:
    *   访问当前K线数据，**必须**使用 `[0]` 索引，例如 `self.data.close[0]`。
    *   访问上一根K线数据，**必须**使用 `[-1]` 索引，例如 `self.data.close[-1]`。
3.  **多线指标访问 (最重要)**:
    *   当使用有多个输出线的指标时（如MACD, 布林带, ADX等），**必须**通过其 `.lines` 属性来访问具体的线。
    *   **正确示例**: `self.macd.lines.histo`, `self.bband.lines.top`, `self.adx.lines.adx`。
    *   **错误示例**: `self.macd.histo`, `self.bband.top`。
4.  **交叉信号**:
    *   对于“上穿”或“下穿”逻辑，**强烈建议**使用 `backtrader` 内置的 `bt.indicators.CrossOver` 或 `CrossDown` 指标。
    *   **示例**: 在 `__init__` 中定义 `self.buy_signal = bt.ind.CrossOver(self.fast_ma, self.slow_ma)`，然后在 `next` 中判断 `if self.buy_signal[0] > 0:`。
5.  **多步信号状态管理**:
    *   如果策略逻辑包含多个步骤（例如，“条件A发生后，等待条件B”），**必须**使用实例变量（如 `self.condition_A_met = False`）来跟踪状态。
---

**【其他重要指令】**
- 你的回复**必须**只包含修正后的Python代码块，以 ```python 开始，并以 ``` 结束。
- 类名**必须**为 `CustomStrategy`。
- **不要**包含 `if __name__ == '__main__':` 测试代码块。
- **必须**在策略的 `__init__` 方法中初始化 `self.daily_values = []`。
- **必须**在 `next` 方法的末尾处添加 `self.daily_values.append(self.broker.getvalue())`。
- **除了代码块，不要有任何其他文字**。
"""

                    with st.expander(f"第 {{i + 1}} 次尝试的AI通信细节 (调试用)", expanded=False):
                        st.write("**Prompt Sent to AI:**")
                        st.text(prompt)
                        messages = [HumanMessage(content=prompt)]
                        llm = get_llm_instance(llm_config)
                        result = llm.invoke(messages)
                        st.write("**Raw Result from AI:**")
                        st.write(result)

                    raw_code = extract_python_code(result.content)
                    st.session_state.strategy_code = auto_correct_backtrader_code(raw_code)
                    st.session_state.thinking_process = "（AI自我修正模式）"

                    try:
                        compile(st.session_state.strategy_code, 'generated_strategy', 'exec')
                        st.success(f"✅ AI在第 {{i + 1}} 次尝试后生成了通过语法检查的代码。" )
                        
                        symbol_match = re.search(r'(\d+\..+?)_', selected_report) or re.search(r'(.*?)', selected_report)
                        stock_symbol = "UNKNOWN"
                        if symbol_match:
                            stock_symbol = symbol_match.group(1).replace(".", "_")
                        
                        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        strategy_dir = project_root / "Strategy"
                        strategy_dir.mkdir(exist_ok=True)
                        strategy_filename = f"strategy_{{stock_symbol}}_{{timestamp}}.py"
                        strategy_filepath = strategy_dir / strategy_filename
                        
                        with open(strategy_filepath, 'w', encoding='utf-8') as f:
                            f.write(st.session_state.strategy_code)
                        
                        st.session_state.strategy_filepath = str(strategy_filepath)
                        st.session_state.syntax_error = None
                        st.success(f"代码已成功生成并保存为: `{{strategy_filename}}`")
                        break

                    except SyntaxError as e:
                        error_message = str(e)
                        st.session_state.syntax_error = error_message
                        st.session_state.strategy_filepath = None
                        st.warning(f"第 {{i + 1}} 次尝试失败: {{error_message}}")
                        if i == max_retries - 1:
                            st.error(f"❌ AI在 {{max_retries}} 次尝试后仍无法生成语法正确的代码。" )

            except Exception as e:
                st.error(f"❌ 生成策略时发生严重错误: {{e}}")
                st.exception(e)

    if st.session_state.get('strategy_code'):
        st.markdown("#### AI生成的最终代码:")
        st.code(st.session_state.strategy_code, language='python')

        if st.session_state.get('syntax_error'):
            st.error(f"❌ 最终代码存在语法错误: {{st.session_state.syntax_error}}")
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

                # 保存回测结果到session_state，供策略分析师对话使用
                st.session_state.backtest_results = {
                    "plot": plot_fig,
                    "summary": summary_md,
                    "symbol": symbol,
                    "start_date": start_date.strftime('%Y-%m-%d'),
                    "end_date": end_date.strftime('%Y-%m-%d'),
                    "initial_cash": initial_cash,
                    "market": market
                }

            except Exception as e:
                st.error(f"❌ 运行回测时发生错误: {{e}}")
                st.exception(e)
                
    # --- 4. 与策略分析师对话 ---
    if st.session_state.get('backtest_results') and st.session_state.get('strategy_code'):
        st.markdown("---")
        st.subheader("第四步: 与策略分析师对话")
        
        # 初始化对话历史
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        
        # 显示当前策略和回测结果的摘要（折叠）
        with st.expander("查看策略代码和回测结果", expanded=False):
            st.markdown("**策略代码:**")
            st.code(st.session_state.strategy_code, language='python')
            st.markdown("**回测结果:**")
            st.markdown(st.session_state.backtest_results["summary"])
        
        # 显示对话历史
        st.markdown("#### 对话历史")
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    st.markdown(f"**您:** {{msg['content']}}")
                else:
                    st.markdown(f"**策略分析师:** {{msg['content']}}")
        
        # 用户输入框
        with st.form(key="chat_form", clear_on_submit=True):
            user_input = st.text_input("向策略分析师提问或提出修改建议:", key="user_chat_input")
            submit_button = st.form_submit_button("发送")
        
        if submit_button and user_input:
            # 将用户消息添加到对话历史
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # 构建对话提示
            prompt = f"""
您是一位专业的量化策略分析师。用户希望基于以下信息对当前的交易策略进行调整：

**当前策略摘要:**
{{st.session_state.report_summary}}

**当前策略风险偏好:**
{{st.session_state.final_risk_appetite}}

**当前策略代码:**
```python
{{st.session_state.strategy_code}}
```

**最近一次回测结果:**
{{st.session_state.backtest_results["summary"]}}

**用户的具体要求:**
{{user_input}}

请根据用户的要求，提供以下信息：
1. 对用户要求的理解和分析
2. 针对用户要求的策略调整建议（可以是参数调整、逻辑修改等）
3. 如果需要修改策略代码，请提供修改后的完整代码
4. 解释修改的原因和预期效果

请以清晰、专业的方式回复用户。
"""
            
            with st.spinner("策略分析师正在思考您的要求..."):
                try:
                    messages = [HumanMessage(content=prompt)]
                    llm = get_llm_instance(llm_config)
                    result = llm.invoke(messages)
                    
                    # 将分析师回复添加到对话历史
                    st.session_state.chat_history.append({"role": "assistant", "content": result.content})
                    
                    # 重新运行页面以更新对话历史显示
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 与策略分析师对话时发生错误: {{e}}")
                    st.exception(e)
        
        # 清除对话历史按钮
        if st.button("清除对话历史"):
            st.session_state.chat_history = []
            st.rerun()
