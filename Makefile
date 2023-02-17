# Makefile

# Variables
PYTHON = python3
SERVER_FILE = server.py
CLIENT_FILE = client.py

# Targets
.PHONY: all
all: server client

server:
	$(PYTHON) $(SERVER_FILE)

client:
	$(PYTHON) $(CLIENT_FILE)
