import backtrader as bt
import math

class CustomStrategy(bt.Strategy):
    """
    策略蓝图: 趋势跟踪下的回调买入 (Trend Following with Pullback Entry)
    - 趋势过滤器: 价格必须在长期EMA之上，且长期EMA本身在上升。
    - 入场信号 (Plan A): RSI从高位回调后，重新上穿中线。
    - 入场信号 (Plan B): 价格回调跌破短期EMA后，迅速重新站上。
    - 出场逻辑: ATR追踪止损，让利润奔跑。
    - 风险管理: 基于ATR和账户百分比计算仓位大小。
    """
    params = (
        # 1. 趋势过滤器参数
        ('ema_long_period', 200),   # 用于定义长期趋势的EMA周期

        # 2. 入场信号参数 (Plan A: RSI Pullback)
        ('rsi_period', 14),         # RSI计算周期
        ('rsi_high_level', 68),     # 定义近期强势区的RSI阈值
        ('rsi_pullback_level', 50), # RSI回调后重新走强的入场参考线

        # 3. 入场信号参数 (Plan B: MA Pullback)
        ('ema_short_period', 20),   # 用于定义短期动态支撑的EMA周期

        # 4. 出场逻辑参数
        ('atr_period', 14),         # ATR计算周期
        ('atr_multiplier', 2.5),    # ATR追踪止损的倍数

        # 5. 风险管理参数
        ('risk_percent', 0.02),     # 每笔交易承担的账户风险百分比 (2%)
    )

    def __init__(self):
        """策略初始化"""
        # 必须在 __init__ 的最开始，根据风险偏好调整参数
        # 对于 "中等" 风险偏好，我们使用默认参数，无需修改
        # if "{st.session_state.final_risk_appetite}" == '激进型':
        #     self.p.lines.atr_multiplier = 2.0
        #     self.p.risk_percent = 0.03
        # elif "{st.session_state.final_risk_appetite}" == '保守型':
        #     self.p.lines.atr_multiplier = 3.0
        #     self.p.risk_percent = 0.01

        # 初始化每日净值记录列表
        self.daily_values = []

        # 引用数据线
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # 1. 趋势过滤器指标
        self.lines.ema_long = bt.indicators.EMA(self.dataclose, period=self.p.lines.ema_long_period)

        # 2. 入场信号指标
        self.lines.ema_short = bt.indicators.EMA(self.dataclose, period=self.p.lines.ema_short_period)
        self.lines.rsi = bt.indicators.RSI(self.dataclose, period=self.p.lines.rsi_period)
        
        # 使用内置交叉指标
        self.lines.rsi_crossover = bt.indicators.CrossOver(self.lines.rsi, self.p.lines.rsi_pullback_level)
        self.ma_crossover = bt.indicators.CrossOver(self.dataclose, self.lines.ema_short)

        # 3. 出场和风控指标
        self.lines.atr = bt.indicators.ATR(self.datas[0], period=self.p.lines.atr_period)

        # 4. 状态变量
        self.trailing_stop_price = None
        self.order = None

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # 买入订单完成
                self.trailing_stop_price = order.executed.price - self.lines.atr[0] * self.p.lines.atr_multiplier
                print(
                    f'BUY EXECUTED --- Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}, '
                    f'Initial Stop: {self.trailing_stop_price:.2f}'
                )
            elif order.issell():
                # 卖出订单完成
                print(
                    f'SELL EXECUTED --- Price: {order.executed.price:.2f}, '
                    f'Size: {order.executed.size}, '
                    f'Profit: {order.executed.pnl:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                self.trailing_stop_price = None # 重置追踪止损价
            self.order = None # 重置订单引用
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'Order Canceled/Margin/Rejected: {order.Status[order.status]}')
            self.order = None

    def next(self):
        """策略核心逻辑"""
        # 强制诊断日志：打印每日关键指标
        print(
            f"Date: {self.datas[0].datetime.date(0)}, "
            f"Close: {self.dataclose[0]:.2f}, "
            f"Long EMA({self.p.lines.ema_long_period}): {self.lines.ema_long[0]:.2f}, "
            f"Short EMA({self.p.lines.ema_short_period}): {self.lines.ema_short[0]:.2f}, "
            f"RSI({self.p.lines.rsi_period}): {self.lines.rsi[0]:.2f}, "
            f"ATR({self.p.lines.atr_period}): {self.lines.atr[0]:.2f}"
        )

        # 如果有挂单，则不进行任何操作
        if self.order:
            return

        # --- 出场逻辑 ---
        if self.position:
            # 计算新的追踪止损价
            new_stop_price = self.dataclose[0] - self.lines.atr[0] * self.p.lines.atr_multiplier
            # 止损价只上移，不下降
            self.trailing_stop_price = max(self.trailing_stop_price, new_stop_price)
            
            print(f"Position Active --- Current Trailing Stop: {self.trailing_stop_price:.2f}")

            # 检查是否触发追踪止损
            if self.datalow[0] < self.trailing_stop_price:
                print(f"STOP TRIGGERED --- Low Price {self.datalow[0]:.2f} < Stop Price {self.trailing_stop_price:.2f}. Closing position.")
                self.order = self.close() # 平仓
        
        # --- 入场逻辑 ---
        elif not self.position:
            # 1. 趋势过滤器
            is_long_trend = self.dataclose[0] > self.lines.ema_long[0]
            is_ema_rising = self.lines.ema_long[0] > self.lines.ema_long[-1]
            trend_filter_passed = is_long_trend and is_ema_rising
            
            print(f"Trend Filter Check --- Price > Long EMA: {is_long_trend}, Long EMA Rising: {is_ema_rising}, Filter Passed: {trend_filter_passed}")

            if trend_filter_passed:
                # 2. 入场信号 (Plan A: RSI Pullback)
                recent_rsi_high = any(self.lines.rsi.get(ago=-i) > self.p.lines.rsi_high_level for i in range(1, 11))
                rsi_crossover_signal = self.lines.rsi_crossover[0] > 0
                plan_a_signal = recent_rsi_high and rsi_crossover_signal
                
                print(f"Plan A Check --- Recent RSI High: {recent_rsi_high}, RSI Crossover: {rsi_crossover_signal}, Signal: {plan_a_signal}")

                # 3. 入场信号 (Plan B: MA Pullback)
                ma_crossover_signal = self.ma_crossover[0] > 0
                plan_b_signal = ma_crossover_signal
                
                print(f"Plan B Check --- MA Crossover: {ma_crossover_signal}, Signal: {plan_b_signal}")

                # 4. 最终买入条件
                buy_condition = plan_a_signal or plan_b_signal
                print(f"Final Buy Condition Met: {buy_condition}")

                if buy_condition:
                    # 5. 风险管理和仓位计算
                    initial_stop = self.dataclose[0] - self.lines.atr[0] * self.p.lines.atr_multiplier
                    risk_per_share = self.dataclose[0] - initial_stop

                    if risk_per_share > 0:
                        risk_amount = self.broker.getvalue() * self.p.risk_percent
                        size = math.floor(risk_amount / risk_per_share)
                        
                        print(
                            f"BUY SIGNAL --- Sizing Calculation: "
                            f"Risk Amount: {risk_amount:.2f}, "
                            f"Risk Per Share: {risk_per_share:.2f}, "
                            f"Calculated Size: {size}"
                        )

                        if size > 0:
                            self.order = self.buy(size=size)
        
        # 必须在 next 方法的末尾处添加
        self.daily_values.append(self.broker.getvalue())