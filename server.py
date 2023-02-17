import socket
import sqlite3
import sys

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 8942        # Port to listen on (non-privileged ports are > 1023)

# Connect to database and create tables if they don't exist
conn = sqlite3.connect('example.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS Users
             (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
             first_name TEXT, 
             last_name TEXT, 
             user_name TEXT NOT NULL, 
             password TEXT,          
             usd_balance REAL NOT NULL)''')
c.execute('''CREATE TABLE IF NOT EXISTS Stocks
             (ID INTEGER PRIMARY KEY AUTOINCREMENT, 
             stock_symbol TEXT NOT NULL, 
             stock_name TEXT NOT NULL, 
             stock_balance REAL, 
             user_id INTEGER, 
             FOREIGN KEY(user_id) REFERENCES Users(ID))''')

# Insert sample data into Users table
c.execute("INSERT INTO Users (first_name, last_name, user_name, password, usd_balance) VALUES (?, ?, ?, ?, ?)",
          ('John', 'Doe', 'jdoe', 'password123', 5000.00))
c.execute("INSERT INTO Users (first_name, last_name, user_name, password, usd_balance) VALUES (?, ?, ?, ?, ?)",
          ('Jane', 'Doe', 'jane_doe', 'letmein', 10000.00))
conn.commit()

# Insert sample data into Stocks table
c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
          ('AAPL', 'Apple Inc.', 100, 1))
c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
          ('MSFT', 'Microsoft Corporation', 50, 2))
c.execute("INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, ?, ?, ?)",
          ('GOOG', 'Alphabet Inc.', 200, 2))
conn.commit()
# Listen for incoming connections
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f'Server listening on {HOST}:{PORT}...')
    conn, addr = s.accept()
    with conn:
        print('Connected by', addr)
        while True:
            data = conn.recv(1024).decode().strip()
            if not data:
                break
            command = data.split()[0].upper()
            if command == 'BUY':
                # Parse the arguments and check for errors
                try:
                    symbol, amount, price, user_id = data.split()[1:]
                    amount = float(amount)
                    price = float(price)
                    user_id = int(user_id)
                except ValueError:
                    conn.sendall(b'Invalid BUY command')
                    continue

                # Retrieve the user from the database
                c.execute("SELECT * FROM Users WHERE ID = ?", (user_id,))
                user = c.fetchone()
                if not user:
                    conn.sendall(b'User does not exist')
                    continue

                # Calculate the total cost of the purchase and check the user's balance
                total_cost = amount * price
                if user[5] < total_cost:
                    conn.sendall(b'Not enough balance')
                    continue

                # Deduct the cost of the purchase from the user's balance
                new_balance = user[5] - total_cost
                c.execute("UPDATE Users SET usd_balance = ? WHERE ID = ?", (new_balance, user_id))

                # Check if the user already owns the stock being purchased
                c.execute("SELECT * FROM Stocks WHERE user_id = ? AND stock_symbol = ?", (user_id, symbol))
                stock = c.fetchone()
                if stock:
                    # Update the balance of the existing stock
                    new_stock_balance = stock[3] + amount
                    c.execute("UPDATE Stocks SET stock_balance = ? WHERE ID = ?", (new_stock_balance, stock[0]))
                else:
                    # Add a new stock record for the user
                    c.execute(
                        "INSERT INTO Stocks (stock_symbol, stock_name, stock_balance, user_id) VALUES (?, '', ?, ?)",
                        (symbol, amount, user_id))

                # Commit the changes to the database
                conn.commit()

                # Send the response to the client
                response = f'200 OK\nBOUGHT: New balance: {amount:.2f} {symbol}. USD balance ${new_balance:.2f}'.encode()
                conn.sendall(response)
                pass
            elif command == 'SELL':
                # Parse the arguments and check for errors
                try:
                    symbol, amount, price, user_id = data.split()[1:]
                    amount = float(amount)
                    price = float(price)
                    user_id = int(user_id)
                except ValueError:
                    conn.sendall(b'Invalid SELL command')
                    continue

                # Retrieve the user from the database
                c.execute("SELECT * FROM Users WHERE ID = ?", (user_id,))
                user = c.fetchone()
                if not user:
                    conn.sendall(b'User does not exist')
                    continue

                # Check if the user owns the stock being sold
                c.execute("SELECT * FROM Stocks WHERE user_id = ? AND stock_symbol = ?", (user_id, symbol))
                stock = c.fetchone()
                if not stock:
                    conn.sendall(b'User does not own this stock')
                    continue

                # Check if the user has enough stocks to sell
                if stock[3] < amount:
                    conn.sendall(b'Not enough stocks to sell')
                    continue

                # Update the user's USD balance and stock balance
                total_sale = amount * price
                new_balance = user[5] + total_sale
                new_stock_balance = stock[3] - amount
                c.execute("UPDATE Users SET usd_balance = ? WHERE ID = ?", (new_balance, user_id))
                c.execute("UPDATE Stocks SET stock_balance = ? WHERE ID = ?", (new_stock_balance, stock[0]))

                # Commit the changes to the database
                conn.commit()

                # Send the response to the client
                response = f'200 OK\nSOLD: New balance: {amount:.2f} {symbol}. USD balance ${new_balance:.2f}'.encode()
                conn.sendall(response)
                pass
            elif command == 'BALANCE':
                args = data.split()[1:]
                if len(args) != 1:
                    conn.sendall(b'Invalid BALANCE command')
                else:
                    user_id = int(args[0])

                    # Check if user exists
                    c.execute("SELECT * FROM Users WHERE ID = ?", (user_id,))
                    user = c.fetchone()
                    if not user:
                        conn.sendall(b'User does not exist')
                        continue

                    # Send response to client
                    response = f'200 OK\nBalance for user {user[2]} {user[3]}: ${user[5]:.2f}'.encode()
                    conn.sendall(response)
                pass
            elif command == 'LIST':
                # Retrieve all stocks from the Stocks table
                c.execute("SELECT * FROM Stocks")
                stocks = c.fetchall()

                # Generate response string
                response = ''
                for stock in stocks:
                    response += f'{stock[1]} {stock[3]:.1f}\n'
                response = response.strip().encode()

                # Send response to client
                conn.sendall(response)
                pass
            elif command == 'SHUTDOWN':
                # Close all open sockets and database connection
                conn.close()

                sys.exit()

            elif command == 'QUIT':
                # Send QUIT command to server
                conn.sendall(b'QUIT\n')

                # Close socket and terminate program
                s.close()
                sys.exit()
                break
            else:
                conn.sendall(b'Invalid command')
        print('Connection closed.')
