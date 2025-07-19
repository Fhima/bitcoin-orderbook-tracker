import signal
import sys
import time
import datetime
import logging

logger = logging.getLogger(__name__)  # Added missing logger
last_message_time = None  # Added missing global

def setup_graceful_shutdown(get_cleanup_data_func):  # Fixed: expect function parameter
    """
    Setup graceful shutdown, with a callback to get data from main file
    """
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Initiating graceful shutdown...")
        
        # Call the function provided by main file to get current state
        csv_file, message_counter, connection_start_time = get_cleanup_data_func()
        
        # Now we can clean up with the actual data
        cleanup_and_exit(csv_file, message_counter, connection_start_time)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Graceful shutdown handler registered")

def cleanup_and_exit(csv_file, message_counter, connection_start_time):
    """
    Clean shutdown with all the data we need passed in as parameters
    """
    try:
        if csv_file and not csv_file.closed:
            csv_file.flush()
            csv_file.close()
            logger.info("CSV file closed successfully")
        
        if connection_start_time:
            total_duration = time.time() - connection_start_time
            messages_per_second = message_counter / total_duration if total_duration > 0 else 0
            logger.info(f"Final statistics:")
            logger.info(f"  Total runtime: {total_duration:.1f} seconds") 
            logger.info(f"  Total messages processed: {message_counter}")
            logger.info(f"  Average messages per second: {messages_per_second:.2f}")
    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        sys.exit(0)

def detect_data_gaps(current_time):
    """
    DATA GAP DETECTION ENHANCEMENT - Core Logic
    
    This function monitors the timing between messages to detect data gaps.
    
    Why this matters: In financial data, gaps can indicate:
    - Network connectivity issues
    - Exchange maintenance or problems
    - Your system being overloaded
    - Data feed interruptions
    
    Think of it like a heartbeat monitor - if the heartbeat stops or becomes
    irregular, you need to know about it immediately.
    
    Args:
        current_time: The timestamp when the current message was received
    """
    global last_message_time
    
    # Import CONFIG from main module
    from __main__ import CONFIG  # Fixed: get CONFIG from main
    
    if last_message_time is not None:
        # Calculate the time gap since the last message
        time_gap = current_time - last_message_time
        
        # Check if the gap exceeds our threshold
        if time_gap > CONFIG['gap_threshold_seconds']:
            logger.warning(f"DATA GAP DETECTED: {time_gap:.2f} seconds between messages")
            logger.warning(f"Gap occurred between {datetime.datetime.fromtimestamp(last_message_time)} and {datetime.datetime.fromtimestamp(current_time)}")
            
            # This is important: we're not just logging the gap, we're providing
            # context about when it happened so you can correlate it with
            # market events, network issues, or other external factors
            
        elif time_gap > CONFIG['normal_message_interval'] * 2:
            # Log smaller gaps that might still be concerning
            # This helps you understand the quality of your data feed
            logger.info(f"Minor delay detected: {time_gap:.2f} seconds between messages")
    
    # Update the last message time for the next comparison
    last_message_time = current_time