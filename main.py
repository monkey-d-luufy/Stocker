from flask import Flask, render_template, request, jsonify
import requests
import json
import yfinance as yf
from datetime import datetime, timedelta
import os
import math
import time

cached_trending = None
last_fetch_time = None

app = Flask(__name__)

# Global cache
market_movers_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION = 5 * 60  # cache for 5 minutes (300 seconds)

# Alpha Vantage API for stock data (free tier available)
ALPHA_VANTAGE_API_KEY = "demo"  # Replace with your API key
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"

# OpenAI-style API for AI insights (you can use OpenAI, Groq, or other providers)
AI_API_KEY = os.getenv("AI_API_KEY", "")  # Set this in Secrets

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

def get_trending_stocks():
    """Get trending/hottest stocks with demo data"""
    # In a real app, you'd fetch this from financial data APIs
    trending_stocks = [
        {
            'symbol': 'AAPL',
            'name': 'Apple Inc.',
            'price': 175.84,
            'change': 5.23,
            'change_percent': '+3.07%',
            'volume': 45000000,
            'market_cap': '2.74T',
            'pe_ratio': '28.5',
            'sector': 'Technology'
        },
        {
            'symbol': 'NVDA',
            'name': 'NVIDIA Corporation',
            'price': 438.12,
            'change': 12.45,
            'change_percent': '+2.93%',
            'volume': 32000000,
            'market_cap': '1.08T',
            'pe_ratio': '65.2',
            'sector': 'Technology'
        },
        {
            'symbol': 'TSLA',
            'name': 'Tesla Inc.',
            'price': 252.48,
            'change': -3.21,
            'change_percent': '-1.26%',
            'volume': 89000000,
            'market_cap': '804B',
            'pe_ratio': '47.8',
            'sector': 'Consumer Cyclical'
        },
        {
            'symbol': 'MSFT',
            'name': 'Microsoft Corporation',
            'price': 415.26,
            'change': 8.92,
            'change_percent': '+2.20%',
            'volume': 28000000,
            'market_cap': '3.09T',
            'pe_ratio': '34.1',
            'sector': 'Technology'
        },
        {
            'symbol': 'GOOGL',
            'name': 'Alphabet Inc.',
            'price': 164.87,
            'change': 2.15,
            'change_percent': '+1.32%',
            'volume': 25000000,
            'market_cap': '2.03T',
            'pe_ratio': '24.7',
            'sector': 'Communication Services'
        },
        {
            'symbol': 'AMZN',
            'name': 'Amazon.com Inc.',
            'price': 145.63,
            'change': -1.87,
            'change_percent': '-1.27%',
            'volume': 41000000,
            'market_cap': '1.52T',
            'pe_ratio': '45.3',
            'sector': 'Consumer Cyclical'
        }
    ]

    return trending_stocks

def get_market_movers(n=20):
    """
    Returns top n gainers and top n losers with live data, using cache,
    and formats market cap with commas.
    """
    global market_movers_cache
    current_time = time.time()

    # Return cached data if still valid
    if market_movers_cache["data"] and (current_time - market_movers_cache["timestamp"] < CACHE_DURATION):
        return market_movers_cache["data"]

    # Define stock universe
    universe = ["AAPL","MSFT","TSLA","NFLX","GOOGL","AMZN","META","NVDA","INTC",
                "AMD","PYPL","ADBE","CRM","UBER","LYFT","SPOT","SHOP","SQ","ZM","DOCU",
                "MRNA","RIOT","AMC","GME","PLTR","PLUG","BBBY","WISH","CLOV","SPCE"]

    movers = []
    for sym in universe:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            price = info.get("regularMarketPrice")
            prev_close = info.get("previousClose")
            if price and prev_close:
                change_percent = (price - prev_close) / prev_close * 100
                change = price - prev_close

                # Format market cap with commas
                market_cap_raw = info.get("marketCap", 0)
                market_cap = f"{market_cap_raw:,}" if market_cap_raw else "N/A"

                movers.append({
                    "symbol": sym,
                    "name": info.get("longName", sym),
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_percent": f"{change_percent:+.2f}%",
                    "volume": info.get("volume", 0),
                    "market_cap": market_cap,
                    "sector": info.get("sector", "N/A")
                })
        except Exception as e:
            print(f"Error fetching {sym}: {e}")

    # Sort movers by percentage change
    gainers = sorted(movers, key=lambda x: float(x["change_percent"].replace('%','')), reverse=True)[:n]
    losers = sorted(movers, key=lambda x: float(x["change_percent"].replace('%','')))[:n]

    result = {"gainers": gainers, "losers": losers}

    # Update cache
    market_movers_cache["data"] = result
    market_movers_cache["timestamp"] = current_time

    return result
    
