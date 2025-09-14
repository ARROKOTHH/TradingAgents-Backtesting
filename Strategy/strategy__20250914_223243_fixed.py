import backtrader as bt
import datetime

class CustomStrategy(bt.Strategy):
    """
    策略蓝图: 趋势跟踪 + 逢低买入 (Trend-Following with Buy-the-Dip)
    - 风险偏好: 中等
    - 趋势过滤器: 价格必须高于长期均线 (SMA 50) 才能考虑买入。
    - 入场信号 (满足其一即可):
        1. RSI回调企稳: 在上升趋势中，RSI从下方上穿40，表明回调结束，多头力量回归。
        2. MACD动能反转: 在上升趋势中，MACD柱状图从负值转为正值，确认短期动能由空转多。
    - 出场逻辑: 基于ATR的追踪止损，保护利润，让盈利奔跑。
    - 仓位管理: 固定风险百分比模型，确保单笔亏损可控。
    """
    params = (
        # 1. 趋势过滤器参数
        ('trend_period', 50),  # 用于判断长期趋势的SMA周期

        # 2. 入场信号参数 (Plan A: RSI回调)
        ('rsi_period', 14),      # RSI指标的计算周期
        ('rsi_entry_level', 40), # RSI回调后重新走强的入场阈值

        # 3. 入场信号参数 (Plan B: MACD动能确认)
        ('macd_fast', 12),       # MACD快线周期
        ('macd_slow', 26),       # MACD慢线周期
        ('macd_signal', 9),      # MACD信号线周期

        # 4. 出场逻辑参数 (ATR追踪止损)
        ('atr_period', 14),      # ATR指标的计算周期
        ('atr_multiplier', 3.0), # ATR倍数，用于计算止损距离

        # 5. 风险管理参数
        ('risk_percent', 0.02),  # 每笔交易愿意承担的投资组合风险百分比 (2%)
    )

    def __init__(self):
        """策略初始化"""
        # 必须: 初始化 daily_values 列表
        self.daily_values = []

        # 引用数据
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        # 状态变量
        self.order = None
        self.stop_price = None
        self.entry_price = None

        # 1. 趋势过滤器指标
        self.trend_sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.p.trend_period)

        # 2. 入场信号指标
        self.rsi = bt.indicators.RSI(period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        
        # 使用CrossOver简化信号判断
        self.rsi_crossover = bt.indicators.CrossOver(self.rsi, self.p.rsi_entry_level)
        self.macd_hist_crossover = bt.indicators.CrossOver(self.macd.lines.histo, 0)

        # 3. 出场逻辑指标
        self.atr = bt.indicators.ATR(period=self.p.atr_period)

    def log(self, txt, dt=None):
        """日志记录函数"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def notify_order(self, order):
        """订单状态通知"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                self.entry_price = order.executed.price
                # 买入成功后，立即设置初始止损价
                self.stop_price = self.entry_price - self.p.atr_multiplier * self.atr[0]
            elif order.issell():
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
                # 卖出后重置状态
                self.stop_price = None
                self.entry_price = None
            
            self.order = None # 订单完成后，重置订单引用

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
            self.order = None # 订单失败后，重置订单引用

    def next(self):
        """策略核心逻辑"""
        # 如果有订单正在处理，则不执行新操作
        if self.order:
            return

        # 入场逻辑: 检查是否持有仓位
        if not self.position:
            # 1. 趋势过滤器
            trend_filter = self.dataclose[0] > self.trend_sma[0]
            
            # 2. 入场信号
            rsi_signal = self.rsi_crossover[0] > 0  # RSI上穿阈值
            macd_signal = self.macd_hist_crossover[0] > 0 # MACD柱状图上穿0轴
            
            if trend_filter and (rsi_signal or macd_signal):
                # 3. 风险管理：计算仓位大小
                stop_dist = self.p.atr_multiplier * self.atr[0]
                if stop_dist == 0: # 避免除以零
                    return
                
                risk_per_share = stop_dist
                portfolio_value = self.broker.getvalue()
                total_risk_amount = portfolio_value * self.p.risk_percent
                
                size = total_risk_amount / risk_per_share
                
                if size > 0:
                    self.log(f'BUY CREATE, Price: {self.dataclose[0]:.2f}, Size: {size:.2f}')
                    self.order = self.buy(size=size)

        # 出场逻辑: 如果持有仓位，则更新并检查追踪止损
        else:
            # 1. 计算新的潜在止损位
            potential_stop = self.dataclose[0] - self.p.atr_multiplier * self.atr[0]
            
            # 2. 更新止损价（只上移，不下调）
            self.stop_price = max(self.stop_price, potential_stop)
            
            # 3. 检查是否触发止损
            if self.dataclose[0] < self.stop_price:
                self.log(f'SELL CREATE (Trailing Stop Hit), Price: {self.dataclose[0]:.2f}')
                self.order = self.close()

        # 必须: 在next方法末尾记录每日市值
        self.daily_values.append(self.broker.getvalue())

    def stop(self):
        """策略结束时调用"""
        self.log(f'Ending Value {self.broker.getvalue():.2f}')