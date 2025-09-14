import backtrader as bt

class CustomStrategy(bt.Strategy):
    """
    交易策略蓝图: 趋势回调策略
    策略风格: 趋势跟踪下的回调买入策略 (Buy-the-Dip Trend Following Strategy)
    风险偏好: 中等 (Moderate)
    """
    params = (
        # 1. 趋势过滤器参数
        ('p_long_ma_period', 60),   # 长期均线周期，用于定义主趋势 (e.g., 季度线)

        # 2. 入场信号参数 (Plan A: 回调)
        ('p_short_ma_period', 20),  # 短期均线周期，用于识别回调支撑 (e.g., 月线)
        ('p_rsi_period', 14),       # RSI指标周期
        ('p_rsi_low', 40),          # RSI回调买入的阈值下限 (强势股回调通常不会太深)

        # 3. 入场信号参数 (Plan B: 动量突破)
        ('p_vol_ma_period', 20),    # 成交量均线周期
        ('p_vol_multiplier', 2.0),  # 成交量放大倍数

        # 4. 出场逻辑参数
        ('p_atr_period', 14),       # ATR周期，用于计算止损距离
        ('p_atr_multiplier', 2.5),  # ATR倍数，决定止损的宽松程度

        # 5. 风险管理参数
        ('p_risk_percent', 0.02),   # 每笔交易愿意承担的账户总资金风险百分比 (e.g., 2%)
    )

    def __init__(self):
        """
        策略初始化
        """
        # 必须在 __init__ 中初始化 self.daily_values
        self.daily_values = []

        # 引用数据线以便于访问
        self.dataclose = self.datas[0].close
        self.dataopen = self.datas[0].open
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume

        # 1. 趋势过滤器指标
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.dataclose, period=self.p.p_long_ma_period)

        # 2. 入场信号指标
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.dataclose, period=self.p.p_short_ma_period)
        # --- FIX: Correctly initialize RSI indicator ---
        self.rsi.lines.rsi = bt.indicators.RSI(
            self.dataclose, period=self.p.p_rsi_period)
        self.vol_ma = bt.indicators.SimpleMovingAverage(
            self.datavolume, period=self.p.p_vol_ma_period)
        
        # 使用CrossOver来精确捕捉上穿信号
        self.price_cross_short_ma = bt.indicators.CrossOver(
            self.dataclose, self.short_ma)

        # 3. 出场逻辑指标
        # --- FIX: Correctly initialize ATR indicator ---
        self.atr.lines.atr = bt.indicators.AverageTrueRange(
            self.datas[0], period=self.p.p_atr_period)

        # 4. 状态管理变量
        self.order = None
        self.stop_price = None
        self.buy_atr_value = None # 用于在订单成交后计算初始止损

    def log(self, txt, dt=None):
        """
        日志记录函数
        """
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交/已接受，不执行任何操作
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # --- FIX: Corrected and completed the log message ---
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                # --- ADD: Set initial stop loss after buy order is completed ---
                entry_price = order.executed.price
                stop_dist = self.buy_atr_value * self.p.p_atr_multiplier
                self.stop_price = entry_price - stop_dist
                self.log(f'Initial Stop Loss set at: {self.stop_price:.2f}')

            elif order.issell():
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                self.stop_price = None # Reset stop price on sell

            self.order = None # Reset order status

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')
            self.order = None

    def next(self):
        """
        策略核心逻辑
        """
        # 如果有挂单，不进行任何操作
        if self.order:
            return

        # --- 出场逻辑: ATR追踪止损 ---
        if self.position:
            # 计算新的追踪止损位
            new_stop_price = self.dataclose[0] - (self.atr.lines.atr[0] * self.p.p_atr_multiplier)
            # 止损位只上移，不下移
            self.stop_price = max(self.stop_price, new_stop_price)
            
            # 检查是否触发止损 (检查当日最低价是否跌破止损位)
            if self.datalow[0] < self.stop_price:
                self.log(f'TRAILING STOP HIT, Price: {self.datalow[0]:.2f}, Stop Price: {self.stop_price:.2f}')
                self.order = self.close()

        # --- 入场逻辑 ---
        if not self.position:
            # 1. 趋势过滤器
            is_uptrend = (self.dataclose[0] > self.long_ma[0] and 
                          self.long_ma[0] > self.long_ma[-1])

            if is_uptrend:
                # 2. 入场信号
                # Plan A: 回调企稳信号
                buy_signal_A = (self.price_cross_short_ma[0] > 0 and 
                                self.rsi.lines.rsi[0] > self.p.p_rsi_low)

                # Plan B: 放量突破信号
                is_bullish_candle = self.dataclose[0] > self.dataopen[0]
                is_volume_spike = self.datavolume[0] > (self.vol_ma[0] * self.p.p_vol_multiplier)
                buy_signal_B = is_bullish_candle and is_volume_spike

                if buy_signal_A or buy_signal_B:
                    # 3. 风险管理: 计算仓位大小
                    self.buy_atr_value = self.atr.lines.atr[0] # Store ATR for stop loss calculation
                    risk_per_share = self.buy_atr_value * self.p.p_atr_multiplier
                    
                    if risk_per_share > 0:
                        account_value = self.broker.getvalue()
                        risk_amount = account_value * self.p.p_risk_percent
                        size = int(risk_amount / risk_per_share)

                        if size > 0:
                            signal_type = "A (回调企稳)" if buy_signal_A else "B (放量突破)"
                            self.log(f'BUY CREATE, Price: {self.dataclose[0]:.2f}, Size: {size}, Signal: {signal_type}')
                            self.order = self.buy(size=size)

        # 必须在 next 方法的末尾处添加
        self.daily_values.append(self.broker.getvalue())