import gradio as gr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import backtrader as bt
import datetime

# ================= 回测策略（双均线 + ATR 止损止盈） =================
class DualMAATRStrategy(bt.Strategy):
    params = dict(
        fast_ma=5,
        slow_ma=20,
        long_ma=200,
        atr_period=14,
        stop_loss_atr=2,
        take_profit_1=0.30,
        take_profit_2=0.50,
        pyramid_add=0.10
    )

    def __init__(self):
        self.fast_ma = bt.ind.SMA(period=self.p.fast_ma)
        self.slow_ma = bt.ind.SMA(period=self.p.slow_ma)
        self.long_ma = bt.ind.SMA(period=self.p.long_ma)
        self.atr = bt.ind.ATR(period=self.p.atr_period)
        self.buy_price = None
        self.added_once = False
        self.added_twice = False
        # 用于记录每日账户价值
        self.daily_values = []

    def next(self):
        # Debugging prints
        # print(f"Date: {self.datas[0].datetime.date(0)}, Close: {self.data.close[0]}, Fast_MA: {self.fast_ma[0]:.2f}, Slow_MA: {self.slow_ma[0]:.2f}, Long_MA: {self.long_ma[0]:.2f}")

        if not self.position:  # 空仓 → 建仓
            condition = self.fast_ma > self.slow_ma and self.data.close > self.long_ma
            # print(f"Date: {self.datas[0].datetime.date(0)}, Buy Signal Condition: {condition}")
            if condition:
                print(f"BUY Signal at {self.datas[0].datetime.date(0)} - Price: {self.data.close[0]}")
                self.buy_price = self.data.close[0]
                self.buy(size=0.3)
                print(f"  -> Bought at price {self.buy_price}")
        else:  # 持仓中
            current_price = self.data.close[0]
            change = (current_price - self.buy_price) / self.buy_price
            # print(f"Date: {self.datas[0].datetime.date(0)}, Holding, Change: {change:.2%}")

            # 加仓
            if change >= self.p.pyramid_add and not self.added_once:
                print(f"ADD 1 at {self.datas[0].datetime.date(0)} - Price: {current_price}")
                self.buy(size=0.25)
                self.added_once = True
            elif change >= 2 * self.p.pyramid_add and not self.added_twice:
                print(f"ADD 2 at {self.datas[0].datetime.date(0)} - Price: {current_price}")
                self.buy(size=0.25)
                self.added_twice = True

            # 止损
            stop_loss_condition = current_price < self.buy_price - self.p.stop_loss_atr * self.atr[0]
            # print(f"Date: {self.datas[0].datetime.date(0)}, Stop Loss Condition: {stop_loss_condition}")
            if stop_loss_condition:
                print(f"STOP LOSS at {self.datas[0].datetime.date(0)} - Price: {current_price}")
                self.close()
                self.reset_flags()

            # 止盈
            tp1_condition = change >= self.p.take_profit_1 and self.position.size > 0
            tp2_condition = change >= self.p.take_profit_2 and self.position.size > 0
            # print(f"Date: {self.datas[0].datetime.date(0)}, TP1 Condition: {tp1_condition}, TP2 Condition: {tp2_condition}")
            if tp1_condition:
                print(f"TAKE PROFIT 1 at {self.datas[0].datetime.date(0)} - Price: {current_price}")
                self.sell(size=self.position.size * 0.5)
            if tp2_condition:
                print(f"TAKE PROFIT 2 at {self.datas[0].datetime.date(0)} - Price: {current_price}")
                self.close()
                self.reset_flags()
        
        # 在每个 bar 结束时记录账户总价值
        current_value = self.broker.getvalue()
        self.daily_values.append(current_value)

    def reset_flags(self):
        self.added_once = False
        self.added_twice = False

