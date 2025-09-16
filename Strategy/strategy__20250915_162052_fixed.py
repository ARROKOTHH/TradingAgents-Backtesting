import backtrader as bt
import math

class CustomStrategy(bt.Strategy):
    """
    稀土龙头趋势回调策略 (Rare Earth Leader Trend Pullback Strategy)

    - 策略风格: 趋势跟踪与回调入场 (Trend Following with Pullback Entry)
    - 风险偏好: 中等 (Moderate)

    核心逻辑:
    1.  **趋势过滤**: 仅当价格在长期EMA之上且EMA本身在上升时，才考虑交易。
    2.  **入场信号 (二选一)**:
        - Plan A: 在上升趋势中，等待RSI回调至相对低位后再次上穿时买入。
        - Plan B: 在上升趋势中，等待价格下探中期EMA支撑位后收回时买入。
    3.  **出场逻辑**: 使用基于ATR的追踪止损来让利润奔跑并控制下行风险。
    4.  **风险管理**: 采用固定风险百分比模型来确定每次交易的仓位大小。
    """
    params = (
        # 1. 趋势过滤器参数
        ('trend_ema_period', 200),   # 用于定义长期趋势的EMA周期

        # 2. 入场信号参数 (Plan A)
        ('entry_rsi_period', 14),    # RSI指标周期
        ('entry_rsi_low', 40),       # RSI回调买入的阈值

        # 3. 入场信号参数 (Plan B)
        ('entry_ema_short_period', 50), # 用于Plan B的短期支撑EMA周期

        # 4. 出场逻辑参数
        ('exit_atr_period', 14),     # ATR周期，用于计算波动率
        ('exit_atr_multiplier', 2.5),# ATR乘数，用于设定追踪止损的距离

        # 5. 风险管理参数
        ('risk_percent_per_trade', 0.02), # 每笔交易承担的账户总资金风险百分比 (2%)
    )

    def __init__(self):
        """策略初始化"""
        # 必须在__init__中初始化 daily_values
        self.daily_values = []

        # 引用数据线以便于访问
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # 1. 趋势过滤器指标
        self.ema_long = bt.indicators.ExponentialMovingAverage(
            self.datas[0], period=self.p.trend_ema_period)

        # 2. 入场信号指标
        # Plan A: RSI
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.entry_rsi_period)
        self.rsi_crossup = bt.indicators.CrossUp(self.rsi, self.p.entry_rsi_low)

        # Plan B: 短期EMA
        self.ema_short = bt.indicators.ExponentialMovingAverage(
            self.datas[0], period=self.p.entry_ema_short_period)

        # 3. 出场逻辑指标
        self.atr = bt.indicators.AverageTrueRange(
            self.datas[0], period=self.p.exit_atr_period)

        # 状态变量
        self.order = None  # 跟踪挂单
        self.trailing_stop_price = 0.0 # 追踪止损价格

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/接受，无需操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # print(
                #     f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                #     f'Cost: {order.executed.value:.2f}, '
                #     f'Comm: {order.executed.comm:.2f}'
                # )
                pass
            elif order.issell():
                # print(
                #     f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                #     f'Cost: {order.executed.value:.2f}, '
                #     f'Comm: {order.executed.comm:.2f}'
                # )
                pass
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # print(f'Order Canceled/Margin/Rejected: {order.Status[order.status]}')
            pass

        self.order = None

    def next(self):
        """策略核心逻辑，每个K线调用一次"""
        # --- 修复: 增加数据预热期检查 ---
        # 错误 "array assignment index out of range" 通常是因为指标需要一定数量的数据才能计算出有效值。
        # 策略中使用了最长周期为200的EMA，并且逻辑中比较了 self.ema_long[0] 和 self.ema_long[-1]，
        # 这意味着需要至少201个数据点才能安全执行。
        # 因此，在策略开始时，我们跳过没有足够数据的K线。
        if len(self) <= self.p.trend_ema_period:
            return

        # 诊断日志：打印每日关键指标
        print(
            f"Date: {self.datas[0].datetime.date(0)}, "
            f"Close: {self.dataclose[0]:.2f}, "
            f"Long EMA({self.p.trend_ema_period}): {self.ema_long[0]:.2f}, "
            f"Short EMA({self.p.entry_ema_short_period}): {self.ema_short[0]:.2f}, "
            f"RSI({self.p.entry_rsi_period}): {self.rsi[0]:.2f}, "
            f"ATR({self.p.exit_atr_period}): {self.atr[0]:.2f}"
        )

        # --- 出场逻辑 ---
        if self.position:
            # 计算新的追踪止损价格
            new_stop_price = self.dataclose[0] - self.atr[0] * self.p.exit_atr_multiplier
            
            # 止损位只上移，不下调
            self.trailing_stop_price = max(self.trailing_stop_price, new_stop_price)

            # 检查是否触发追踪止损
            if self.datalow[0] < self.trailing_stop_price:
                print(
                    f"--- SELL SIGNAL (Trailing Stop) --- \n"
                    f"Date: {self.datas[0].datetime.date(0)}, "
                    f"Low Price {self.datalow[0]:.2f} < Trailing Stop Price {self.trailing_stop_price:.2f}. Closing position."
                )
                self.close() # 市价平仓
                self.trailing_stop_price = 0.0 # 重置止损价

        # --- 入场逻辑 ---
        elif not self.position:
            # 1. 趋势过滤器
            is_long_trend = self.dataclose[0] > self.ema_long[0]
            is_trend_healthy = self.ema_long[0] > self.ema_long[-1]
            trend_filter_passed = is_long_trend and is_trend_healthy

            # 2. 入场信号
            # Plan A: RSI 回调上穿
            plan_a_triggered = self.rsi_crossup[0] > 0

            # Plan B: 动态支撑位反弹 (下探回升)
            plan_b_triggered = self.datalow[0] < self.ema_short[0] and self.dataclose[0] > self.ema_short[0]

            # 综合判断
            buy_condition = trend_filter_passed and (plan_a_triggered or plan_b_triggered)

            # 诊断日志：打印入场条件判断结果
            print(
                f"Buy Condition Check: Trend Filter Passed: {trend_filter_passed} "
                f"(Price > EMA200: {is_long_trend}, EMA200 Rising: {is_trend_healthy}), "
                f"Plan A (RSI CrossUp): {plan_a_triggered}, "
                f"Plan B (EMA50 Reclaim): {plan_b_triggered} "
                f"==> Final Buy Decision: {buy_condition}"
            )

            if buy_condition:
                # 3. 风险管理与下单
                # 计算初始止损价
                initial_stop_price = self.dataclose[0] - self.atr[0] * self.p.exit_atr_multiplier
                
                # 计算单股风险
                risk_per_share = self.dataclose[0] - initial_stop_price
                if risk_per_share <= 0: # 避免除以零或负数
                    return

                # 计算总风险金额
                total_risk_amount = self.broker.getvalue() * self.p.risk_percent_per_trade
                
                # 计算仓位大小 (股数)
                size = math.floor(total_risk_amount / risk_per_share)

                if size > 0:
                    print(
                        f"--- BUY SIGNAL --- \n"
                        f"Date: {self.datas[0].datetime.date(0)}, "
                        f"Buy Price: {self.dataclose[0]:.2f}, "
                        f"Calculated Size: {size}, "
                        f"Initial Stop Price: {initial_stop_price:.2f}"
                    )
                    self.buy(size=size)
                    # 设置初始追踪止损价
                    self.trailing_stop_price = initial_stop_price

        # 必须在next方法末尾处添加
        self.daily_values.append(self.broker.getvalue())