def get_exchange_data():
    """Get stocks by exchange (NYSE, NASDAQ, AMEX)"""
    import random

    exchanges = {
        'NYSE': {
            'name': 'New York Stock Exchange',
            'stocks': []
        },
        'NASDAQ': {
            'name': 'NASDAQ',
            'stocks': []
        },
        'AMEX': {
            'name': 'American Stock Exchange',
            'stocks': []
        }
    }

    # NYSE stocks
    nyse_stocks = [
        {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
        {'symbol': 'WMT', 'name': 'Walmart Inc.'},
        {'symbol': 'PG', 'name': 'Procter & Gamble Co.'},
        {'symbol': 'V', 'name': 'Visa Inc.'},
        {'symbol': 'HD', 'name': 'Home Depot Inc.'},
        {'symbol': 'MA', 'name': 'Mastercard Inc.'},
        {'symbol': 'BAC', 'name': 'Bank of America Corp.'},
        {'symbol': 'DIS', 'name': 'Walt Disney Co.'},
        {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
        {'symbol': 'XOM', 'name': 'Exxon Mobil Corp.'},
        {'symbol': 'KO', 'name': 'Coca-Cola Co.'},
        {'symbol': 'PFE', 'name': 'Pfizer Inc.'},
        {'symbol': 'CVX', 'name': 'Chevron Corp.'},
        {'symbol': 'WFC', 'name': 'Wells Fargo & Co.'},
        {'symbol': 'T', 'name': 'AT&T Inc.'},
        {'symbol': 'VZ', 'name': 'Verizon Communications'},
        {'symbol': 'IBM', 'name': 'International Business Machines'},
        {'symbol': 'GE', 'name': 'General Electric Co.'},
        {'symbol': 'MRK', 'name': 'Merck & Co. Inc.'}
    ]

    # NASDAQ stocks
    nasdaq_stocks = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corp.'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corp.'},
        {'symbol': 'META', 'name': 'Meta Platforms Inc.'},
        {'symbol': 'NFLX', 'name': 'Netflix Inc.'},
        {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.'},
        {'symbol': 'INTC', 'name': 'Intel Corp.'},
        {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
        {'symbol': 'CRM', 'name': 'Salesforce Inc.'},
        {'symbol': 'AVGO', 'name': 'Broadcom Inc.'},
        {'symbol': 'TXN', 'name': 'Texas Instruments Inc.'},
        {'symbol': 'QCOM', 'name': 'Qualcomm Inc.'},
        {'symbol': 'COST', 'name': 'Costco Wholesale Corp.'},
        {'symbol': 'TMUS', 'name': 'T-Mobile US Inc.'},
        {'symbol': 'CMCSA', 'name': 'Comcast Corp.'},
        {'symbol': 'PEP', 'name': 'PepsiCo Inc.'},
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices'}
    ]

    # AMEX stocks
    amex_stocks = [
        {'symbol': 'SPY', 'name': 'SPDR S&P 500 ETF'},
        {'symbol': 'GLD', 'name': 'SPDR Gold Shares'},
        {'symbol': 'SLV', 'name': 'iShares Silver Trust'},
        {'symbol': 'EWJ', 'name': 'iShares MSCI Japan ETF'},
        {'symbol': 'FXI', 'name': 'iShares China Large-Cap ETF'},
        {'symbol': 'EEM', 'name': 'iShares MSCI Emerging Markets ETF'},
        {'symbol': 'IWM', 'name': 'iShares Russell 2000 ETF'},
        {'symbol': 'QQQ', 'name': 'Invesco QQQ Trust'},
        {'symbol': 'VTI', 'name': 'Vanguard Total Stock Market ETF'},
        {'symbol': 'BND', 'name': 'Vanguard Total Bond Market ETF'},
        {'symbol': 'XLF', 'name': 'Financial Select Sector SPDR'},
        {'symbol': 'XLK', 'name': 'Technology Select Sector SPDR'},
        {'symbol': 'XLE', 'name': 'Energy Select Sector SPDR'},
        {'symbol': 'XLV', 'name': 'Health Care Select Sector SPDR'},
        {'symbol': 'XLI', 'name': 'Industrial Select Sector SPDR'},
        {'symbol': 'XLP', 'name': 'Consumer Staples Select Sector SPDR'},
        {'symbol': 'XLY', 'name': 'Consumer Discretionary Select Sector SPDR'},
        {'symbol': 'XLU', 'name': 'Utilities Select Sector SPDR'},
        {'symbol': 'XLB', 'name': 'Materials Select Sector SPDR'},
        {'symbol': 'XLRE', 'name': 'Real Estate Select Sector SPDR'}
    ]

    # Generate data for each exchange
    for stock in nyse_stocks:
        price = random.uniform(50, 500)
        change_percent = random.uniform(-5, 5)
        change = price * (change_percent / 100)

        exchanges['NYSE']['stocks'].append({
            'symbol': stock['symbol'],
            'name': stock['name'],
            'price': round(price, 2),
            'change': round(change, 2),
            'change_percent': f'{change_percent:+.2f}%',
            'volume': random.randint(1000000, 20000000),
            'market_cap': f"{random.randint(10, 500)}B",
            'sector': random.choice(['Financial Services', 'Healthcare', 'Consumer Defensive', 'Technology'])
        })

    for stock in nasdaq_stocks:
        price = random.uniform(100, 800)
        change_percent = random.uniform(-5, 5)
        change = price * (change_percent / 100)

        exchanges['NASDAQ']['stocks'].append({
            'symbol': stock['symbol'],
            'name': stock['name'],
            'price': round(price, 2),
            'change': round(change, 2),
            'change_percent': f'{change_percent:+.2f}%',
            'volume': random.randint(5000000, 50000000),
            'market_cap': f"{random.randint(50, 3000)}B",
            'sector': random.choice(['Technology', 'Communication Services', 'Consumer Cyclical'])
        })

    for stock in amex_stocks:
        price = random.uniform(20, 300)
        change_percent = random.uniform(-3, 3)
        change = price * (change_percent / 100)

        exchanges['AMEX']['stocks'].append({
            'symbol': stock['symbol'],
            'name': stock['name'],
            'price': round(price, 2),
            'change': round(change, 2),
            'change_percent': f'{change_percent:+.2f}%',
            'volume': random.randint(500000, 10000000),
            'market_cap': f"{random.randint(1, 100)}B",
            'sector': random.choice(['ETF', 'Financial Services', 'Commodities'])
        })

    return exchanges

def get_historical_data(symbol):
    """Fetch 6-month historical stock data"""
    try:
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': 'full',
            'apikey': ALPHA_VANTAGE_API_KEY
        }

        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=10)
        data = response.json()

        if "Time Series (Daily)" in data:
            time_series = data["Time Series (Daily)"]
            # Get last 6 months of data (approximately 126 trading days)
            sorted_dates = sorted(time_series.keys(), reverse=True)[:126]

            historical_data = []
            for date in reversed(sorted_dates):  # Reverse to get chronological order
                day_data = time_series[date]
                historical_data.append({
                    'date': date,
                    'open': float(day_data['1. open']),
                    'high': float(day_data['2. high']),
                    'low': float(day_data['3. low']),
                    'close': float(day_data['4. close']),
                    'volume': int(day_data['5. volume'])
                })

            return historical_data
        else:
            # Generate demo historical data
            import random
            from datetime import datetime, timedelta

            historical_data = []
            base_price = 150.0
            current_date = datetime.now() - timedelta(days=180)

            for i in range(126):  # 6 months of trading days
                # Skip weekends
                while current_date.weekday() >= 5:
                    current_date += timedelta(days=1)

                # Random price movement
                change = random.uniform(-0.05, 0.05)
                base_price = max(base_price * (1 + change), 10)  # Don't go below $10

                daily_volatility = base_price * 0.02
                high = base_price + random.uniform(0, daily_volatility)
                low = base_price - random.uniform(0, daily_volatility)
                open_price = low + random.uniform(0, high - low)
                close_price = low + random.uniform(0, high - low)

                historical_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'open': round(open_price, 2),
                    'high': round(high, 2),
                    'low': round(low, 2),
                    'close': round(close_price, 2),
                    'volume': random.randint(500000, 5000000)
                })

                current_date += timedelta(days=1)

            return historical_data

    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return None

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

