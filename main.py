from flask import Flask, render_template, request, jsonify
import yfinance as yf
from datetime import datetime, timedelta
import random

cached_trending = None
last_fetch_time = None
app = Flask(__name__)

# ------------------------
# Stock Data Functions
# ------------------------
def get_stock_data(symbol):
    """Fetch stock price data using Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        return {
            'symbol': symbol.upper(),
            'price': info.get('currentPrice', 0),
            'change': info.get('regularMarketChange', 0),
            'change_percent': f"{info.get('regularMarketChangePercent', 0):.2f}%",
            'volume': info.get('volume', 0),
            'last_updated': datetime.now().strftime('%Y-%m-%d')
        }
    except Exception as e:
        return {'error': str(e)}

def get_stock_fundamentals(symbol):
    """Fetch stock fundamentals data using Yahoo Finance"""
    try:
        stock = yf.Ticker(symbol)
        info = stock.info

        return {
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'peg_ratio': info.get('pegRatio', 'N/A'),
            'dividend_yield': info.get('dividendYield', 'N/A'),
            'eps': info.get('trailingEps', 'N/A'),
            'beta': info.get('beta', 'N/A'),
            '52_week_high': info.get('fiftyTwoWeekHigh', 'N/A'),
            '52_week_low': info.get('fiftyTwoWeekLow', 'N/A'),
            'analyst_target': info.get('targetMeanPrice', 'N/A'),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A')
        }

    except Exception as e:
        return {'error': str(e)}

def get_ai_insights(stock_data):
    """Simple rule-based insights"""
    if not stock_data or 'error' in stock_data:
        return "Unable to generate insights - no stock data available."

    price = stock_data['price']
    change = stock_data['change']
    try:
        change_percent = float(stock_data['change_percent'].replace('%', '').replace('+', ''))
    except:
        change_percent = 0

    insights = []

    if change > 0:
        if change_percent > 5:
            insights.append("🚀 Strong upward momentum!")
        elif change_percent > 2:
            insights.append("📈 Positive trend observed.")
        else:
            insights.append("✅ Mild positive movement.")
    elif change < 0:
        if change_percent < -5:
            insights.append("⚠️ Significant decline detected.")
        elif change_percent < -2:
            insights.append("📉 Negative trend.")
        else:
            insights.append("🔄 Minor decline.")
    else:
        insights.append("➡️ Stable price action.")

    if stock_data['volume'] > 1000000:
        insights.append("📊 High trading volume.")

    if price > 200:
        insights.append("💎 Premium stock price range.")
    elif price < 50:
        insights.append("💰 Affordable entry point.")

    return " ".join(insights)

# ------------------------
# Flask Routes
# ------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stock/<symbol>')
def get_stock_info(symbol):
    stock_data = get_stock_data(symbol)
    if 'error' in stock_data:
        return jsonify({'error': stock_data['error']}), 400

    fundamentals = get_stock_fundamentals(symbol)
    if 'error' in fundamentals:
        return jsonify({'error': fundamentals['error']}), 400

    ai_insights = get_ai_insights(stock_data)

    return jsonify({
        'stock_data': stock_data,
        'fundamentals': fundamentals,
        'ai_insights': ai_insights,
        'timestamp': datetime.now().isoformat()
    })
# ------------------------
# Predefined popular stocks
# ------------------------
POPULAR_STOCKS = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL', 'META']

# ------------------------
# Trending Stocks Endpoint
# ------------------------
@app.route('/api/trending')
def get_trending():
    global cached_trending, last_fetch_time

    # Cache for 5 minutes
    if cached_trending and last_fetch_time and datetime.now() - last_fetch_time < timedelta(minutes=5):
        return jsonify({"trending_stocks": cached_trending})

    symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN"]
    trending_stocks = []

    for sym in symbols:
        ticker = yf.Ticker(sym)
        info = ticker.history(period="1d")
        if not info.empty:
            price = info["Close"].iloc[-1]
            prev_close = info["Close"].iloc[-2] if len(info) > 1 else price
            change = price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close else 0
            trending_stocks.append({
                "symbol": sym,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_percent": f"{change_percent:.2f}%"
            })

    cached_trending = trending_stocks
    last_fetch_time = datetime.now()
    return jsonify({"trending_stocks": trending_stocks})

# ------------------------
# Main
# ------------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
