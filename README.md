Bitcoin Orderbook Tracker 📈
Thanks for checking out my Bitcoin orderbook tracker. I built this because I needed a reliable way to collect real-time market depth data from Binance, and honestly, most of the existing tools were either overcomplicated or didn't handle edge cases well.
This tool does one thing and does it well: it connects to Binance's WebSocket feed, grabs the orderbook data, validates it, and saves everything to CSV files. No fancy UI, no bloat - just clean, reliable data collection.
What This Actually Does
So here's the deal - this connects to Binance's live data stream and captures the "orderbook" (basically all the buy and sell orders sitting in the market). Every time the orderbook updates, we grab:

Multiple price levels (not just the best bid/ask, but deeper into the book)
Timestamps (both local and exchange timestamps, because timing matters)
Data validation (filters out weird prices and zero quantities)
Market metrics (spread, mid-price, bid/ask ratios - the good stuff)

The output is clean CSV files with timestamps, so you can analyze market microstructure, backtest strategies, or just satisfy your curiosity about how Bitcoin trades.

Getting Started
Installation

bash:
git clone https://github.com/yourusername/bitcoin-orderbook-tracker.git
cd bitcoin-orderbook-tracker
pip install -r requirements.txt

Running It
bash:
python main.py

That's it! It'll start collecting data and save it to a CSV file with today's date. Hit Ctrl+C when you want to stop - it handles shutdown gracefully and won't corrupt your data.
Configuration
Want to tweak things? Edit config.json:

json:
{
    "price_levels": 10,           // How deep into the orderbook to go
    "symbol": "btcusdt",          // Trading pair (stick with BTC for now)
    "reconnect_delay": 5,         // Seconds to wait before reconnecting
    "log_level": "INFO"           // How chatty the logs should be
}
The price_levels setting is important - more levels = more data but bigger files. I find 10 levels gives you a good view of market depth without going overboard.
What You Get
The CSV output looks like this:

timestamp - When we captured the data
exchange_timestamp - Binance's timestamp
bid_price_1, bid_size_1 - Best bid price and quantity
ask_price_1, ask_size_1 - Best ask price and quantity
... more price levels ...
spread - Ask price minus bid price
mid_price - Average of best bid and ask
bid_ask_ratio - Total bid size divided by total ask size

The bid/ask ratio is particularly interesting - when it's above 1, there's more buying pressure; below 1, more selling pressure. Not a trading signal by itself, but useful context.
Data Quality Features
Look, crypto markets are wild and data feeds can be unreliable. I learned this the hard way, so this tool includes:

Gap Detection: If messages stop coming or there are big delays, you'll get warnings. Network issues happen, exchanges have maintenance, stuff breaks - at least you'll know about it.
Data Validation: Filters out obviously wrong prices (like BTC at $10 million) and invalid quantities. The data might be messy, but what you save will be clean.
Auto-Reconnection: Connection drops? No problem. It'll keep trying to reconnect with exponential backoff. Your data collection doesn't stop just because the internet hiccupped.
Graceful Shutdown: Hit Ctrl+C and it properly closes files, logs final stats, and exits cleanly. No corrupted data files.
Use Cases
I originally built this for my own trading research, but it's useful for:

Backtesting strategies (especially ones that care about market depth)
Academic research on market microstructure
Understanding market dynamics during volatile periods
Quality analysis of exchange data feeds
Just being curious about how Bitcoin actually trades

A Few Warnings
Rate Limits: Binance is pretty generous with WebSocket connections, but don't abuse it. This tool is designed to be respectful of their infrastructure.
Data Size: Bitcoin orderbook updates come fast and frequently. You can easily generate hundreds of MB per day. Plan your disk space accordingly.
Not Financial Advice: This is a data collection tool. What you do with the data is up to you, but please don't blame me if you lose money trading based on patterns you find. Markets are hard.
Contributing
Found a bug? Have an idea for improvement? Pull requests are welcome! Just keep the code clean and make sure it doesn't break existing functionality.
Some ideas for future features:

Support for other trading pairs
Real-time visualization dashboard
More sophisticated gap detection
Integration with other exchanges
Data analysis examples

Thanks!
Seriously, thank you for using this tool. I put a lot of thought into making it reliable and easy to use. If it helps with your research or trading, that makes me happy.
If you find any issues or have suggestions, feel free to open an issue. And if this tool saves you time or makes your life easier, consider giving it a star ⭐ - it helps other people discover it.
Happy data collecting!