# ================= AkShare 数据获取 =================
def get_data(symbol, start_date, end_date, source="A股", adjust="qfq"):
    import akshare as ak
    try:
        if source == "A股":
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust=adjust
            )
            # 打印实际列名以调试
            print("A股数据列名:", df.columns.tolist())
            # 重命名列
            df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }, inplace=True)
        elif source == "美股":
            df = ak.stock_us_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq"
            )
            # 打印实际列名以调试
            print("美股数据列名:", df.columns.tolist())
            # 重命名列（美股数据可能已有英文列名）
            df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }, inplace=True)

        # 检查必要列是否存在
        required_columns = ["date", "open", "close", "high", "low", "volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"数据缺少必要列: {missing_columns}")

        # 转换为日期格式并设为索引
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df
    except Exception as e:
        raise ValueError(f"获取 AkShare 数据失败: {str(e)}")

# ================= 回测执行函数 =================
def run_backtest(use_akshare=False, symbol=None, start_date=None, end_date=None, source='A股', adjust='qfq',
                 fast_ma=5, slow_ma=20, long_ma=200, atr_period=14, stop_loss_atr=2.0, 
                 take_profit_1=0.3, take_profit_2=0.5, pyramid_add=0.1,
                 use_custom_strategy=False, strategy_file=None, initial_cash=100000, file=None): # 新增参数
    
    # 初始化总结文本
    summary_md = "## 回测总结\n\n"
    
    try:
        if use_akshare:
            df = get_data(symbol, start_date, end_date, source, adjust)
        else:
            if not file:
                raise ValueError("未上传 CSV 文件")
            df = pd.read_csv(file.name)
            # 打印 CSV 列名以调试
            print("CSV 数据列名:", df.columns.tolist())
            # 检查日期列，支持常见变体
            date_columns = ["date", "Date", "日期", "time", "Time"]
            date_col = None
            for col in date_columns:
                if col in df.columns:
                    date_col = col
                    break
            if not date_col:
                raise ValueError(f"CSV 文件缺少日期列，期望包含以下之一: {date_columns}")
            # 重命名日期列
            df.rename(columns={date_col: "date"}, inplace=True)
            # 检查其他必要列
            required_columns = ["date", "open", "close", "high", "low", "volume"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"CSV 文件缺少必要列: {missing_columns}")
            # 转换为日期格式并设为索引
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

        # 记录每日股价到日志文件
        try:
            log_file_path = "daily_prices.log"
            df.to_csv(log_file_path)
            print(f"成功将每日股价数据记录到 {log_file_path}")
        except Exception as log_e:
            print(f"记录股价日志失败: {log_e}")

        # 计算买入并持有收益率
        initial_price = df["close"].iloc[0]
        buy_hold_returns = (df["close"] - initial_price) / initial_price

        # 转换为 Backtrader 数据格式
        data = bt.feeds.PandasData(dataname=df)

        cerebro = bt.Cerebro()
        cerebro.adddata(data)
        
        # 确定要使用的策略类和参数
        strategy_class = DualMAATRStrategy # 默认策略
        strategy_params = {} # 默认为空，使用策略类自己的默认参数
        
        if use_custom_strategy and strategy_file:
            # 尝试动态导入用户上传的策略
            try:
                # gr.File 上传的文件内容通常保存在一个临时文件中，其路径可以通过 .name 访问
                # 我们直接使用这个路径进行导入
                if hasattr(strategy_file, 'name'):
                    strategy_file_path = strategy_file.name  # Gradio-like file object
                else:
                    strategy_file_path = strategy_file  # Assumes it's a string path

                if not strategy_file_path:
                     raise ValueError("策略文件路径无效。")
                print(f"尝试加载策略文件: {strategy_file_path}")
                
                # 使用 importlib 动态导入上传的 .py 文件
                import sys
                module_name = "custom_strategy_module"
                spec = importlib.util.spec_from_file_location(module_name, strategy_file_path)
                if spec is None:
                    raise ValueError(f"无法从文件 {strategy_file_path} 创建模块规范。")
                    
                custom_module = importlib.util.module_from_spec(spec)
                if custom_module is None:
                    raise ValueError(f"无法从规范创建模块 {strategy_file_path}。")
                
                # 关键步骤：将新创建的模块添加到 sys.modules 中
                # 这样 backtrader 在内部查找时才能找到它
                sys.modules[module_name] = custom_module
                
                # 执行模块，使其内部的类和函数被定义
                spec.loader.exec_module(custom_module)
                
                # 从导入的模块中获取策略类 (约定类名为 CustomStrategy)
                if hasattr(custom_module, 'CustomStrategy'):
                    strategy_class = getattr(custom_module, 'CustomStrategy')
                    print(f"成功加载自定义策略: {strategy_class.__name__}")
                    # 如果需要传递参数给自定义策略，这里可以处理
                    # 但为了简化，我们假设自定义策略在定义时已包含所需参数
                    # strategy_params = {...} 
                else:
                    # 清理：如果加载失败，从 sys.modules 中移除
                    if module_name in sys.modules:
                        del sys.modules[module_name]
                    raise ValueError("上传的 .py 文件中未找到名为 'CustomStrategy' 的类。")

            except Exception as e:
                raise ValueError(f"加载自定义策略文件失败: {str(e)}")
        else:
            # 使用默认策略并传递滑块参数
            strategy_params = dict(
                fast_ma=fast_ma,
                slow_ma=slow_ma,
                long_ma=long_ma,
                atr_period=atr_period,
                stop_loss_atr=stop_loss_atr,
                take_profit_1=take_profit_1,
                take_profit_2=take_profit_2,
                pyramid_add=pyramid_add
            )
            print(f"使用默认策略: {strategy_class.__name__} with params {strategy_params}")


        # 添加策略
        cerebro.addstrategy(strategy_class, **strategy_params)
        cerebro.broker.set_cash(initial_cash) # 使用用户输入的本金
        initial_value = cerebro.broker.getvalue()

        # 运行回测
        strategies = cerebro.run() # 运行并获取策略实例列表
        final_value = cerebro.broker.getvalue()
        
        # 从策略实例获取信息
        strategy_instance = strategies[0]
        
        # --- 计算指标 ---
        total_return = final_value - initial_value
        total_return_pct = (final_value / initial_value - 1) * 100
        
        # 年化收益率
        start_dt = df.index[0]
        end_dt = df.index[-1]
        # print(f"Start Date: {start_dt}, End Date: {end_dt}") # Debug
        delta = end_dt - start_dt
        years = delta.days / 365.25
        # print(f"Delta Days: {delta.days}, Years: {years}") # Debug
        annualized_return = (((final_value / initial_value) ** (1 / years)) - 1) * 100 if years > 0 else 0

        # 从策略实例获取交易记录和每日价值
        completed_trades = getattr(strategy_instance, 'completed_trades', [])
        strategy_values = getattr(strategy_instance, 'daily_values', [])
        
        # --- 更稳健地计算交易指标 ---
        # 统计所有买卖订单作为交易次数
        total_trades = len([t for t in completed_trades if t['type'] in ['BUY', 'SELL']])
        
        # 简化处理：胜率和 Profit Factor 需要更复杂的逻辑（例如跟踪每笔完整交易的盈亏）
        # 这里暂时只显示总交易次数和基于账户价值的总收益
        # 暂时将胜率和 Profit Factor 显示为 "N/A" 或 "需要 Analyzer"
        # 总盈利和总亏损基于最终账户价值相对于初始价值的变化
        win_rate = "N/A (需要 TradeAnalyzer)"
        profit_factor = "N/A (需要 TradeAnalyzer)"
        # 如果最终价值高于初始价值，则认为是盈利，否则是亏损
        total_profit = max(0, total_return) 
        total_loss = abs(min(0, total_return))

        # --- 构造总结文本 ---
        if abs(final_value - initial_value) < 1e-6: # 检查是否存在交易活动
            summary_md += "- **<font color='red'>注意：策略在回测期间没有进行任何交易。</font>**\n"
        summary_md += f"- **总收益**: {total_return:.2f} ({total_return_pct:.2f}%)\n"
        summary_md += f"- **年化收益率**: {annualized_return:.2f}%\n"
        summary_md += f"- **总交易次数**: {total_trades}\n"
        summary_md += f"- **胜率**: {win_rate}\n"
        summary_md += f"- **Profit Factor**: {profit_factor}\n"
        summary_md += f"- **总盈利 (估算)**: {total_profit:.2f}\n"
        summary_md += f"- **总亏损 (估算)**: {total_loss:.2f}\n"

        print(f"\n--- Performance Metrics ---")
        print(f"Initial Value: {initial_value:.2f}")
        print(f"Final Value: {final_value:.2f}")
        print(f"Total Return: {total_return:.2f} ({total_return_pct:.2f}%)")
        print(f"Annualized Return: {annualized_return:.2f}%")
        print(f"Total Trades: {total_trades}")
        # print(f"Winning Trades: {winning_trades}") # 变量已移除
        print(f"Win Rate: {win_rate}")
        print(f"Profit Factor: {profit_factor}")
        print(f"Total Profit (Est.): {total_profit:.2f}")
        print(f"Total Loss (Est.): {total_loss:.2f}")
        print(f"--- End Metrics ---\n")

        # --- 绘图 ---
        # 确保策略收益率长度与数据索引一致
        # 先检查strategy_values的类型，确保它是列表
        if isinstance(strategy_values, dict):
            # 如果是字典，转换为列表形式
            strategy_values_list = []
            for date in df.index:
                if date in strategy_values:
                    # 假设字典中的值包含账户价值信息
                    value_data = strategy_values[date]
                    if isinstance(value_data, dict) and 'portfolio_value' in value_data:
                        strategy_values_list.append(value_data['portfolio_value'])
                    elif isinstance(value_data, (int, float)):
                        strategy_values_list.append(value_data)
                    else:
                        strategy_values_list.append(np.nan)
                else:
                    strategy_values_list.append(np.nan)
            strategy_values = strategy_values_list
        elif not isinstance(strategy_values, list):
            # 如果既不是字典也不是列表，初始化为空列表
            strategy_values = []
            
        if len(strategy_values) != len(df):
             print(f"Warning: Length mismatch. Strategy returns: {len(strategy_values)}, DataFrame: {len(df)}")
             # 如果长度不匹配，我们简单地截断或填充。这里假设策略从第一天开始记录。
             if len(strategy_values) > len(df):
                  strategy_values = strategy_values[:len(df)]
             else:
                  padding_length = len(df) - len(strategy_values)
                  strategy_values = [np.nan] * padding_length + strategy_values
                 
        # Calculate strategy returns based on the initial value
        strategy_returns = [(value - initial_value) / initial_value for value in strategy_values]

        # 检查是否有有效的策略收益率数据
        if all(np.isnan(r) for r in strategy_returns):
            print("Warning: All strategy returns are NaN. The plot will likely show only the Buy & Hold line.")
            
        # 计算胜率 (用于图表标题，这个计算方式本身可能有问题，但不影响绘图)
        win_rate_chart = np.nan
        if len(strategy_returns) == len(buy_hold_returns):
            win_rate_chart = np.mean(np.array(strategy_returns) > np.array(buy_hold_returns)) * 100
        else:
            print("Warning: Cannot calculate win rate for chart title due to length mismatch.")

        # 绘图
        plt.figure(figsize=(10, 6))
        plt.plot(df.index, buy_hold_returns, label="Buy & Hold Returns", color="blue")
        plt.plot(df.index, strategy_returns, label="Strategy Returns", color="red", linewidth=2.0)
        plt.title(f"Returns Comparison ({symbol}) - Final Portfolio Value: {final_value:.2f}, Win Rate: {win_rate_chart:.2f}%")
        plt.xlabel("Date")
        plt.ylabel("Returns")
        plt.legend()
        plt.grid()
        plt.tight_layout()

        return plt, summary_md # 返回图表和总结文本

    except Exception as e:
        error_msg = f"回测失败: {str(e)}"
        print(error_msg)
        summary_md += f"**错误**: {error_msg}\n"
        # 如果出错，返回一个空的图表和错误信息
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, 'Error occurred during backtest', ha='center', va='center', transform=ax.transAxes)
        ax.set_title('Backtest Error')
        return fig, summary_md
    except Exception as e:
        raise ValueError(f"回测失败: {str(e)}")

