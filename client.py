import socket
import threading
from select import select

def receive(server):
    while True:
        readable, _, _ = select([server], [], [], 1)
        if not readable:
            continue

        msg = server.recv(1024).decode("utf-8")
        if msg:
            print(msg)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((SERVER, PORT))

    receive_thread = threading.Thread(target=receive, args=(server,))
    receive_thread.start()

    while True:
        command = input("Enter command: ")
        server.send(command.encode("utf-8"))
        if command.lower() == "quit":
            break

    server.close()

if __name__ == "__main__":
    SERVER = "127.0.0.1"
    PORT = 5050
    main()
