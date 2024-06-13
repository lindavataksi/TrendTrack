import os
import requests
import urllib.parse
import yfinance as yf

from flask import redirect, render_template, request, session
from functools import wraps

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def get_stock_price(symbol):
    try:
        # Fetch historical data for the symbol
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="max")  # Adjust period as needed
        
        if data.empty:
            print(f"No historical data found for symbol: {symbol}")
            return None
        
        # Get the last closing price
        price = data['Close'].iloc[-1]

        return price  # Return the actual price value
        
    except Exception as e:
        print(f"Error fetching data for symbol {symbol}: {e}")
        return None


def lookup(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info:
            print(f"No information found for symbol: {symbol}")
            return None
        
        print(f"Available keys in info: {list(info.keys())}")
        
        market_price = get_stock_price(symbol)
        print(f"Market price for {symbol}: {market_price}")
        
        if market_price is not None:
            return {
                "name": info.get("shortName", info.get("longName", "N/A")),
                "price": float(market_price),  # Ensure market_price is numeric
                "symbol": info["symbol"]
            }
        else:
            print(f"No market price found for symbol: {symbol}")
            return None
        
    except Exception as e:
        print(f"Error looking up symbol {symbol}: {e}")
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"
