# 1. Introduction to TradingAgents-Backtesting

Welcome to the official documentation for **TradingAgents-Backtesting**.

This project is a sophisticated platform based on Large Language Models (LLM) and a Multi-Agent framework, designed for in-depth stock analysis and the automated backtesting of trading strategies. It is adapted from the well-known `hsliuping/TradingAgents-CN`, with a streamlined data source approach and a powerful new core feature: the ability to generate and validate `backtrader` trading strategies directly from AI-driven analysis reports.

At its core, the system simulates a professional investment research team, where different AI agents—each with a specialized role—collaborate to produce a comprehensive analysis of a given stock. This analysis is then used by a specialized "Strategy Analyst" agent to write Python code for a trading strategy, which can be immediately tested against historical data.

## Key Features

*   **🤖 Multi-Agent Collaboration**: Employs a team of specialized AI agents (market analysts, fundamental analysts, risk managers, etc.) who work together to conduct deep-dive stock analysis.
*   **🔌 Pluggable LLM Support**: Easily integrate and switch between various Large Language Models, including OpenAI (GPT series), Google (Gemini), DeepSeek, and Alibaba Qwen (Dashscope), thanks to a flexible adapter-based design.
*   **🚀 Strategy Generation & Backtesting**: The standout feature of the project. It automatically translates qualitative AI analysis reports into executable Python trading strategies and uses the robust `backtrader` engine to evaluate their historical performance.
*   **💻 Dual Interfaces**: Offers both a modern, user-friendly Web UI built with Streamlit and a powerful Command-Line Interface (CLI) for automation and integration.
*   **🐳 One-Click Docker Deployment**: Simplifies the setup process immensely with pre-configured `Dockerfile` and `docker-compose.yml` files for one-click deployment.
*   **📝 Detailed Analysis Reports**: Automatically generates structured and detailed analysis reports in Markdown format, clearly presenting the entire analysis process and its conclusions.
