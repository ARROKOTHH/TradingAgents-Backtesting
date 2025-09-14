def auto_correct_backtrader_code(code: str) -> str:
    """
    自动修正Backtrader代码中常见的.lines属性访问错误。
    """
    import re
    
    # 添加调试信息
    print("[DEBUG] 开始自动修正Backtrader代码...")
    print("[DEBUG] 修正前的代码:")
    print(code)
    print("")
    
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
    
    # 新增：修正AI错误的指标初始化方式
    # 例如：self.rsi.lines.rsi = bt.indicators.RSI(...) -> self.rsi = bt.indicators.RSI(...)
    wrong_init_rules = []
    for var_name in indicator_vars:
        # 错误的初始化方式：self.var.lines.var = bt.indicators.Indicator(...)
        wrong_init_rules.append((
            rf'self\.{var_name}\.lines\.{var_name}\s*=\s*bt\.indicators\.',
            f'self.{var_name} = bt.indicators.'
        ))
    
    # 定义需要修正的属性访问模式
    # 只修正那些明确是指标变量的属性访问
    correction_rules = []
    for var_name in indicator_vars:
        # 修正 .histo, .rsi, .atr 等属性访问
        correction_rules.append((rf'\b{var_name}\.histo\b', f'{var_name}.lines.histo'))
        correction_rules.append((rf'\b{var_name}\.macd\b', f'{var_name}.lines.macd'))
        correction_rules.append((rf'\b{var_name}\.signal\b', f'{var_name}.lines.signal'))
        correction_rules.append((rf'\b{var_name}\.DIp\b', f'{var_name}.lines.DIp'))
        correction_rules.append((rf'\b{var_name}\.DIm\b', f'{var_name}.lines.DIm'))
        correction_rules.append((rf'\b{var_name}\.adx\b', f'{var_name}.lines.adx'))
        correction_rules.append((rf'\b{var_name}\.top\b', f'{var_name}.lines.top'))
        correction_rules.append((rf'\b{var_name}\.mid\b', f'{var_name}.lines.mid'))
        correction_rules.append((rf'\b{var_name}\.bot\b', f'{var_name}.lines.bot'))
        correction_rules.append((rf'\b{var_name}\.rsi\b', f'{var_name}.lines.rsi'))
        correction_rules.append((rf'\b{var_name}\.percK\b', f'{var_name}.lines.percK'))
        correction_rules.append((rf'\b{var_name}\.percD\b', f'{var_name}.lines.percD'))
        correction_rules.append((rf'\b{var_name}\.atr\b', f'{var_name}.lines.atr'))
        correction_rules.append((rf'\b{var_name}\.sma\b', f'{var_name}.lines.sma'))
        correction_rules.append((rf'\b{var_name}\.ema\b', f'{var_name}.lines.ema'))
    
    # 合并规则，特定变量的规则优先
    all_rules = wrong_init_rules + correction_rules
    
    corrected_code = code
    modifications_made = []
    
    for pattern, replacement in all_rules:
        # 记录替换前的代码
        original_code = corrected_code
        
        # 应用替换
        corrected_code = re.sub(pattern, replacement, corrected_code)
        
        # 如果代码发生了变化，记录下来
        if original_code != corrected_code:
            modifications_made.append(f"应用规则: {pattern} -> {replacement}")
    
    print("[DEBUG] 自动修正完成。")
    if modifications_made:
        print("[DEBUG] 执行的修正操作:")
        for mod in modifications_made:
            print("  - " + mod)
        print("[DEBUG] 修正后的代码:")
        print(corrected_code)
        print("")
    else:
        print("[DEBUG] 未发现需要修正的内容。")
        print("")
        
    return corrected_code