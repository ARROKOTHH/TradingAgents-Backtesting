# 3. Project Structure

This document provides a detailed overview of the project's directory and file structure.

```
.
├── docs/               # Documentation for the project
├── tradingagents/      # Core backend source code
│   ├── agents/         # Definitions for all specialized agents
│   ├── config/         # Configuration management (models, pricing, etc.)
│   ├── dataflows/      # Data acquisition and processing from various sources
│   ├── graph/          # Definition of the agent collaboration workflow (LangGraph)
│   ├── llm_adapters/   # Adapters for different LLM providers
│   └── tools/          # Tools usable by agents (e.g., stock indicator calculations)
├── web/                # Streamlit Web UI source code
│   ├── app.py          # Main entry point and router for the web application
│   ├── components/     # Reusable UI components (e.g., sidebar, header)
│   └── modules/        # Code for individual pages/tabs in the UI
├── cli/                # Command-Line Interface (CLI) source code
│   └── main.py         # Main entry point for the CLI application
├── Backtesting/        # The core backtesting engine
│   └── backtesting.py  # Main script for running backtrader simulations
├── Strategy/           # Default directory for AI-generated strategy files
├── analysis reports/   # Default directory for saved analysis reports
├── config/             # User-facing configuration files (models.json, etc.)
├── .env                # Environment variables (API keys, etc.)
├── requirements.txt    # Python package dependencies
├── docker-compose.yml  # Docker orchestration file
└── README.md           # Main project README
```

## Key Directory Breakdown

### `tradingagents/`
This is the heart of the application, containing all the core logic.
-   **`agents/`**: Each agent (e.g., `fundamentals_analyst.py`, `risk_manager.py`) is defined here. Their roles, prompts, and capabilities are specified in this module.
-   **`config/`**: Manages the application's internal configuration. `config_manager.py` is the central hub for this.
-   **`dataflows/`**: Contains all logic for fetching data from external sources like `Akshare`, `Google News`, etc. It handles caching and data normalization.
-   **`graph/`**: This is where the multi-agent collaboration is defined using `LangGraph`. `trading_graph.py` specifies the nodes (agents) and edges (flow of information) of the workflow.
-   **`llm_adapters/`**: A critical module that implements the Adapter Pattern. It provides a unified interface for different LLMs, making it easy to switch between providers like OpenAI, Google, and DeepSeek.
-   **`tools/`**: Defines functions that can be exposed to the LLM agents as tools, such as `china_stock_indicator_tool.py`.

### `web/`
This directory contains all the code for the Streamlit-based user interface.
-   **`app.py`**: The main application file. It handles page routing and maintains the global state.
-   **`components/`**: Contains reusable parts of the UI, like the `sidebar.py`, which is crucial for LLM selection.
-   **`modules/`**: Each `.py` file here typically corresponds to a major feature or page in the UI, such as `strategy_backtesting.py`.

### `Backtesting/`
This module houses the `backtrader` implementation.
-   **`backtesting.py`**: Contains the `run_backtest` function, which takes a strategy file and backtesting parameters to execute the simulation and plot the results.

### `config/` (Root Directory)
This folder contains user-editable JSON files that control which models are available in the UI, their pricing information (for token cost calculation), and usage statistics.
