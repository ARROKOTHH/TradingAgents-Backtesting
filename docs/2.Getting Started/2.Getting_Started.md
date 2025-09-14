# 2. Getting Started

This guide provides all the necessary steps to get the TradingAgents-Backtesting platform running on your local machine.

## Step 1: Clone the Project

First, clone the repository from GitHub to your local machine using the following command:

```bash
git clone https://github.com/ARROKOTHH/TradingAgents-Backtesting.git
cd TradingAgents-Backtesting
```

## Step 2: Environment Preparation

It is highly recommended to use **Python 3.11**. You can manage your Python versions using tools like `conda` or `pyenv`.

To create a new environment with conda:
```bash
conda create -n tradingagents python=3.11
conda activate tradingagents
```

## Step 3: Install Dependencies

Install all the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Step 4: Configure Environment Variables

The project uses a `.env` file to manage API keys and other sensitive configurations.

First, copy the example file:

```bash
# On Windows
copy .env.example .env

# On macOS/Linux
cp .env.example .env
```

Next, open the newly created `.env` file with a text editor and fill in your API keys for the Large Language Models you intend to use (e.g., `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.).

## Step 5: Quick Start

You can run the project via the Web UI or the CLI.

### Launching the Web UI

The most user-friendly way to interact with the platform is through the Streamlit-based Web UI.

We recommend using the provided scripts:
```bash
# On Windows
start_web.bat

# On macOS/Linux
bash start_web.sh
```

After launching, open your web browser and navigate to `http://localhost:8501`.

### Launching the CLI

For automation or integration purposes, you can use the command-line interface.

```bash
python cli/main.py
```

To see all available commands and options, use the `--help` flag:
```bash
python cli/main.py --help
```

## Alternative: Docker Deployment

If you have Docker and Docker Compose installed, you can easily run the application in a container.

1.  Ensure your `.env` file is properly configured as described in Step 4.
2.  Run the following command from the project root:

    ```bash
    docker-compose up --build -d
    ```

The service will start in the background. To view the application logs, use:
```bash
docker-compose logs -f
```
