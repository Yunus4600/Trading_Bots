# main.py
import time
import logging
import signal
import sys
from data_fetch import DataFetcher
from strategy import apply_strategy
from trade import TradeExecutor
from config import SYMBOL, TIMEFRAME, TRADE_AMOUNT

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG level
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='trading_bot.log'
)


def signal_handler(sig, frame):
    logging.info("Shutting down the trading bot.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logging.info("Starting the trading bot...")
    data_fetcher = DataFetcher()
    trade_executor = TradeExecutor(TRADE_AMOUNT)
    last_check_time = None

    while True:
        try:
            current_time = time.time()

            # Log the time since last check
            if last_check_time:
                logging.debug(f"Time since last check: {current_time - last_check_time} seconds")

            # Fetch data
            logging.debug(f"Fetching data for {SYMBOL} on {TIMEFRAME} timeframe")
            data = data_fetcher.fetch_data(SYMBOL, TIMEFRAME)

            if data is not None:
                logging.debug(f"Data fetched successfully. Shape: {data.shape}")

                # Apply strategy and check for signals
                data = apply_strategy(data)
                if data is not None and 'signal' in data.columns:
                    latest_signal = data['signal'].iloc[-1]
                    logging.debug(f"Strategy applied. Latest signal: {latest_signal}")


                    # Execute trade if a valid signal is provided
                    if latest_signal in ['buy', 'sell']:
                        logging.info(f"Valid signal detected: {latest_signal}")
                        trade_executor.execute_trade(latest_signal, SYMBOL)
                    else:
                        logging.debug("No valid signal in current data")

                    # Manage existing trades
                    logging.debug("Checking existing trades...")
                    trade_executor.manage_trades(SYMBOL)
                else:
                    logging.warning("No signal column in strategy output")

            # Update last check time
            last_check_time = current_time

            # Sleep for a shorter interval (10 seconds)
            logging.debug("Sleeping for 10 seconds...")
            time.sleep(10)

        except Exception as e:
            logging.error(f"Error in main loop: {str(e)}", exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()