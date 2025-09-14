import re

def auto_correct_backtrader_code_test():
    """
    测试修复后的正则表达式
    """
    # 测试代码
    code = """
    self.rsi = bt.indicators.RSI(
        self.dataclose, period=self.p.p_rsi_period)
    self.atr = bt.indicators.AverageTrueRange(
        self.datas[0], period=self.p.p_atr_period)
    """
    
    # 定义指标类名，用于识别指标初始化语句
    indicator_classes = [
        'SimpleMovingAverage', 'ExponentialMovingAverage', 'RSI', 'MACD', 
        'BollingerBands', 'AverageTrueRange', 'Stochastic', 'ADX', 'DMI',
        'CrossOver', 'CrossDown'
    ]
    
    # 构建正则表达式模式来匹配指标初始化语句
    indicator_class_pattern = '|'.join(indicator_classes)
    # 转义特殊字符以避免正则表达式错误
    assignment_pattern = re.compile(
        r'(\w+)\s*=\s*bt\.indicators\.(' + indicator_class_pattern + r')\s*\('
    )
    
    # 找到所有指标变量名
    indicator_vars = set()
    for match in assignment_pattern.finditer(code):
        var_name = match.group(1)
        indicator_vars.add(var_name)
    
    print(f"[DEBUG] 识别到的指标变量名: {indicator_vars}")
    return indicator_vars

if __name__ == "__main__":
    auto_correct_backtrader_code_test()