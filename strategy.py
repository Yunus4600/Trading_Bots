# strategy.py
import pandas as pd
import logging



def apply_strategy(data: pd.DataFrame) -> pd.DataFrame:
    """
    Apply a fast SMAC strategy optimized for 1-minute scalping.
    Uses 3 and 7 period SMAs for quicker signals.
    """
    try:
        logging.debug(f"Applying scalping strategy to data. Shape before: {data.shape}")

        # Calculate faster moving averages (3 and 7 periods)
        data['SMA_Short'] = data['close'].rolling(window=3).mean()  # 3-period SMA
        data['SMA_Long'] = data['close'].rolling(window=7).mean()  # 7-period SMA


        # Initialize signal column
        data['signal'] = None

        # Calculate crossovers
        data['crossover'] = (data['SMA_Short'] > data['SMA_Long']).astype(int)
        data['crossover_change'] = data['crossover'].diff()

        # Generate signals only on crossovers
        data.loc[data['crossover_change'] == 1, 'signal'] = 'buy'  # Golden cross
        data.loc[data['crossover_change'] == -1, 'signal'] = 'sell'  # Death cross

        # Add trend strength confirmation
        data['trend_strength'] = abs(data['SMA_Short'] - data['SMA_Long']) / data['SMA_Long'] * 100

        # Only keep signals where trend strength is sufficient
        min_trend_strength = 0.001  # 0.001% minimum trend strength
        data.loc[data['trend_strength'] < min_trend_strength, 'signal'] = None

        # Log signal generation
        if data['signal'].last_valid_index() is not None:
            last_signal = data.loc[data['signal'].last_valid_index(), 'signal']
            trend_strength = data.loc[data['signal'].last_valid_index(), 'trend_strength']
            logging.debug(f"Generated signal: {last_signal} at index {data['signal'].last_valid_index()}")
            logging.debug(f"Trend strength: {trend_strength:.4f}%")

        # Clean up intermediate columns
        data = data.drop(['crossover', 'crossover_change', 'trend_strength'], axis=1)

        logging.info("Scalping strategy applied successfully")
        return data

    except Exception as e:
        logging.error(f"Error applying strategy: {str(e)}", exc_info=True)
        return data