def fetch_quote(sym):
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="1d")
        price = hist['Close'].iloc[-1] if not hist.empty else None

        info = ticker.info

        return {
            "symbol": sym,
            "name": info.get("longName", sym),
            "price": float(price) if price else None,
            "change": info.get("regularMarketChange", 0.0),
            "change_percent": info.get("regularMarketChangePercent", 0.0),
            "volume": info.get("volume", 0),
            "market_cap": info.get("marketCap", 0),
            "sector": info.get("sector", "N/A"),
            "as_of": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        print(f"[fetch_quote ERROR] {sym}: {e}")
        return {"symbol": sym, "price": None}

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

@app.route("/api/trending")
def get_trending():
    symbols = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN"]
    trending_data = []

    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            hist = stock.history(period="1d")

            if not hist.empty:
                price = round(hist["Close"].iloc[-1], 2)
                open_price = round(hist["Open"].iloc[-1], 2)
                change = round(price - open_price, 2)
                change_percent = f"{(change / open_price * 100):.2f}%"

                trending_data.append({
                    "symbol": symbol,
                    "name": info.get("shortName", "N/A"),
                    "price": price,
                    "change": change,
                    "change_percent": change_percent,
                    "volume": info.get("volume", "N/A"),
                    "market_cap": info.get("marketCap", "N/A"),
                    "sector": info.get("sector", "N/A"),
                    "pe_ratio": info.get("trailingPE", "N/A")
                })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            continue

    return jsonify({"trending_stocks": trending_data})
        
@app.route('/api/market-movers')
def get_market_movers_api():
    movers = get_market_movers(n=20)  # top 20 gainers/losers
    return jsonify({
        "market_movers": movers,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/exchanges')
def get_exchanges_api():
    """API endpoint to get stocks by exchange"""
    exchanges = get_exchange_data()
    return jsonify({
        'exchanges': exchanges,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stock/<symbol>')
def stock_detail(symbol):
    """Stock detail page with historical data"""
    return render_template('stock_detail.html', symbol=symbol.upper())

@app.route('/api/stock/<symbol>/historical')
def get_historical_stock_data(symbol):
    """API endpoint to get historical stock data"""
    historical_data = get_historical_data(symbol)
    if not historical_data:
        return jsonify({'error': 'Unable to fetch historical data'}), 400

    return jsonify({
        'symbol': symbol.upper(),
        'historical_data': historical_data,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/watchlist', methods=['POST'])
def add_to_watchlist():
    """Add stock to watchlist (simple in-memory storage)"""
    data = request.get_json()
    symbol = data.get('symbol', '').upper()

    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400

    # In a real app, you'd store this in a database
    return jsonify({'message': f'{symbol} added to watchlist', 'symbol': symbol})

@app.get("/api/quotes")
def get_quotes():
    symbols = request.args.get("symbols","").upper().replace(" ", "")
    syms = [s for s in symbols.split(",") if s]
    data = { s: fetch_quote(s) for s in syms }
    resp = jsonify({"quotes": data})
    # Prevent CDN/browser from serving stale results
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
