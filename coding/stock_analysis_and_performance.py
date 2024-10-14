# filename: stock_analysis_and_performance.py

import yfinance as yf
import pandas as pd

def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    return stock.info['currentPrice'], hist

def analyze_stock_performance(historical_data):
    historical_data['Return'] = historical_data['Close'].pct_change()
    avg_return = historical_data['Return'].mean()
    volatility = historical_data['Return'].std()
    return avg_return, volatility

ticker = "AAPL"  # 示例股票代码，可以替换成其他股票代码
current_price, historical_data = get_stock_data(ticker)
avg_return, volatility = analyze_stock_performance(historical_data)

print("最新的股票价格:", current_price)
print("\n历史数据:")
print(historical_data.tail())  # 只显示最后5行
print("\n股票表现分析:")
print("平均回报率:", avg_return)
print("波动性:", volatility)