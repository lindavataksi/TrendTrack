import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import yfinance as yf

def predict_stock_price(ticker):
    # Fetch historical data for the specified ticker
    data = yf.download(ticker, start="2010-01-01", end="2024-06-01")
    data.reset_index(inplace=True)
    data = data[['Date', 'Close']]
    data['Date'] = pd.to_datetime(data['Date'])

    # Sorting the data by date
    data = data.sort_values(by='Date')

    # Prepare the data
    X = np.array(data.index).reshape(-1, 1)  # Using index as feature
    y = np.array(data['Close'])

    # Build the linear regression model
    model = LinearRegression()
    model.fit(X, y)

    # Predict future stock prices
    future_index = np.arange(len(X), len(X) + 365).reshape(-1, 1)
    future_prices = model.predict(future_index)

    # Storing variables for comparing current and future prices (future = after 365 days)
    current_price = data['Close'].iloc[-1]
    future_price = future_prices[364]
    
    # determine accuracy- Calc. R^2 score and convert it to a percentage
    r2_score = model.score(X, y)
    accuracy_percentage = r2_score * 100

    return round(current_price, 2), round(future_price, 2), round(accuracy_percentage, 2)