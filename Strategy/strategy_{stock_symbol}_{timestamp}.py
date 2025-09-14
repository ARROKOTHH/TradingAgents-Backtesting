import backtrader as bt
import datetime

class CustomStrategy(bt.Strategy):
    """
    策略摘要:
    本策略是一个结合趋势过滤、回调入场和信号确认的多指标共振系统。
    1.  **趋势判断**: 使用长期指数移动平均线（EMA）作为主要趋势过滤器。只有当价格位于长期EMA之上时，才考虑做多。
    2.  **入场时机 (回调)**: 在确认上涨趋势后，等待相对强弱指数（RSI）从高位回落到指定阈值以下，识别为短期回调，作为潜在入场机会。
    3.  **入场确认 (动量)**: 在回调信号出现后，等待MACD指标的快线（DIF）上穿慢线（DEA），即出现“金叉”，作为最终的买入确认信号。
    4.  **离场规则**: 采用单一的追踪止损机制。入场后，设置一个基于百分比的追踪止损订单，该订单既能锁定利润，也能作为初始的止损保护。
    5.  **资金管理**: 每次交易投入总权益的固定百分比。
    """
    
    # 默认参数（稳健型）
    params = (
        ('long_ema_period', 100),
        ('rsi_period', 14),
        ('rsi_pullback_level', 55), # RSI回调至此水平以下
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
        ('trailing_stop_pct', 0.07), # 追踪止损百分比
        ('sizing_pct', 0.50), # 仓位大小（占总资金百分比）
        ('risk_appetite', '{st.session_state.final_risk_appetite}'), # 风险偏好
    )

    def __init__(self):
        """
        策略初始化
        """
        # 1. 根据风险偏好动态调整参数 (必须在__init__最开始)
        if self.p.risk_appetite == '激进型':
            self.p.long_ema_period = 50
            self.p.rsi_pullback_level = 65
            self.p.trailing_stop_pct = 0.05 # 更紧的止损
            self.p.sizing_pct = 0.90       # 更大的仓位
        elif self.p.risk_appetite == '保守型':
            self.p.long_ema_period = 200
            self.p.rsi_pullback_level = 45
            self.p.trailing_stop_pct = 0.10 # 更宽的止损
            self.p.sizing_pct = 0.20       # 更小的仓位
        
        # 2. 初始化指标
        self.long_ema = bt.indicators.EMA(self.data.close, period=self.p.long_ema_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.lines.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.lines.macd_fast,
            period_me2=self.p.lines.macd_slow,
            period_signal=self.p.lines.macd_signal
        )
        # 使用内置交叉指标来检测MACD金叉
        self.lines.macd_crossover = bt.indicators.CrossOver(self.lines.macd.lines.macd, self.lines.macd.lines.signal)

        # 3. 状态管理变量
        self.order = None
        self.waiting_for_confirmation = False # 状态：是否已观察到回调并等待MACD确认

        # 4. 每日市值记录
        self.daily_values = []

    def log(self, txt, dt=None):
        """
        日志记录函数
        """
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # 买入成功后，立即设置追踪止损单
                self.order = self.sell(exectype=bt.Order.StopTrail, trailpercent=self.p.trailing_stop_pct)
                self.log(f'Trailing Stop Placed at {self.p.trailing_stop_pct*100:.2f}%')

            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')

        # 重置订单跟踪器
        if not order.alive():
            self.order = None

    def next(self):
        """
        策略核心逻辑
        """
        # 诊断日志：打印每日关键指标
        print(
            f"Date: {self.datas[0].datetime.date(0)}, "
            f"Close: {self.data.close[0]:.2f}, "
            f"Long EMA({self.p.long_ema_period}): {self.long_ema[0]:.2f}, "
            f"RSI({self.p.rsi_period}): {self.rsi[0]:.2f}, "
            f"MACD: {self.lines.macd.lines.macd[0]:.2f}, "
            f"Signal: {self.lines.macd.lines.signal[0]:.2f}, "
            f"MACD Cross: {self.lines.macd_crossover[0]}"
        )

        # 如果有挂单，则不进行任何操作
        if self.order:
            self.daily_values.append(self.broker.getvalue())
            return

        # 检查是否持有仓位
        if not self.position:
            # === 入场逻辑 ===
            
            # 条件1: 趋势判断 - 价格在长期EMA之上
            is_uptrend = self.data.close[0] > self.long_ema[0]
            
            # 条件2: 回调信号 - RSI回落到指定水平之下
            is_pullback = self.rsi[0] < self.p.rsi_pullback_level
            
            # 条件3: 确认信号 - MACD金叉
            is_confirmed = self.lines.macd_crossover[0] > 0

            # 状态机逻辑：
            # 步骤A: 如果处于上升趋势且发生回调，则进入“等待确认”状态
            if is_uptrend and is_pullback:
                self.waiting_for_confirmation = True
            
            # 步骤B: 如果处于“等待确认”状态，并且趋势仍然向上，同时MACD发生金叉，则触发买入
            buy_condition = self.waiting_for_confirmation and is_uptrend and is_confirmed

            # 诊断日志：打印入场条件判断结果
            print(
                f"Buy Condition Check: is_uptrend={is_uptrend}, "
                f"is_pullback={is_pullback} (sets waiting flag), "
                f"waiting_for_confirmation={self.waiting_for_confirmation}, "
                f"is_confirmed={is_confirmed} -> Final Buy Signal: {buy_condition}"
            )

            if buy_condition:
                # 计算仓位大小
                cash = self.broker.get_cash()
                target_value = cash * self.p.sizing_pct
                size = target_value / self.data.close[0]
                
                self.log(f'BUY CREATE, Size: {size:.2f}, Price: {self.data.close[0]:.2f}')
                self.order = self.buy(size=size)
                
                # 重置状态，避免连续买入
                self.waiting_for_confirmation = False
        
        else:
            # === 离场逻辑 ===
            # 持仓时，离场逻辑完全由`notify_order`中设置的追踪止损单管理
            # 此处无需额外代码
            pass
        
        # 记录每日组合净值
        self.daily_values.append(self.broker.getvalue())

    def stop(self):
        """
        策略结束时调用
        """
        self.log(f'(Risk Appetite: {self.p.risk_appetite}) Final Portfolio Value: {self.broker.getvalue():.2f}')