import socket
import threading
from select import select
import json
import os

# Replace with your own file path
DATA_FILE = "user_data.json"

def create_sample_data():
    return {
        "users": [
            {
                "username": "user1",
                "password": "pass1",
                "balance": 1000,
                "stocks": {}
            },
            {
                "username": "user2",
                "password": "pass2",
                "balance": 2000,
                "stocks": {}
            }
        ]
    }

def load_data():
    if not os.path.exists(DATA_FILE):
        data = create_sample_data()
        save_data(data)
        return data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def handle_client(conn, addr, user_data):
    print(f"[NEW CONNECTION] {addr} connected.")
    connected = True
    while connected:
        readable, _, _ = select([conn], [], [], 1)
        if not readable:
            continue

        data = conn.recv(1024).decode("utf-8")
        if not data:
            break

        command, *args = data.split()
        response = process_command(command, args, user_data)
        conn.send(response.encode("utf-8"))

    conn.close()
    print(f"[DISCONNECTED] {addr} disconnected.")

def process_command(command, args, user_data):
    # Implement command processing logic based on the project requirements.
    response = f"Received command: {command}, Args: {args}"
    return response

def start():
    user_data = load_data()  # Load or create user data
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((SERVER, PORT))
    server.listen()

    print(f"[LISTENING] Server is listening on {SERVER}:{PORT}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr, user_data))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    SERVER = "127.0.0.1"
    PORT = 5050
    start()
