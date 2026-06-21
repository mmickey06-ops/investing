"""
Alpaca paper trading connection test.
Connects to the paper trading API, checks account status, and places a small test trade.
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

API_KEY = "PKPL7V2SCVE4ZU26MB3JAASRRQ"
API_SECRET = "563s8JGbAjC7F4TSSFioXreLp9LcrYewT1LNKhUH8c4H"
PAPER = True  # Paper trading endpoint

def main():
    # Connect
    client = TradingClient(API_KEY, API_SECRET, paper=PAPER)
    data_client = StockHistoricalDataClient(API_KEY, API_SECRET)

    # Account info
    account = client.get_account()
    print("=== Account Status ===")
    print(f"Status:          {account.status}")
    print(f"Buying Power:    ${float(account.buying_power):,.2f}")
    print(f"Cash:            ${float(account.cash):,.2f}")
    print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"Equity:          ${float(account.equity):,.2f}")
    print(f"Day Trade Count: {account.daytrade_count}")
    print()

    # Get current price of AAPL
    symbol = "AAPL"
    quote_req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quote = data_client.get_stock_latest_quote(quote_req)
    ask_price = quote[symbol].ask_price
    print(f"=== Latest Quote: {symbol} ===")
    print(f"Ask Price: ${ask_price}")
    print()

    # Place a small test market order (1 share of AAPL)
    print(f"=== Placing Test Market Order: Buy 1 share of {symbol} ===")
    order_req = MarketOrderRequest(
        symbol=symbol,
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    order = client.submit_order(order_req)
    print(f"Order ID:     {order.id}")
    print(f"Symbol:       {order.symbol}")
    print(f"Qty:          {order.qty}")
    print(f"Side:         {order.side}")
    print(f"Type:         {order.order_type}")
    print(f"Status:       {order.status}")
    print(f"Submitted at: {order.submitted_at}")
    print()

    # List open positions
    positions = client.get_all_positions()
    print("=== Current Positions ===")
    if positions:
        for p in positions:
            print(f"  {p.symbol}: {p.qty} shares @ avg ${float(p.avg_entry_price):.2f} | P&L: ${float(p.unrealized_pl):.2f}")
    else:
        print("  No open positions yet (order may be pending market open).")

    print("\nTest complete.")

if __name__ == "__main__":
    main()
