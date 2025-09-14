import backtrader as bt

# 定义交易策略
class CustomStrategy(bt.Strategy): # 修改类名为 CustomStrategy
    params = (
        ('short_ma', 10),  # 短期均线
        ('long_ma', 50),   # 长期均线
        ('rsi_period', 14), # RSI周期
        ('rsi_overbought', 70), # RSI超买阈值
        ('risk_per_trade', 0.01), # 每笔交易风险1%
        ('stop_loss', 0.02), # 固定止损2%
    )

    def __init__(self):
        self.sma_short = bt.indicators.SMA(self.data.close, period=self.params.short_ma)
        self.sma_long = bt.indicators.SMA(self.data.close, period=self.params.long_ma)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)
        self.order = None
        self.daily_values = [] # 添加用于记录每日价值的列表

    def next(self):
        if self.order:
            return

        # 计算仓位大小
        account_value = self.broker.getvalue()
        risk_amount = account_value * self.params.risk_per_trade
        stop_loss_distance = self.data.close[0] * self.params.stop_loss
        size = int(risk_amount / stop_loss_distance)

        # 入场：短期均线上穿长期均线，且RSI不过买
        if not self.position and self.sma_short[0] > self.sma_long[0] and self.sma_short[-1] <= self.sma_long[-1] and self.rsi[0] < self.params.rsi_overbought:
            self.order = self.buy(size=size)
            self.stop_price = self.data.close[0] * (1 - self.params.stop_loss)
            self.log(f'买入 {size} 股，价格 {self.data.close[0]:.2f}, 止损 {self.stop_price:.2f}')

        # 出场：短期均线下穿长期均线或触及止损
        if self.position:
            if self.sma_short[0] < self.sma_long[0] and self.sma_short[-1] >= self.sma_long[-1]:
                self.order = self.sell(size=self.position.size)
                self.log(f'卖出 {self.position.size} 股，价格 {self.data.close[0]:.2f} (均线交叉)')
            elif self.data.close[0] <= self.stop_price:
                self.order = self.sell(size=self.position.size)
                self.log(f'卖出 {self.position.size} 股，价格 {self.data.close[0]:.2f} (止损)')
        
        # 在每个 bar 结束时记录账户总价值
        current_value = self.broker.getvalue()
        self.daily_values.append(current_value) # 记录当日价值

    def log(self, txt):
        dt = self.data.datetime.date(0)
        print(f'{dt}: {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            self.order = None