import backtrader as bt
import math

class CustomStrategy(bt.Strategy):
    """
    Backtrader Strategy: 北方稀土(600111)趋势回调策略
    Style: Buy-the-Dip Trend Following Strategy
    Risk Appetite: Moderate
    """
    
    # 1. 核心参数 (Parameters)
    params = (
        # 趋势过滤器参数
        ('p_long_ma_period', 60),   # 长期均线周期，用于定义主趋势 (季度线)
        # 入场信号参数 (Plan A: 回调)
        ('p_short_ma_period', 20),  # 短期均线周期，用于识别回调支撑 (月线)
        ('p_rsi_period', 14),       # RSI指标周期
        ('p_rsi_low', 40),          # RSI回调买入的阈值下限
        # 入场信号参数 (Plan B: 动量突破)
        ('p_vol_ma_period', 20),    # 成交量均线周期
        ('p_vol_multiplier', 2.0),  # 成交量放大倍数
        # 出场逻辑参数
        ('p_atr_period', 14),       # ATR周期，用于计算止损距离
        ('p_atr_multiplier', 2.5),  # ATR倍数，决定止损的宽松程度
        # 风险管理参数
        ('p_risk_percent', 0.02),   # 每笔交易承担的账户总资金风险百分比 (2%)
    )

    def __init__(self):
        """
        策略初始化
        """
        # 严格遵守【Backtrader 编码核心准则】，此处不进行参数的动态调整
        # 因为默认参数已符合【最终风险偏好】: 中等

        # 数据快捷访问
        self.data_close = self.datas[0].close
        self.data_open = self.datas[0].open
        self.data_low = self.datas[0].low
        self.data_high = self.datas[0].high
        self.data_volume = self.datas[0].volume

        # 初始化指标
        # 趋势过滤器
        self.long_ma = bt.indicators.SimpleMovingAverage(
            self.data_close, period=self.p.p_long_ma_period)
        
        # 入场信号指标
        self.short_ma = bt.indicators.SimpleMovingAverage(
            self.data_close, period=self.p.p_short_ma_period)
        self.rsi.lines.rsi = bt.indicators.RSI(period=self.p.p_rsi_period)
        self.vol_ma = bt.indicators.SimpleMovingAverage(
            self.data_volume, period=self.p.p_vol_ma_period)
        
        # 使用CrossOver/CrossDown指标处理交叉信号
        self.crossover_short_ma = bt.indicators.CrossOver(self.data_close, self.short_ma)
        self.crossdown_short_ma = bt.indicators.CrossDown(self.data_close, self.short_ma)

        # 出场和风险管理指标
        self.atr.lines.atr = bt.indicators.ATR(self.datas[0], period=self.p.p_atr_period)

        # 状态管理变量
        self.order = None
        self.trailing_stop_price = 0.0
        self.waiting_for_rebound = False # Plan A 的状态变量

        # 必须初始化的日志记录列表
        self.daily_values = []

    def notify_order(self, order):
        """
        订单状态通知
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                # 买入成功后，设置初始追踪止损价
                entry_price = order.executed.price
                self.trailing_stop_price = entry_price - (self.atr.lines.atr[0] * self.p.p_atr_multiplier)
                print(
                    f'BUY EXECUTED, Price: {entry_price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}, '
                    f'Initial Stop: {self.trailing_stop_price:.2f}'
                )
            elif order.issell():
                print(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, '
                    f'Comm: {order.executed.comm:.2f}'
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print(f'Order Canceled/Margin/Rejected: {order.getstatusname()}')

        self.order = None

    def notify_trade(self, trade):
        """
        交易状态通知
        """
        if not trade.isopen:
            print(f'TRADE PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')

    def next(self):
        """
        策略核心逻辑
        """
        # 强制要求：每日关键指标日志
        print(
            f"Date: {self.datas[0].datetime.date(0)}, "
            f"Close: {self.data_close[0]:.2f}, "
            f"Long MA({self.p.p_long_ma_period}): {self.long_ma[0]:.2f}, "
            f"Short MA({self.p.p_short_ma_period}): {self.short_ma[0]:.2f}, "
            f"RSI({self.p.p_rsi_period}): {self.rsi.lines.rsi[0]:.2f}, "
            f"ATR({self.p.p_atr_period}): {self.atr.lines.atr[0]:.2f}, "
            f"Volume: {self.data_volume[0]:.0f}, "
            f"Vol MA({self.p.p_vol_ma_period}): {self.vol_ma[0]:.0f}"
        )

        # 如果有挂单，不进行任何操作
        if self.order:
            return

        # 6. 量化出场逻辑 (Exit Logic)
        if self.position:
            # 基于ATR的追踪止损
            new_stop_price = self.data_close[0] - (self.atr.lines.atr[0] * self.p.p_atr_multiplier)
            self.trailing_stop_price = max(self.trailing_stop_price, new_stop_price)
            
            if self.data_close[0] < self.trailing_stop_price:
                print(f"--- SELL SIGNAL: Trailing Stop Hit ---")
                print(f"Date: {self.datas[0].datetime.date(0)}, Close: {self.data_close[0]:.2f}, Stop Price: {self.trailing_stop_price:.2f}")
                self.order = self.close()
            return

        # 3. 量化趋势过滤器 (Trend Filter)
        is_uptrend = (self.data_close[0] > self.long_ma[0]) and (self.long_ma[0] > self.long_ma[-1])
        
        # 如果不在上升趋势中，重置回调等待状态
        if not is_uptrend:
            self.waiting_for_rebound = False

        # 4. 量化入场信号 (Entry Signal)
        # 必须是空仓状态
        if not self.position and is_uptrend:
            buy_signal_A = False
            buy_signal_B = False

            # Plan A: 回调企稳信号
            # 步骤1: 监测到回调开始（下穿短期均线），进入等待反弹状态
            if self.crossdown_short_ma[0] < 0:
                self.waiting_for_rebound = True
                print(f"State Change: Price crossed down short MA. Now waiting for rebound.")

            # 步骤2: 在等待状态下，监测到反弹（上穿短期均线）且RSI健康
            if self.waiting_for_rebound and self.crossover_short_ma[0] > 0 and self.rsi.lines.rsi[0] > self.p.p_rsi_low:
                buy_signal_A = True

            # Plan B: 放量突破信号
            is_positive_candle = self.data_close[0] > self.data_open[0]
            is_volume_spike = self.data_volume[0] > (self.vol_ma[0] * self.p.p_vol_multiplier)
            if is_positive_candle and is_volume_spike:
                buy_signal_B = True

            # 强制要求：入场条件判断日志
            final_buy_signal = buy_signal_A or buy_signal_B
            print(f"Trend Filter Met: {is_uptrend}")
            print(f"Buy Condition A (Callback): {buy_signal_A}, Buy Condition B (Breakout): {buy_signal_B}")
            print(f"Final Buy Condition Met: {final_buy_signal}")

            if final_buy_signal:
                # 6. 量化风险管理 (Risk Management) - 计算仓位规模
                initial_stop_price = self.data_close[0] - (self.atr.lines.atr[0] * self.p.p_atr_multiplier)
                
                # 确保止损价有效
                if self.data_close[0] <= initial_stop_price:
                    print(f"Skipping trade: Entry price {self.data_close[0]:.2f} is too close to stop price {initial_stop_price:.2f}")
                    return

                risk_per_share = self.data_close[0] - initial_stop_price
                risk_amount = self.broker.getvalue() * self.p.p_risk_percent
                size = math.floor(risk_amount / risk_per_share)

                print(f"--- BUY SIGNAL: Triggered ---")
                print(f"Portfolio Value: {self.broker.getvalue():.2f}")
                print(f"Risk Amount ({self.p.p_risk_percent*100}%): {risk_amount:.2f}")
                print(f"Risk Per Share (Entry - Stop): {risk_per_share:.2f}")
                print(f"Calculated Position Size: {size}")

                if size > 0:
                    self.order = self.buy(size=size)
                    # 买入后重置回调等待状态
                    self.waiting_for_rebound = False

        # 必须在next方法末尾添加
        self.daily_values.append(self.broker.getvalue())