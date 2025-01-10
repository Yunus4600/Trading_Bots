import MetaTrader5 as mt5
import logging
from datetime import datetime


class TradeExecutor:
    def __init__(self, trade_amount: float):
        self.trade_amount = trade_amount
        self.active_trades = {}
        self.last_signal = None

    def calculate_profit(self, position, current_price):
        """Calculate current profit/loss in dollars."""
        if position.type == mt5.ORDER_TYPE_BUY:
            profit = (current_price - position.price_open) * position.volume * 100000  # Assuming standard lot size
        else:  # SELL position
            profit = (position.price_open - current_price) * position.volume * 100000
        return profit

    def has_open_positions(self, symbol: str) -> bool:
        """Check if there are any open positions for the symbol."""
        positions = mt5.positions_get(symbol=symbol)
        return positions is not None and len(positions) > 0

    def get_position_type(self, symbol: str) -> str:
        """Get the type of open position (buy/sell) if any exists."""
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None and len(positions) > 0:
            return "buy" if positions[0].type == mt5.ORDER_TYPE_BUY else "sell"
        return None

    # Inside the TradeExecutor class, modify manage_trades method:

    def manage_trades(self, symbol: str):
        """Monitor and manage open trades based on time and profit conditions."""
        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None or len(positions) == 0:
                return

            current_time = datetime.now()
            current_tick = mt5.symbol_info_tick(symbol)

            for position in positions:
                if position.ticket not in self.active_trades:
                    continue

                start_time = self.active_trades[position.ticket]['start_time']
                time_open = (current_time - start_time).total_seconds()

                # Get current profit
                current_price = current_tick.bid if position.type == mt5.ORDER_TYPE_BUY else current_tick.ask
                profit = self.calculate_profit(position, current_price)

                # Check if 1 minute has passed (changed from 2 minutes for faster scalping)
                if time_open >= 60:  # 1 minute = 60 seconds
                    if profit > 0:
                        # If in profit after 1 minute, close immediately
                        logging.info(
                            f"Closing profitable position {position.ticket} after 1 minute. Profit: ${profit:.2f}")
                        self.close_trade(symbol, position_ticket=position.ticket)
                    else:
                        # If in loss after 1 minute, use tighter stop loss
                        if profit <= -5:  # Maximum stop loss of $5 (reduced from $10)
                            logging.info(f"Closing position {position.ticket} at stop loss. Loss: ${profit:.2f}")
                            self.close_trade(symbol, position_ticket=position.ticket)
                        elif profit >= 2:  # Keep $2 profit target
                            logging.info(f"Closing position {position.ticket} at profit target. Profit: ${profit:.2f}")
                            self.close_trade(symbol, position_ticket=position.ticket)

        except Exception as e:
            logging.error(f"Error in manage_trades: {str(e)}")

    def close_trade(self, symbol: str, position_type: str = None, position_ticket: int = None):
        """Closes specific or all positions of a given type for a symbol."""
        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None or len(positions) == 0:
                logging.warning(f"No open positions found for {symbol}")
                return

            for position in positions:
                # Skip if not the specified ticket (if provided)
                if position_ticket is not None and position.ticket != position_ticket:
                    continue

                # Skip if not the specified type (if provided)
                if position_type is not None:
                    if (position.type == mt5.ORDER_TYPE_BUY and position_type != "buy") or \
                            (position.type == mt5.ORDER_TYPE_SELL and position_type != "sell"):
                        continue

                order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(
                    symbol).ask

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": position.volume,
                    "type": order_type,
                    "position": position.ticket,
                    "price": price,
                    "deviation": 30,
                    "magic": position.magic,
                    "comment": "Closing position"
                }

                result = mt5.order_send(request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logging.error(f"Failed to close position {position.ticket}: {result}")
                else:
                    logging.info(f"Closed position {position.ticket}: {result}")
                    if position.ticket in self.active_trades:
                        del self.active_trades[position.ticket]

        except Exception as e:
            logging.error(f"Error while closing trade: {str(e)}")

    def execute_trade(self, signal: str, symbol: str):
        """Executes a trade based on the given signal, with position checks."""
        # Check if signal is the same as last executed signal
        if signal == self.last_signal:
            logging.info(f"Ignoring {signal} signal - same as previous signal")
            return

        # Check current positions
        current_position_type = self.get_position_type(symbol)

        # If we have an open position
        if current_position_type is not None:
            # If signal matches our current position, do nothing
            if signal == current_position_type:
                logging.info(f"Ignoring {signal} signal - already in {current_position_type} position")
                return
            # If signal is opposite, we'll close and open new position
            logging.info(f"Closing {current_position_type} position to open {signal} position")

        # Execute the trade logic
        if signal == "buy":
            self.close_trade(symbol, "sell")  # Close any existing SELL positions

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.trade_amount,
                "type": mt5.ORDER_TYPE_BUY,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": 30,
            }

        elif signal == "sell":
            self.close_trade(symbol, "buy")  # Close any existing BUY positions

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": self.trade_amount,
                "type": mt5.ORDER_TYPE_SELL,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 30,
            }

        else:
            logging.warning("Invalid signal received.")
            return

        # Send the order
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logging.info(f"Opened {signal.upper()} position: {result}")
            # Store trade info
            self.active_trades[result.order] = {
                'start_time': datetime.now(),
                'entry_price': request['price']
            }
            self.last_signal = signal  # Update last executed signal
        else:
            logging.error(f"Trade operation failed: {result}")

        return result