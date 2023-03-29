import socket
import sqlite3
import sys
import threading
import select

HOST = '127.0.0.1'
PORT = 8283
MAX_CONCURRENT_CONNECTIONS = 10
logged_in_users = set()
active_users_ips = {}

def init_database(database_name):
    conn = sqlite3.connect(database_name)
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
        # Create sample users
        sample_users = [
            ('John', 'Doe', 'John', 'John01', 'john.doe@example.com', 5000.00),
            ('Root', 'User', 'Root', 'Root01', 'Root@example.com', 0.00),
            ('Mary', 'Smith', 'Mary', 'Mary01', 'mary.smith@example.com', 6000.00),
            ('Moe', 'Doe', 'Moe', 'Moe01', 'moe.doe@example.com', 3000.00)
        ]

        c.executemany("INSERT INTO Users (first_name, last_name, user_name, password, email, usd_balance) VALUES (?, ?, ?, ?, ?, ?)", sample_users)
        conn.commit()

        # Create sample stocks
        sample_stocks = [
            ('AAPL', 'Apple Inc.', 100.0, 1),
            ('MSFT', 'Microsoft Corporation', 50.0, 1),
            ('GOOG', 'Alphabet Inc.', 200.0, 1),
            ('AAPL', 'Apple Inc.', 150.0, 2),
            ('GOOG', 'Alphabet Inc.', 50.0, 3),
            ('MSFT', 'Microsoft Corporation', 25.0, 4),
        ]

        c.executemany("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)", sample_stocks)
        conn.commit()

    return conn

def handle_login(c, username, password, session_data, client_address):
    if 'user_id' in session_data:
        return "Already logged in"

    c.execute("SELECT ID FROM Users WHERE user_name=? AND password=?", (username, password))
    user_data = c.fetchone()

    if user_data is None:
        return "403 Wrong UserID or Password"

    user_id = user_data[0]
    if user_id in logged_in_users:
        return "User is already logged in"

    session_data['user_id'] = user_id
    logged_in_users.add(user_id)
    active_users_ips[user_id] = client_address[0]

    return f"200 OK\nLogged in as {username}"

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

def handle_list(c, user_id):
    # Check if the user is a root user
    c.execute("SELECT user_name FROM Users WHERE ID=?", (user_id,))
    user_name = c.fetchone()[0]
    is_root_user = user_name.lower() == 'root'

    if is_root_user:
        # Retrieve all stock records for all users
        c.execute("SELECT Stocks.ID, stock_symbol, stock_name, stock_balance, Users.user_name FROM Stocks INNER JOIN Users ON Stocks.user_id = Users.ID")
    else:
        # Retrieve stock records only for the logged-in user
        c.execute("SELECT ID, stock_symbol, stock_name, stock_balance FROM Stocks WHERE user_id=?", (user_id,))
    
    stocks = c.fetchall()

    if not stocks:
        return "No stock records found in the Stocks database."

    # Format the stock records for output
    if is_root_user:
        stock_records = "\n".join([f"{stock_id} {stock_symbol} {stock_name} {stock_balance} {user}" for stock_id, stock_symbol, stock_name, stock_balance, user in stocks])
    else:
        stock_records = "\n".join([f"{stock_id} {stock_symbol} {stock_name} {stock_balance}" for stock_id, stock_symbol, stock_name, stock_balance in stocks])

    return f"200 OK\nThe list of records in the Stocks database{' for ' + user_name if not is_root_user else ''}:\n{stock_records}"

def handle_who(c):
    if not active_users_ips:
        return "No active users"

    c.execute("SELECT ID, user_name FROM Users WHERE ID IN ({})".format(', '.join('?' * len(active_users_ips))), tuple(active_users_ips.keys()))
    active_users_data = c.fetchall()

    active_users_info = "\n".join([f"{user_name} {active_users_ips[user_id]}" for user_id, user_name in active_users_data])

    return f"200 OK\nThe list of the active users:\n{active_users_info}"

def handle_lookup(c, stock_symbol, user_id):
    # Check if the stock exists
    c.execute("SELECT * FROM Stocks WHERE stock_symbol=?", (stock_symbol,))
    stock_data = c.fetchone()

    if stock_data is None:
        return "Stock not found"

    stock_id, stock_symbol, stock_name, stock_value, stock_change = stock_data

    return f"200 OK\nID: {stock_id}\nSymbol: {stock_symbol}\nName: {stock_name}\nValue: {stock_value}\nChange: {stock_change}"

