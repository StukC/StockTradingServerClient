import socket
import sys

# Define constants
SERVER_PORT = 8942
USER_FILE = "data.txt"

# Open user file and read data into memory
try:
    with open(USER_FILE, 'r') as file:
        user_data = file.read().splitlines()
except FileNotFoundError:
    sys.exit(f"Error: {USER_FILE} not found")

# Check if there is at least one user in the user table. If not, create a new user and write the record to the file
if len(user_data) == 0:
    user_data.append("ID,email,first_name,last_name,username,password,usd_balance")
    new_user = "1,jdoe@example.com,John,Doe,jdoe,pass123,1000.00"
    user_data.append(new_user)
    with open(USER_FILE, 'w') as file:
        file.write('\n'.join(user_data))

# Create a socket and bind to the server port number
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('localhost', SERVER_PORT))

# Listen for incoming connections and accept the first one
server_socket.listen(1)
print(f"Server listening on port {SERVER_PORT}...")
client_socket, client_address = server_socket.accept()
print(f"Connected by {client_address}")

# Loop to receive and process client requests
while True:
    # Receive data from client and parse based on command type
    data = client_socket.recv(1024).decode().strip()
    if not data:
        break
    command, *params = data.split()

    # Process the request and update user and stock data
    if command == "BUY":
        # Handle buy request
        pass
    elif command == "SELL":
        # Handle sell request
        pass
    elif command == "BALANCE":
        # Handle list request
        pass
    elif command == "LIST":
        # Handle list request
        pass
    elif command == "SHUTDOWN":
        # Handle shutdown request and break from loop
        break
    else:
        # Unknown command, send error response
        response = "Error: unknown command"
        client_socket.send(response.encode())
        continue

    # Send response to client
    response = "Response data"
    client_socket.send(response.encode())

# Clean up and exit
client_socket.close()
server_socket.close()