import tempfile
import importlib.util

# ================= Gradio GUI =================
with gr.Blocks() as demo:
    gr.Markdown("# 📈 回测 GUI (支持 A股 / 美股 数据源)")

    with gr.Row():
        use_akshare = gr.Checkbox(label="使用 AkShare 数据", value=False)
        source = gr.Dropdown(["A股", "美股"], label="数据源", value="A股")
        symbol = gr.Textbox(label="股票代码", value="000001")
        adjust = gr.Dropdown(["", "qfq", "hfq"], label="复权方式 (仅A股)", value="qfq")
        start_date = gr.Textbox(label="开始日期 (YYYY-MM-DD)", value="2021-01-01")
        end_date = gr.Textbox(label="结束日期 (YYYY-MM-DD)", value="2023-01-01")
        file = gr.File(label="上传 CSV 数据", file_types=[".csv"])
        initial_cash = gr.Number(label="初始本金", value=100000, precision=2) # 新增本金输入框

    with gr.Row():
        use_custom_strategy = gr.Checkbox(label="使用自定义策略文件 (.py)", value=False)
        strategy_file = gr.File(label="上传自定义策略 (.py)", file_types=[".py"])
        
    # 默认策略参数滑块 (默认显示，上传策略时隐藏)
    default_params = gr.Group(visible=True) # 创建一个组来方便控制显示/隐藏
    with default_params:
        with gr.Row():
            fast_ma = gr.Slider(3, 20, 5, step=1, label="快均线")
            slow_ma = gr.Slider(10, 60, 20, step=1, label="慢均线")
            long_ma = gr.Slider(100, 250, 200, step=10, label="长均线")
            atr_period = gr.Slider(5, 30, 14, step=1, label="ATR 周期")

        with gr.Row():
            stop_loss_atr = gr.Slider(1.0, 5.0, 2.0, step=0.1, label="止损 ATR 倍数")
            take_profit_1 = gr.Slider(0.1, 0.5, 0.3, step=0.05, label="止盈 1 (比例)")
            take_profit_2 = gr.Slider(0.2, 1.0, 0.5, step=0.05, label="止盈 2 (比例)")
            pyramid_add = gr.Slider(0.05, 0.2, 0.1, step=0.01, label="加仓阈值 (比例)")

    run_btn = gr.Button("运行回测")
    output_plot = gr.Plot()
    summary_text = gr.Markdown() # 用于显示总结文本的新组件

    # 定义交互：勾选"使用自定义策略"时，隐藏默认参数滑块
    def toggle_params_visibility(use_custom):
        return gr.update(visible=not use_custom)
        
    use_custom_strategy.change(fn=toggle_params_visibility, inputs=use_custom_strategy, outputs=default_params)

    run_btn.click(run_backtest,
                  inputs=[file, use_akshare, symbol, start_date, end_date, source, adjust,
                          fast_ma, slow_ma, long_ma, atr_period, stop_loss_atr, take_profit_1, take_profit_2, pyramid_add,
                          use_custom_strategy, strategy_file, initial_cash], # 新增输入
                  outputs=[output_plot, summary_text]) # 修改输出

if __name__ == "__main__":
    demo.launch(server_port=7863)  # 使用不同端口避免冲突
