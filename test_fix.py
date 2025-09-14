import sys
import os
sys.path.insert(0, 'K:/Git/Tradingagents-Backtesitng')

from web.modules.strategy_backtesting import auto_correct_backtrader_code

# 测试代码，包含AI错误的初始化方式
test_code = '''
import backtrader as bt

class CustomStrategy(bt.Strategy):
    params = (
        ('p_rsi_period', 14),
        ('p_atr_period', 14),
    )

    def __init__(self):
        self.daily_values = []
        
        # AI错误的初始化方式
        self.rsi.lines.rsi = bt.indicators.RSI(
            self.dataclose, period=self.p.p_rsi_period)
        self.atr.lines.atr = bt.indicators.AverageTrueRange(
            self.datas[0], period=self.p.p_atr_period)

    def next(self):
        # 错误的属性访问方式
        if self.rsi.rsi[0] < 30:  # 应该是 self.rsi.lines.rsi[0]
            self.buy()
        
        # 错误的属性访问方式
        atr_value = self.atr.atr[0]  # 应该是 self.atr.lines.atr[0]
        self.daily_values.append(self.broker.getvalue())
'''

print("原始代码:")
print(test_code)
print("\n" + "="*50 + "\n")

corrected_code = auto_correct_backtrader_code(test_code)

print("修正后的代码:")
print(corrected_code)