def handle_logout(c, username, session_data):
    if 'user_id' not in session_data:
        return "Not logged in"

    c.execute("SELECT ID FROM Users WHERE user_name=?", (username,))
    user_data = c.fetchone()

    if user_data is None:
        return "User not found"

    user_id = user_data[0]
    if user_id != session_data['user_id']:
        return "User mismatch"

    logged_in_users.remove(user_id)
    del session_data['user_id']

    return "200 OK\nLogged out"

def handle_deposit(c, user_id, deposit_amount):
    # Check if user exists
    c.execute("SELECT usd_balance FROM Users WHERE ID=?", (user_id,))
    user_balance_data = c.fetchone()

    if user_balance_data is None:
        return "User doesn't exist"

    user_balance = user_balance_data[0]
    new_usd_balance = user_balance + float(deposit_amount)

    # Update user balance
    c.execute("UPDATE Users SET usd_balance=? WHERE ID=?", (new_usd_balance, user_id))

    # Commit the changes
    c.connection.commit()

    return f"Deposit successfully. New balance ${new_usd_balance:.2f}"

def client_handler(client_socket, client_address, database_name):
    conn = sqlite3.connect(database_name)
    c = conn.cursor()
    print('Connected by', client_address)

    session_data = {}
    c = conn.cursor()

    logged_out = False

    while True:
        data = client_socket.recv(1024).decode().strip()
        if not data:
            break
        command = data.split()[0].upper()
        print(f"Received command: {command} from {client_address}")

        try:
            if command == 'LOGIN':
                username, password = data.split()[1:]
                result = handle_login(c, username, password, session_data, client_address)
                client_socket.sendall(result.encode())
            elif command == 'BUY':
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
                if 'user_id' not in session_data:
                    result = "You must be logged in to use the LIST command"
                else:
                    result = handle_list(c, session_data['user_id'])
                client_socket.sendall(result.encode())
            elif command == 'WHO':
                if 'user_id' in session_data and session_data['user_id'] == 2:  # Check if the user is the root user (ID 2)
                    result = handle_who(c)
                else:
                    result = "403 Forbidden: WHO command is only allowed for the root user"
                client_socket.sendall(result.encode())
            elif command == 'LOOKUP':
                if 'user_id' not in session_data:
                    result = "You must be logged in to use the LOOKUP command"
                else:
                    stock_symbol = data.split()[1]
                    result = handle_lookup(c, stock_symbol, session_data['user_id'])
                client_socket.sendall(result.encode())
            elif command == 'DEPOSIT':
                if 'user_id' not in session_data:
                    result = "You must be logged in to use the DEPOSIT command"
                else:
                    deposit_amount = data.split()[1]
                    result = handle_deposit(c, session_data['user_id'], deposit_amount)
                client_socket.sendall(result.encode())
            elif command == 'LOGOUT':
                data_parts = data.split()
                if len(data_parts) != 2:
                    raise ValueError("Invalid arguments for LOGOUT command")
                username = data_parts[1]
                result = handle_logout(c, username, session_data)
                client_socket.sendall(result.encode())
                logged_out = True
                break
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

        # Add this block after the exception handling
        if command == 'LOGOUT' or command == 'QUIT':
            if 'user_id' in session_data:
                logged_in_users.remove(session_data['user_id'])
            break

    # Close the connection for this thread
    print('Connection closed by', client_address)
    client_socket.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print(f'Server listening on {HOST}:{PORT}...')

        database_name = 'example.db'
        init_database(database_name)
        connections = []

        while True:
            readable_sockets, _, _ = select.select([s] + connections, [], [], 1)

            for sock in readable_sockets:
                if sock is s:
                    if len(connections) < MAX_CONCURRENT_CONNECTIONS:
                        client_socket, client_address = s.accept()
                        connections.append(client_socket)
                        client_thread = threading.Thread(target=client_handler, args=(client_socket, client_address, database_name))
                        client_thread.start()
                    else:
                        print("Maximum concurrent connections reached")
                else:
                    pass

            # Remove closed connections from the connections list
            connections = [conn for conn in connections if not conn._closed]

            # Print the number of active connections
            print(f"{len(connections)} active connections")

if __name__ == '__main__':
    main()
