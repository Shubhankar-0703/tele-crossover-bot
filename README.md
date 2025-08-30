# 📈 Tele-Crossover Bot Web App

A web-based stock market analysis tool that provides SMA (Simple Moving Average) crossover signals for your watchlist. The application supports both web interface and Telegram bot functionality.

## 🚀 Features

- **Web Dashboard**: Beautiful, responsive web interface to manage your stock watchlist
- **SMA Crossover Signals**: Detects Golden Cross and Death Cross patterns
- **Real-time Stock Prices**: Displays current stock prices from Yahoo Finance
- **Telegram Bot**: Optional Telegram bot for mobile notifications
- **RESTful API**: JSON API endpoints for programmatic access
- **Auto-refresh**: Dashboard automatically refreshes every 5 minutes

## 🌐 Web Interface

### Dashboard Features
- View all stocks in your watchlist with live prices
- See daily and hourly crossover signals
- Add/remove stocks from watchlist
- Responsive design for mobile and desktop
- Color-coded signal indicators

### Signal Types
- **Golden Cross**: SMA50 crosses above SMA200 (Bullish signal)
- **Death Cross**: SMA50 crosses below SMA200 (Bearish signal)
- **No Crossover**: No recent crossover detected

## 📱 Telegram Bot Commands

- `/start` - Show welcome message and commands
- `/watchlist` - Display current watchlist
- `/addstock SYMBOL` - Add stock to watchlist
- `/removestock SYMBOL` - Remove stock from watchlist
- `/signal SYMBOL` - Check crossover signals for specific stock
- `/price SYMBOL` - Get latest stock price

## 🔧 API Endpoints

- `GET /` - Main dashboard
- `GET /api/watchlist` - Get watchlist as JSON
- `GET /api/signal/{symbol}` - Get signals for specific stock
- `POST /add_stock` - Add stock to watchlist
- `POST /remove_stock` - Remove stock from watchlist
- `GET /health` - Health check endpoint
- `GET /api` - API documentation

## 🚀 Deployment

### Environment Variables Required:
```
PORT=5000                    # Port for web app (auto-set by most platforms)
BOT_TOKEN=your_bot_token     # Optional: Telegram bot token
CHAT_ID=your_chat_id         # Optional: Telegram chat ID
WATCHLIST=RELIANCE.NS,INFY.NS,TCS.NS  # Default watchlist
```

### Deploy to Railway:
1. Connect your GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically from main branch

### Deploy to Heroku:
```bash
heroku create your-app-name
heroku config:set BOT_TOKEN=your_token
heroku config:set CHAT_ID=your_chat_id
heroku config:set WATCHLIST=RELIANCE.NS,INFY.NS,TCS.NS
git push heroku main
```

### Deploy to Render:
1. Connect repository
2. Set environment variables
3. Use `web: python app.py` as start command

## 🏃‍♂️ Local Development

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set environment variables in `.env` file
5. Run the application:
   ```bash
   python app.py
   ```
6. Open http://localhost:5000 in your browser

## 📁 Project Structure

```
tele-crossover-bot/
├── app.py              # Main Flask web application
├── bot.py              # Original Telegram bot (legacy)
├── Procfile            # Deployment configuration
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version specification
├── .env               # Environment variables (local only)
├── watchlist.json     # Persistent watchlist storage
├── templates/
│   ├── index.html     # Main dashboard template
│   └── api.html       # API documentation template
└── README.md          # This file
```

## 🛠️ Technology Stack

- **Backend**: Python, Flask
- **Data**: Yahoo Finance API (yfinance)
- **Bot**: pyTelegramBotAPI
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Data Processing**: Pandas, NumPy

## 📊 Stock Symbol Format

For Indian stocks, use NSE format:
- `RELIANCE.NS` (Reliance Industries)
- `INFY.NS` (Infosys)
- `TCS.NS` (Tata Consultancy Services)

For US stocks, use ticker symbols:
- `AAPL` (Apple)
- `MSFT` (Microsoft)
- `GOOGL` (Google)

## 🔍 Monitoring

The application includes:
- Health check endpoint at `/health`
- Comprehensive logging
- Error handling for API failures
- Graceful degradation when services are unavailable

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.
