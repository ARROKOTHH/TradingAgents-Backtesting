# 4. Core Workflow

The TradingAgents-Backtesting platform operates on a clear, sequential workflow that transforms a user's request into a fully backtested trading strategy. This document outlines the end-to-end process.

![System Architecture](assets/Trandingagents-Backtesting.png)
*(This diagram is located in the `assets` folder at the project root)*

## Workflow Stages

The entire process can be broken down into two major phases: **Analysis** and **Backtesting**.

### Phase 1: Analysis - Generating the Investment Report

This phase is handled by the multi-agent system.

1.  **User Input**: The process begins when the user inputs a stock symbol (e.g., `NVDA`) and a research question into the Web UI or CLI. The user also selects the LLMs to be used for "fast thinking" and "deep thinking" tasks from the sidebar.

2.  **Graph Invocation**: The system invokes the multi-agent collaboration workflow defined in `tradingagents/graph/trading_graph.py`.

3.  **Agent Collaboration**: The agents work in a sequence orchestrated by LangGraph:
    *   **Data Collection**: Agents like the `MarketAnalyst` and `NewsAnalyst` fetch relevant data, including real-time news, market sentiment, and fundamental financial data.
    *   **In-depth Research**: `BullResearcher` and `BearResearcher` agents take opposing viewpoints to conduct a thorough analysis, identifying potential opportunities and risks.
    *   **Synthesis & Debate**: The findings are synthesized, and debator agents (`AggressiveDebator`, `ConservativeDebator`) argue the key points to refine the investment thesis.
    *   **Risk Assessment**: The `RiskManager` evaluates the proposed course of action and provides a risk assessment.
    *   **Final Verdict**: The `Trader` agent makes the final decision, summarizing the entire analysis into a coherent investment report.

4.  **Report Generation**: The final output is a detailed Markdown report, which is automatically saved to the `analysis reports/` directory. The user is notified of the saved location.

### Phase 2: Backtesting - From Report to Strategy Validation

This phase leverages the generated report to create and test a trading strategy.

1.  **Report Selection**: The user navigates to the "Strategy Generation & Backtesting" page in the Web UI and selects the previously generated analysis report.

2.  **Strategy Blueprint Generation**: The application sends the content of the report to an LLM with a specialized prompt, asking it to create a high-level "blueprint" or logic for a trading strategy based on the report's conclusions.

3.  **Code Generation**: This blueprint is then passed to the LLM again, along with a more detailed prompt containing coding instructions and best practices for the `backtrader` framework. The LLM generates the full Python code for the strategy.

4.  **Automated Code Correction**: Before compilation, the generated code is passed through a "Code Reviewer" function (`auto_correct_backtrader_code`). This function uses regular expressions to automatically fix common syntax errors that LLMs often make when writing `backtrader` code (e.g., correcting `.DIm` to `.lines.DIm`). This step dramatically improves the reliability of the generated code.

5.  **Backtest Execution**: The user provides backtesting parameters (start date, end date, initial capital). The system then uses the `Backtesting/backtesting.py` module to run the corrected strategy code against historical data.

6.  **Results Display**: The results of the backtest, including performance metrics and a plot showing trades, are displayed directly in the Web UI for immediate evaluation.
