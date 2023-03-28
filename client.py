import socket

HOST = 'localhost'
PORT = 8283

def main():
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
            print('Received: ', data.strip())

            # If the server sends a "200 OK" response after a QUIT or LOGOUT command, close the client
            if user_input.strip().upper() == "QUIT" and data.strip() == "200 OK":
                break
            if user_input.strip().upper() == "LOGOUT" and data.strip() == "200 OK":
                break

if __name__ == '__main__':
    main()
