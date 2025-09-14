import akshare as ak

stock_financial_us_analysis_indicator_em_df = ak.stock_financial_us_analysis_indicator_em(symbol="AMD", indicator="单季报")
print(stock_financial_us_analysis_indicator_em_df.columns.tolist())
