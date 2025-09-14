import backtrader as bt
import math

class CustomStrategy(bt.Strategy):
    """
    Backtrader Strategy: 北方稀土(600111) 趋势跟踪与回调买入策略
    - 策略风格: 趋势跟踪与回调买入 (Trend Following with Pullback Entry)
    - 风险偏好: 中等 (Moderate)
    - 核心逻辑:
        1. 趋势过滤器: 仅在长期均线确认的上升趋势中寻找交易机会。
        2. 双重入场信号 (Plan A or Plan B):
            - Plan A: 捕捉强势股回调结束的信号。要求近期RSI曾进入超买区，随后MACD柱状图由负转正。
            - Plan B: 捕捉价格在短期均线获得支撑反弹的信号。要求K线下影线触及EMA支撑位后，收盘价收回均线之上。
        3. 动态止损: 使用ATR追踪止损来保护利润并让盈利奔跑。
        4. 风险管理: 采用固定风险百分比模型来确定每笔交易的仓位大小。
    """
    params = (
        # 风险偏好 (由外部传入，此处为占位符)
        ('risk_appetite', '中等'), 

        # 趋势过滤器参数
        ('p_trend_period', 60),  # 用于定义长期趋势的移动平均线周期

        # 入场信号 Plan A 参数
        ('p_macd_fast', 12),     # MACD 快线周期
        ('p_macd_slow', 26),     # MACD 慢线周期
        ('p_macd_signal', 9),      # MACD 信号线周期
        ('p_rsi_period', 14),    # RSI 周期
        ('p_rsi_overbought', 70),# RSI 超买阈值
        ('p_rsi_lookback', 15),  # RSI超买状态的回看周期

        # 入场信号 Plan B 参数
        ('p_ema_pullback', 20),  # 用于回调支撑的短期EMA周期

        # 出场逻辑参数
        ('p_atr_period', 14),    # ATR周期
        ('p_atr_multiplier', 2.5), # ATR追踪止损的倍数

        # 风险管理参数
        ('p_risk_percent', 0.02), # 每笔交易承担的账户总资金风险百分比 (2%)
    )

    def __init__(self):
        """策略初始化"""
        # 1. 根据最终风险偏好动态调整参数 (必须在__init__最开始)
        # 对于“中等”风险，我们使用默认参数。如果需要，可在此处添加逻辑。
        # 例如: if self.p.risk_appetite == '激进型': self.p.p_atr_multiplier = 2.0
        # 这里我们保持默认值，因为它们已经符合中等风险的设定。

        # 2. 初始化指标
        # 趋势过滤器
        self.trend_sma = bt.ind.SMA(self.data.close, period=self.p.p_trend_period)
        
        # 入场信号 Plan A
        # FIX: Renamed indicator from self.lines.macd to self.lines.macd to follow backtrader best practices
        # and resolve the AttributeError.
        self.lines.macd = bt.ind.MACD(
            self.data.close,
            period_me1=self.p.p_macd_fast,
            period_me2=self.p.p_macd_slow,
            period_signal=self.p.p_macd_signal
        )
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.p_rsi_period)

        # 入场信号 Plan B
        self.ema_pullback = bt.ind.EMA(self.data.close, period=self.p.p_ema_pullback)

        # 出场和风险管理
        self.atr = bt.ind.ATR(self.data, period=self.p.p_atr_period)

        # 3. 状态变量
        self.order = None
        self.stop_price = None
        
        # 4. 必须的每日价值记录
        self.daily_values = []

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # 买入成功后，设置初始止损价
                self.stop_price = self.data.close[0] - self.p.p_atr_multiplier * self.atr[0]
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        """交易结果通知"""
        if not trade.isclosed:
            return
        self.log(f'OPERATION PROFIT, GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')

    def next(self):
        """策略核心逻辑"""
        # 1. 强制诊断日志：打印每日关键指标
        log_date = self.datas[0].datetime.date(0)
        log_close = self.data.close[0]
        log_trend_sma = self.trend_sma[0]
        # FIX: Changed self.lines.macd.lines.histo to self.lines.macd.lines.histo
        log_macd_hist = self.lines.macd.lines.histo[0]
        log_rsi = self.rsi[0]
        log_ema_pullback = self.ema_pullback[0]
        log_atr = self.atr[0]
        
        print(f"Date: {log_date}, Close: {log_close:.2f}, TrendSMA({self.p.p_trend_period}): {log_trend_sma:.2f}, "
              f"MACD Hist: {log_macd_hist:.4f}, RSI({self.p.p_rsi_period}): {log_rsi:.2f}, "
              f"EMAPullback({self.p.p_ema_pullback}): {log_ema_pullback:.2f}, ATR({self.p.p_atr_period}): {log_atr:.2f}")

        # 2. 如果有挂单，则不进行任何操作
        if self.order:
            return

        # 3. 持仓管理 (出场逻辑)
        if self.position:
            # ATR 追踪止损逻辑
            new_stop_price = self.data.close[0] - self.p.p_atr_multiplier * self.atr[0]
            # 止损位只上移，不下调
            self.stop_price = max(self.stop_price, new_stop_price)
            
            # 检查是否触发止损
            if self.data.close[0] < self.stop_price:
                self.log(f'TRAILING STOP HIT! Close: {self.data.close[0]:.2f} < Stop Price: {self.stop_price:.2f}')
                self.order = self.close()
        
        # 4. 空仓管理 (入场逻辑)
        elif not self.position:
            # 4.1 趋势过滤器
            is_trend_up = self.data.close[0] > self.trend_sma[0] and self.trend_sma[0] > self.trend_sma[-1]
            
            if is_trend_up:
                # 4.2 入场信号 Plan A: 基于指标共振的回调结束信号
                # 条件1: 最近N个周期内RSI曾进入超买区
                rsi_recently_overbought = False
                for i in range(-1, -self.p.p_rsi_lookback - 1, -1):
                    if self.rsi[i] > self.p.p_rsi_overbought:
                        rsi_recently_overbought = True
                        break
                # 条件2: MACD柱状图由负转正 (金叉)
                # FIX: Changed self.lines.macd.lines.histo to self.lines.macd.lines.histo
                macd_cross_up = self.lines.macd.lines.histo[-1] <= 0 and self.lines.macd.lines.histo[0] > 0
                buy_signal_A = rsi_recently_overbought and macd_cross_up

                # 4.3 入场信号 Plan B: 基于动态支撑位的价格行为信号
                # 条件: K线最低价下穿EMA，但收盘价收回EMA之上
                buy_signal_B = self.data.low[0] < self.ema_pullback[0] and self.data.close[0] > self.ema_pullback[0]

                # 4.4 最终入场条件
                final_buy_condition = buy_signal_A or buy_signal_B
                
                # 强制诊断日志：打印入场条件判断结果
                print(f"  - Trend Filter UP: {is_trend_up}")
                print(f"  - Plan A (RSI Overbought Recently & MACD Cross): {buy_signal_A} (RSI Recent OB: {rsi_recently_overbought}, MACD Cross: {macd_cross_up})")
                print(f"  - Plan B (EMA Reclaim): {buy_signal_B}")
                print(f"  - Final Buy Condition Met: {final_buy_condition}")

                if final_buy_condition:
                    # 4.5 风险管理与下单
                    # 计算初始止损位
                    initial_stop = self.data.close[0] - self.p.p_atr_multiplier * self.atr[0]
                    risk_per_share = self.data.close[0] - initial_stop

                    if risk_per_share > 0:
                        # 计算仓位大小
                        risk_amount = self.broker.getvalue() * self.p.p_risk_percent
                        size = math.floor(risk_amount / risk_per_share)
                        
                        if size > 0:
                            self.log(f'BUY CREATE, Size: {size}, Close: {self.data.close[0]:.2f}, Initial Stop: {initial_stop:.2f}')
                            self.order = self.buy(size=size)

        # 5. 必须的每日价值记录
        self.daily_values.append(self.broker.getvalue())

    def log(self, txt, dt=None):
        """日志记录函数"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def stop(self):
        """策略结束时调用"""
        self.log(f'(p_trend_period={self.p.p_trend_period}, p_atr_multiplier={self.p.p_atr_multiplier}) FINAL VALUE: {self.broker.getvalue():.2f}')