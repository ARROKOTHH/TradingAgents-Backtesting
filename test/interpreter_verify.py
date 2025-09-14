import sys
import os
import pandas as pd

# 1. 设置Python环境路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from tradingagents.dataflows.akshare_utils import AKShareProvider

def interpreter_verify():
    print("--- Interpreter Verification Step-by-Step ---")
    
    # 2. 调用AKShareProvider获取数据
    print("\n[Step 1] Initializing AKShareProvider...")
    provider = AKShareProvider()
    print("Provider initialized.")

    symbol = "NVDA"
    start_date = "2024-09-08"
    end_date = "2025-09-08"
    print(f"\n[Step 2] Fetching data for {symbol}...")
    hist_data = provider.get_us_stock_data(symbol=symbol, start_date=start_date, end_date=end_date)

    # 3. 打印数据结构
    if hist_data is not None and not hist_data.empty:
        print("Data fetched successfully!")
        print("\n[Step 3] Analyzing DataFrame structure:")
        print("\nColumns:")
        print(hist_data.columns)
        print("\nIndex:")
        print(hist_data.index.name)
        print("\nHead (first 5 rows):")
        print(hist_data.head())
    else:
        print("\n[Step 3] ERROR: Failed to fetch data or the DataFrame is empty.")

if __name__ == "__main__":
    interpreter_verify()
