import socket

SERVER_PORT = 8942

# Create a socket in the Internet domain and connect it to the specified server IP address and port number
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('localhost', SERVER_PORT))

while True:
    try:
        # Send requests to the server via the socket
        command = input("Enter a command: ")

        if command == "QUIT":
            client_socket.sendall(command.encode('utf-8'))
            break

        client_socket.sendall(command.encode('utf-8'))

        # Receive responses from the server via the socket and parse the data
        response = client_socket.recv(1024).decode('utf-8')
        print(response)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        break

# Close the socket and exit the program
client_socket.close()
