import socket
import sqlite3
import sys
import threading

HOST = '127.0.0.1'
PORT = 8283

def init_database():
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Users
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 first_name TEXT,
                 last_name TEXT,
                 user_name TEXT NOT NULL,
                 password TEXT,
                 email TEXT NOT NULL,
                 usd_balance REAL NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Stocks
                 (ID INTEGER PRIMARY KEY AUTOINCREMENT,
                 stock_symbol TEXT NOT NULL,
                 stock_name TEXT NOT NULL,
                 stock_balance REAL,
                 user_id INTEGER,
                 FOREIGN KEY(user_id) REFERENCES Users(ID))''')

    # Check if there are any users
    c.execute("SELECT COUNT(*) FROM Users")
    user_count = c.fetchone()[0]

    if user_count == 0:
        # Create a sample user if there are no users
        c.execute("INSERT INTO Users (first_name, last_name, user_name, password, email, usd_balance) VALUES (?, ?, ?, ?, ?, ?)",
                  ('John', 'Doe', 'jdoe', 'password123', 'john.doe@example.com', 5000.00))
        conn.commit()

    # Check if there are any stock records
    c.execute("SELECT COUNT(*) FROM Stocks")
    stock_count = c.fetchone()[0]

    if stock_count == 0:
        # Get the user ID for the sample user
        c.execute("SELECT ID FROM Users WHERE user_name=?", ('jdoe',))
        user_id = c.fetchone()[0]

        # Insert sample data into Stocks table
        c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
                  ('AAPL', 'Apple Inc.', 100, user_id))
        c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
                  ('MSFT', 'Microsoft Corporation', 50, user_id))
        c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
                  ('GOOG', 'Alphabet Inc.', 200, user_id))
        conn.commit()

    return conn

def handle_buy(c, stock_symbol, stock_amount, price_per_stock, user_id):
    # Check if user exists
    c.execute("SELECT usd_balance FROM Users WHERE ID=?", (user_id,))
    user_balance_data = c.fetchone()

    if user_balance_data is None:
        return "User doesn't exist"

    user_balance = user_balance_data[0]
    stock_price = float(stock_amount) * float(price_per_stock)

    if user_balance < stock_price:
        return "Not enough balance"

    new_usd_balance = user_balance - stock_price

    # Update user balance
    c.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (new_usd_balance, user_id))

    # Check if the stock already exists for the user
    c.execute("SELECT ID, stock_balance FROM Stocks WHERE user_id=? AND stock_symbol=?", (user_id, stock_symbol))
    stock_data = c.fetchone()

    if stock_data is None:
        # Create a new record in the Stocks table
        c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
                  (stock_symbol, stock_symbol, stock_amount, user_id))
    else:
        # Update the existing record in the Stocks table
        stock_id, stock_balance = stock_data
        new_stock_balance = float(stock_balance) + float(stock_amount)
        c.execute("UPDATE Stocks SET stock_balance=? WHERE ID=?", (new_stock_balance, stock_id))

    # Commit the changes
    c.connection.commit()

    return f"200 OK\nBOUGHT: New balance: {stock_amount} {stock_symbol}. USD balance ${new_usd_balance:.2f}"

def handle_sell(c, stock_symbol, stock_amount, price_per_stock, user_id):
    # Check if user exists and has the stock
    c.execute("SELECT Users.ID, Users.usd_balance, Stocks.ID, Stocks.stock_balance "
              "FROM Users INNER JOIN Stocks ON Users.ID = Stocks.user_id "
              "WHERE Users.ID=? AND Stocks.stock_symbol=?", (user_id, stock_symbol))
    user_stock_data = c.fetchone()

    if user_stock_data is None:
        return "User doesn't exist or doesn't have the specified stock"

    user_id, user_balance, stock_id, stock_balance = user_stock_data
    stock_amount = float(stock_amount)

    if stock_balance < stock_amount:
        return "Not enough stocks to sell"

    stock_price = stock_amount * float(price_per_stock)
    new_usd_balance = user_balance + stock_price
    new_stock_balance = stock_balance - stock_amount

    # Update user balance and stock balance
    c.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (new_usd_balance, user_id))
    c.execute("UPDATE Stocks SET stock_balance=? WHERE ID=?", (new_stock_balance, stock_id))

    # Commit the changes
    c.connection.commit()

    return f"200 OK\nSOLD: New balance: {new_stock_balance} {stock_symbol}. USD balance ${new_usd_balance:.2f}"

def handle_balance(c, user_id):
    # Check if user exists
    c.execute("SELECT first_name, last_name, usd_balance FROM Users WHERE ID=?", (user_id,))
    user_data = c.fetchone()

    if user_data is None:
        return "User doesn't exist"

    first_name, last_name, usd_balance = user_data

    return f"200 OK\nBalance for user {first_name} {last_name}: ${usd_balance:.2f}"

def handle_list(c):
    # Retrieve all stock records
    c.execute("SELECT ID, stock_symbol, stock_name, stock_balance, user_id FROM Stocks")
    stocks = c.fetchall()

    if not stocks:
        return "No stock records found in the Stocks database."

    # Format the stock records for output
    stock_records = "\n".join([f"{stock_id} {stock_symbol} {stock_name} {stock_balance} {user_id}" for stock_id, stock_symbol, stock_name, stock_balance, user_id in stocks])

    return f"200 OK\nThe list of records in the Stocks database:\n{stock_records}"

def client_handler(client_socket, client_address):
    print('Connected by', client_address)

    # Create a new connection and cursor for each thread
    conn = init_database()
    c = conn.cursor()

    while True:
        data = client_socket.recv(1024).decode().strip()
        if not data:
            break
        command = data.split()[0].upper()
        print(f"Received command: {command} from {client_address}")

        try:
            if command == 'BUY':
                stock_symbol, stock_amount, price, user_id = data.split()[1:]
                result = handle_buy(c, stock_symbol, float(stock_amount), float(price), int(user_id))
                client_socket.sendall(result.encode())
            elif command == 'SELL':
                stock_symbol, stock_amount, price, user_id = data.split()[1:]
                result = handle_sell(c, stock_symbol, float(stock_amount), float(price), int(user_id))
                client_socket.sendall(result.encode())
            elif command == 'BALANCE':
                data_parts = data.split()
                if len(data_parts) != 2:
                    raise ValueError("Invalid arguments for BALANCE command")

                user_id = data_parts[1]
                result = handle_balance(c, int(user_id))
                client_socket.sendall(result.encode())
            elif command == 'LIST':
                if len(data.split()) != 1:
                    raise ValueError("Invalid arguments for LIST command")

                result = handle_list(c)
                client_socket.sendall(result.encode())
            elif command == 'SHUTDOWN':
                client_socket.sendall(b'200 OK\n')
                break
            elif command == 'QUIT':
                client_socket.sendall(b'200 OK\n')
                break
            else:
                raise ValueError(f"Invalid command: {command}. Please use BUY, SELL, BALANCE, LIST, or SHUTDOWN.")
        except ValueError as e:
            client_socket.sendall(str(e).encode())

    # Close the connection for this thread
    conn.close()
    print('Connection closed by', client_address)
    client_socket.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}...')

        while True:
            client_socket, client_address = s.accept()
            client_thread = threading.Thread(target=client_handler, args=(client_socket, client_address))
            client_thread.start()

    print("Server shutdown.")

if __name__ == '__main__':
    main()