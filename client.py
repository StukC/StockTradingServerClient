import socket

HOST = 'localhost'
PORT = 8942

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        # Prompt user for input
        user_input = input('Enter command: ')

        # Send input to server
        s.sendall(user_input.encode())

        # Receive response from server
        data = s.recv(1024).decode()

        # Print response
        print('Received:', data.strip())
