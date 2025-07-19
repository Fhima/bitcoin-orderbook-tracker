import websocket
import json
import csv
import datetime
import ssl
import time
import threading
import logging
from utils import setup_graceful_shutdown, detect_data_gaps, cleanup_and_exit


# Configuration
CONFIG = {
    'price_levels': 10,  # Number of bid/ask levels to capture
    'symbol': 'btcusdt',
    'exchange_url': 'wss://stream.binance.com:9443/ws/',
    'reconnect_delay': 5,
    'use_exchange_timestamp': True,  # Use exchange timestamp if available
    'log_level': 'INFO',
    'gap_threshold_seconds': 5.0,  # Added missing config
    'normal_message_interval': 1.0  # Added missing config
}

# Global variables
csv_file = None
csv_writer = None
message_counter = 0
connection_start_time = None
last_message_time = None
shutdown_requested = False

# Setup logging
logging.basicConfig(
    level=getattr(logging, CONFIG['log_level']),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'orderbook_tracker_{datetime.datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_price_data(price, size):
    """Validate price and size data"""
    try:
        price_float = float(price)
        size_float = float(size)
        
        if price_float <= 0 or size_float < 0:
            return False, f"Invalid values: price={price_float}, size={size_float}"
        
        if price_float > 1000000:  # Sanity check for BTC price
            return False, f"Price too high: {price_float}"
            
        return True, None
    except (ValueError, TypeError):
        return False, f"Invalid data types: price={price}, size={size}"

def get_timestamp():
    """Get timestamp with millisecond precision"""
    if CONFIG['use_exchange_timestamp']:
        # Return current timestamp in milliseconds
        return int(time.time() * 1000)
    else:
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def on_open(ws):
    global csv_file, csv_writer, connection_start_time
    
    connection_start_time = time.time()
    
    # Create filename with today's date
    filename = f"btc_orderbook_{datetime.datetime.now().strftime('%Y_%m_%d')}.csv"
    
    # Open the file for writing
    csv_file = open(filename, 'w', newline='')
    
    # Create the CSV writer
    csv_writer = csv.writer(csv_file)
    
    # Write the header row with multiple price levels
    header = ['timestamp', 'exchange_timestamp']
    # Add columns for bid levels
    for i in range(1, CONFIG['price_levels'] + 1):
        header.extend([f'bid_price_{i}', f'bid_size_{i}'])
    # Add columns for ask levels  
    for i in range(1, CONFIG['price_levels'] + 1):
        header.extend([f'ask_price_{i}', f'ask_size_{i}'])
    # Add summary metrics
    header.extend(['total_bid_size', 'total_ask_size', 'bid_ask_ratio', 'spread', 'mid_price', 'message_count'])
    
    csv_writer.writerow(header)
    
    logger.info(f"Connected to Binance - logging to {filename}")
    logger.info(f"Configuration: {CONFIG['price_levels']} price levels, symbol: {CONFIG['symbol']}")


def on_message(ws, message):
    global csv_writer, message_counter
    current_time = time.time()
    detect_data_gaps(current_time)

    try:
        message_counter += 1
        
        # Parse the JSON message from Binance
        data = json.loads(message)
        
        # Extract the order book data - BOTH are [price, quantity] format
        bids = data['b']  # List of [price, quantity] pairs
        asks = data['a']  # List of [price, quantity] pairs 
        
        # Get exchange timestamp if available
        exchange_timestamp = data.get('E', get_timestamp())  # 'E' is Binance's event time
        
        # Filter out zero quantity orders and validate data
        active_bids = []
        active_asks = []
        
        for bid in bids:
            is_valid, error_msg = validate_price_data(bid[0], bid[1])
            if is_valid and float(bid[1]) > 0:
                active_bids.append(bid)
            elif not is_valid:
                logger.warning(f"Invalid bid data: {error_msg}")
        
        for ask in asks:
            is_valid, error_msg = validate_price_data(ask[0], ask[1])
            if is_valid and float(ask[1]) > 0:
                active_asks.append(ask)
            elif not is_valid:
                logger.warning(f"Invalid ask data: {error_msg}")
        
        if active_bids and active_asks:
            # Sort bids by price (descending) and asks by price (ascending)
            active_bids.sort(key=lambda x: float(x[0]), reverse=True)
            active_asks.sort(key=lambda x: float(x[0]))
            
            # Get current timestamp
            timestamp = get_timestamp()
            
            # Prepare row data
            row = [timestamp, exchange_timestamp]
            
            # Add bid levels (or pad with zeros if fewer than configured levels)
            total_bid_size = 0
            for i in range(CONFIG['price_levels']):
                if i < len(active_bids):
                    bid_price = float(active_bids[i][0])
                    bid_size = float(active_bids[i][1])
                    total_bid_size += bid_size
                    row.extend([bid_price, bid_size])
                else:
                    row.extend([0, 0])
            
            # Add ask levels (or pad with zeros if fewer than configured levels)
            total_ask_size = 0
            for i in range(CONFIG['price_levels']):
                if i < len(active_asks):
                    ask_price = float(active_asks[i][0])
                    ask_size = float(active_asks[i][1])
                    total_ask_size += ask_size
                    row.extend([ask_price, ask_size])
                else:
                    row.extend([0, 0])
            
            # Calculate summary metrics
            best_bid_price = float(active_bids[0][0])
            best_ask_price = float(active_asks[0][0])
            spread = best_ask_price - best_bid_price
            mid_price = (best_bid_price + best_ask_price) / 2
            bid_ask_ratio = total_bid_size / total_ask_size if total_ask_size > 0 else 0
            
            # Add summary metrics to row
            row.extend([total_bid_size, total_ask_size, bid_ask_ratio, spread, mid_price, message_counter])
            
            # Write to CSV
            csv_writer.writerow(row)
            csv_file.flush()  # Force write to file
            
            # Log every 100th message to avoid spam
            if message_counter % 100 == 0:
                logger.info(f"Processed {message_counter} messages - Bid ratio: {bid_ask_ratio:.2f}, Spread: {spread:.2f}, Mid: {mid_price:.2f}")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        logger.error(f"Message content: {message[:200]}...")  # Log first 200 chars of problematic message

def on_error(ws, error):
    logger.error(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    global csv_file, connection_start_time
    
    # Properly close the file if it exists and isn't already closed
    if csv_file and not csv_file.closed:
        try:
            csv_file.flush()  # Ensure all data is written
            csv_file.close()
            logger.info("CSV file closed successfully")
        except Exception as e:
            logger.error(f"Error closing CSV file: {e}")
        finally:
            csv_file = None  # Reset the global variable
    
    if connection_start_time:
        duration = time.time() - connection_start_time
        logger.info(f"Connection closed after {duration:.1f} seconds. Total messages: {message_counter}")
    
    logger.info("Connection closed, file saved")

def run_with_reconnect():
    attempt = 1
    while True:
        try:
            logger.info(f"Starting WebSocket connection (attempt {attempt})...")
            
            # CREATE NEW WebSocket object for each connection attempt
            ws = websocket.WebSocketApp(
                f"{CONFIG['exchange_url']}{CONFIG['symbol']}@depth",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            
        except Exception as e:
            logger.error(f"Connection failed on attempt {attempt}: {e}")
            logger.info(f"Reconnecting in {CONFIG['reconnect_delay']} seconds...")
            attempt += 1
            time.sleep(CONFIG['reconnect_delay'])

def get_current_state():
    """Provide current state to utils for cleanup"""
    return csv_file, message_counter, connection_start_time

if __name__ == "__main__":
    logger.info("Starting BTC Order Book Tracker")
    logger.info(f"Configuration: {CONFIG}")
    setup_graceful_shutdown(get_current_state)  # Fixed: pass function as parameter
    run_with_reconnect()