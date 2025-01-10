import MetaTrader5 as mt5
import pandas as pd
from typing import Optional
import logging


class DataFetcher:
    def __init__(self):
        # Initialize MetaTrader5 and handle potential errors
        if not mt5.initialize():
            logging.error("Failed to initialize MetaTrader5")
            raise RuntimeError("MetaTrader5 initialization failed")
        logging.info("MetaTrader5 initialized successfully")

    def fetch_data(self, symbol: str, timeframe: str, count: int = 200) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a given symbol and timeframe.

        Args:
            symbol (str): The trading symbol (e.g., "EURUSD").
            timeframe (str): The timeframe (e.g., "M1", "H1", "D1").
            count (int): The number of data points to fetch. Default is 200.

        Returns:
            Optional[pd.DataFrame]: DataFrame with time, open, high, low, close, and tick_volume.
                                    Returns None if fetching data fails.
        """
        try:
            # Get the MetaTrader5 timeframe constant
            timeframe_mt5 = getattr(mt5, f"TIMEFRAME_{timeframe}", None)
            if timeframe_mt5 is None:
                logging.error(f"Invalid timeframe: {timeframe}")
                return None

            # Fetch rates using MetaTrader5 API
            rates = mt5.copy_rates_from_pos(symbol, timeframe_mt5, 0, count)
            if rates is None or len(rates) == 0:
                logging.warning(f"No data returned for symbol: {symbol}")
                return None

            # Convert to DataFrame and format the time column
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')

            # Select relevant columns
            return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

        except AttributeError as attr_err:
            logging.error(f"Attribute error: {attr_err}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error while fetching data: {str(e)}")
            return None

    def __del__(self):
        # Shutdown MetaTrader5 on object deletion
        if mt5.shutdown():
            logging.info("MetaTrader5 shutdown successfully")
        else:
            logging.error("Failed to shut down MetaTrader5")
