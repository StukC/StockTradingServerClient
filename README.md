# Stock Trading Server and Client

This project consists of a simple stock trading server and client application. The server manages a SQLite database containing user and stock information, and the client allows users to send commands to buy, sell, check their balance, or list all stock records in the database.

## Requirements

- Python 3.6 or later
- sqlite3 (included in Python's standard library)

## Running the server and client

1. Open two terminal windows.
4. In the first terminal, navigate to the project directory
3. Run the server using the following command: `python3 server.py` or `python server.py`, depending on your system's configuration.
4. In the second terminal, navigate to the project directory
5. Run the client using the following command: `python3 client.py` or `python client.py`, depending on your system's configuration.

## Commands

The client accepts the following commands:

- `BUY <stock_symbol> <stock_amount> <price_per_stock> <user_id>`: Buy stocks for a user.
- `SELL <stock_symbol> <stock_amount> <price_per_stock> <user_id>`: Sell stocks for a user.
- `BALANCE <user_id>`: Check the USD balance of a user.
- `LIST`: List all stock records in the database.
- `QUIT`: Disconnect the client from the server.
- `SHUTDOWN`: Shut down the server (only use this command when you want to stop the server).

Please note that input validation is minimal, and the server does not provide real-time stock prices. This project is intended for educational purposes only and should not be used for actual stock trading.
