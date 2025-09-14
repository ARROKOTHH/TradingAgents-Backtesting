# TradingAgents-Backtesting

一个基于大型语言模型（LLM）的多智能体（Multi-Agent）框架，用于股票分析和交易策略回测。
由知名项目hsliuping/TradingAgents-CN 修改而来，简化了数据源，增加了根据报告生成交易策略及回测验证的功能。

![System Architecture](assets/Trandingagents-Backtesting.png)

---

## 🌟 项目特色

*   **🤖 多智能体协作**: 模拟专业的投资研究团队，包含市场分析师、基本面分析师、技术分析师、风险管理师和交易员等多种角色，通过协作完成深入的股票分析。
*   **🔌 可插拔LLM支持**: 轻松集成和切换多种大型语言模型，目前已支持 OpenAI (GPT系列), Google (Gemini), DeepSeek, 阿里云通义千问 (Dashscope) 等。
*   **📊 丰富的数据源**: 集成了包括 `Akshare`, `Google News`, `Reddit` 在内的多种实时和历史数据源，覆盖中国A股、港股、美股等主要市场。
*   **🚀 策略生成与回测**: 能够基于AI分析自动生成交易策略，并使用内置的回测引擎对策略进行历史数据回测，评估其有效性。
*   **💻 双重操作界面**:
    *   **Web UI**: 提供基于 Streamlit 的现代化、易于操作的图形用户界面。
    *   **CLI**: 提供功能强大的命令行界面，方便自动化和集成。
*   **🐳 Docker一键部署**: 提供 `Dockerfile` 和 `docker-compose.yml`，支持一键构建和部署，极大简化了环境配置流程。
*   **📝 详细的分析报告**: 自动生成结构化的分析报告（Markdown 或 JSON 格式），清晰展示分析过程和结论。

---

## 🛠️ 安装与环境配置

### 1. 克隆项目

```bash
git clone https://github.com/ARROKOTHH/TradingAgents-Backtesting.git
cd TradingAgents-Backtesting
```

### 2. 环境准备

推荐使用 Python 3.11 版本。你可以使用 [conda](https://github.com/conda/conda) 或其他工具来管理 Python 版本。

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制环境变量示例文件，并根据你的实际情况填写 API 密钥等信息。

```bash
# 在 Windows 上
copy .env.example .env

# 在 macOS/Linux 上
cp .env.example .env
```

然后，编辑 `.env` 文件，填入你所使用的 LLM API Key 和其他必要的配置信息。

---

## 🚀 快速开始

你可以通过 Web UI 或 CLI 两种方式来运行本项目。

### 启动 Web UI

执行以下命令来启动图形化界面：

```bash
# 推荐使用封装好的脚本
# 在 Windows 上
start_web.bat

# 在 macOS/Linux 上
bash start_web.sh

# 或者直接运行
python start_web.py
```

启动后，在浏览器中打开 `http://localhost:8501` 即可开始使用。

### 启动 CLI

执行以下命令来启动命令行界面：

```bash
python cli/main.py
```

你可以通过 `--help` 参数查看所有可用的命令和选项：

```bash
python cli/main.py --help
```

---

## 🐳 Docker 部署

如果你希望通过 Docker 运行，项目已提供 `docker-compose.yml` 文件。

1.  **确保 Docker 和 Docker Compose 已安装。**
2.  **确保你的 `.env` 文件已经配置好。**

然后执行以下命令来构建并启动服务：

```bash
docker-compose up --build -d
```

服务将在后台运行。你可以通过以下命令查看日志：

```bash
docker-compose logs -f
```

---

## 📁 项目结构简介

```
.
├── tradingagents/    # 核心代码目录
│   ├── agents/       # 各类智能体定义
│   ├── config/       # 配置管理
│   ├── dataflows/    # 数据流和数据源管理
│   ├── graph/        # 智能体协作图（工作流）
│   ├── llm_adapters/ # LLM 适配器
│   └── tools/        # 智能体使用的工具
├── web/              # Web UI (Streamlit) 相关代码
├── cli/              # CLI 相关代码
├── Backtesting/      # 回测引擎
├── Strategy/         # 保存生成的策略文件
├── analysis reports/ # 保存分析报告
├── requirements.txt  # Python 依赖
├── docker-compose.yml# Docker 编排文件
└── README.md         # 本文档
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。
