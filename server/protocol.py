import re
import socket
from typing import Literal

import encryption_utils

# --- Constants ---
LENGTH_FIELD_SIZE = 6
PORT = 5555
SERVER_ADDRESS = "127.0.0.1"
ERROR_MESSAGE = "ERROR"
SELECT_TIMEOUT = 0.5 # in seconds

# response codes
RESPONSE_HELLO = 1
RESPONSE_OK = 2
RECIPIENT_NOT_FOUND = 3

RESPONSE_HANDSHAKE = 9
RESPONSE_USER_EXISTS = 4
RESPONSE_USER_DOES_NOT_EXIST = 5
RESPONSE_INCORRECT_PASSWORD = 6
RESPONSE_CORRECT_PASSWORD = 7
RESPONSE_CREATED_USER = 8

# message commands
COMMAND_BROADCAST = 1
COMMAND_PRIVATE = 2
COMMAND_HELLO = 6
COMMAND_SET_USERNAME = 7
COMMAND_SET_PASSWORD = 8
COMMAND_HANDSHAKE = 9

# message types
MESSAGE_TEXT = 0
MESSAGE_VOICE = 1

# --- helper Functions ---

def _recv_fixed(sock: socket.socket, size: int) -> str:
    """
    Read exactly `size` bytes or raise ConnectionError if connection closes prematurely.
    :param sock: the socket
    :param size: the number of bytes (aka chars) to read from the socket
    :return: the string that was read
    """
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:  # connection closed
            raise ConnectionError("Connection closed while reading fixed size data")
        data += chunk
    return data.decode()


def _pad_with_length(data: str) -> str:
    """
    Attach length prefix to string (LENGTH_FIELD_SIZE digits).
    :param data: the data to be padded
    :return: the string with LENGTH_FIELD_SIZE bytes that represent the length of it at the start.
    """
    return str(len(data)).zfill(LENGTH_FIELD_SIZE) + data

# --- Protocol: Create Messages ---

def create_user_msg_handshake(key: str) -> bytes:
    """
    Client → Server. Handshake message.
    :param key: the key to send
    :return: the bytes to send via the socket later on
    """
    return (str(COMMAND_HANDSHAKE) + str(MESSAGE_TEXT) + _pad_with_length(key)).encode()

def create_user_msg_set_username(username: str, encryption_enabled=False, AES_key=None) -> bytes:
    """
    Client → Server. Set username message.
    :param username: the username
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param AES_key: The key to decrypt the client's message
    :return: the bytes to send via the socket later on
    """
    if not (encryption_enabled and AES_key):
        return (str(COMMAND_SET_USERNAME) + str(MESSAGE_TEXT) + _pad_with_length(username)).encode()

    # inner payload: pad(username)
    inner = _pad_with_length(username)
    cipher_bytes = encryption_utils.encrypt_AES(inner, AES_key)
    encrypted_hex = cipher_bytes.hex()
    outer = str(COMMAND_SET_USERNAME) + str(MESSAGE_TEXT) + _pad_with_length(encrypted_hex)
    return outer.encode()

def create_user_msg_set_password(username: str, password: str, encryption_enabled=False, AES_key=None) -> bytes:
    """
    Client → Server. Set username message.
    :param username: the username
    :param password: the password
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param AES_key: The key to decrypt the client's message
    :return: the bytes to send via the socket later on
    """
    if not (encryption_enabled and AES_key):
        return (str(COMMAND_SET_PASSWORD) + str(MESSAGE_TEXT) + _pad_with_length(username) + _pad_with_length(password)).encode()

    # inner payload: pad(username) + pad(password)
    inner = _pad_with_length(username) + _pad_with_length(password)
    cipher_bytes = encryption_utils.encrypt_AES(inner, AES_key)
    encrypted_hex = cipher_bytes.hex()
    outer = str(COMMAND_SET_PASSWORD) + str(MESSAGE_TEXT) + _pad_with_length(encrypted_hex)
    return outer.encode()

def create_user_msg_broadcast(username: str, message_type: Literal[0, 1], data: str, encryption_enabled=False, AES_key=None) -> bytes:
    """
    Client → Server. Broadcast message.
    :param username: the username
    :param message_type: The type of the message (0 = text message, 1 = voice message)
    :param data: the data to send
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param AES_key: The key to decrypt the client's message
    :return: the bytes to send via the socket later on
    """
    if not (encryption_enabled and AES_key):
        return (str(COMMAND_BROADCAST) + str(message_type) + _pad_with_length(username)
                + _pad_with_length(data)).encode()

    # inner payload: pad(username) + pad(message)
    inner = _pad_with_length(username) + _pad_with_length(data)
    cipher_bytes = encryption_utils.encrypt_AES(inner, AES_key)
    encrypted_hex = cipher_bytes.hex()
    outer = str(COMMAND_BROADCAST) + str(message_type) + _pad_with_length(encrypted_hex)
    return outer.encode()


def create_user_msg_private(username: str, recipient: str, message_type: Literal[0, 1], data: str,
                            encryption_enabled=False, AES_key=None) -> bytes:
    """
    Client → Server. Private message.
    :param username: the sender username
    :param recipient: the recipient username
    :param message_type: The type of the message (0 = text message, 1 = voice message)
    :param data: the data to send
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param AES_key: The key to decrypt the client's message
    :return: the bytes to send via the socket later on
    """
    if not (encryption_enabled and AES_key):
        return (str(COMMAND_PRIVATE) + str(message_type) + _pad_with_length(username) + _pad_with_length(recipient)
                + _pad_with_length(data)).encode()

    inner = _pad_with_length(username) + _pad_with_length(recipient) + _pad_with_length(data)
    cipher_bytes = encryption_utils.encrypt_AES(inner, AES_key)
    encrypted_hex = cipher_bytes.hex()
    outer = str(COMMAND_PRIVATE) + str(message_type) + _pad_with_length(encrypted_hex)
    return outer.encode()


def create_server_msg(code: int, message_type: Literal[0, 1], data: str,
                      encryption_enabled=False, encryption_key=None) -> bytes:
    """
    Server → Client. Private message to the client.
    :param code: The response code
    :param message_type: The type of the message.
    :param data: the data to send
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param encryption_key: The key to decrypt the client's message
    :return: the bytes to send via the socket later on
    """
    if not encryption_enabled:
        return (str(code) + str(message_type) + _pad_with_length(data)).encode()

    padded_message = _pad_with_length(data)
    cipher_bytes = encryption_utils.encrypt_AES(padded_message, encryption_key)
    encrypted_hex = cipher_bytes.hex()
    return (str(code) + str(message_type) + _pad_with_length(encrypted_hex)).encode()


# --- Protocol: Parse Messages ---
def recv_client_msg(sock: socket.socket, encryption_enabled=False, encryption_key=None):
    """
    Read a message from a client.
    :param sock: the client's socket
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param encryption_key: The key to decrypt the client's message
    :return: (success: bool, command: int | None, message_type: int, params: dict | None)
    """
    try:
        command = int(_recv_fixed(sock, 1))  # one digit command
        message_type = int(_recv_fixed(sock, 1))  # one digit command

        if command == COMMAND_HANDSHAKE:
            # RSA public key arrives as PEM string
            key_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
            RSA_key_pem = _recv_fixed(sock, key_length)
            return True, command, message_type, {"RSA_key": RSA_key_pem}

        elif command == COMMAND_SET_USERNAME:
            payload_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
            payload = _recv_fixed(sock, payload_length)

            if not encryption_enabled:
                return True, command, message_type, {"username": payload}

            cipher_bytes = bytes.fromhex(payload)
            padded_plain = encryption_utils.decrypt_AES(cipher_bytes, encryption_key)
            username_length = int(padded_plain[:LENGTH_FIELD_SIZE])
            username = padded_plain[LENGTH_FIELD_SIZE:LENGTH_FIELD_SIZE + username_length]
            return True, command, message_type, {"username": username}

        elif command == COMMAND_SET_PASSWORD:
            if not encryption_enabled:
                username_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                username = _recv_fixed(sock, username_length)

                password_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                password = _recv_fixed(sock, password_length)
                return True, command, message_type, {"username": username, "password": password}
            else:
                payload_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                payload = _recv_fixed(sock, payload_length)

                cipher_bytes = bytes.fromhex(payload)
                padded_plain = encryption_utils.decrypt_AES(cipher_bytes, encryption_key)

                username_length = int(padded_plain[:LENGTH_FIELD_SIZE])
                username = padded_plain[LENGTH_FIELD_SIZE:LENGTH_FIELD_SIZE + username_length]
                password_starts_at = username_length + LENGTH_FIELD_SIZE
                password_length = int(padded_plain[password_starts_at: password_starts_at + LENGTH_FIELD_SIZE])
                password = padded_plain[password_starts_at + LENGTH_FIELD_SIZE:]
                return True, command, message_type, {"username": username, "password": password}

        elif command == COMMAND_BROADCAST:
            if not encryption_enabled:
                username_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                username = _recv_fixed(sock, username_length)
                message_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                message = _recv_fixed(sock, message_length)
                return True, command, message_type, {"username": username, "message": message}
            else:
                payload_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                payload = _recv_fixed(sock, payload_length)

                cipher_bytes = bytes.fromhex(payload)
                padded_plain = encryption_utils.decrypt_AES(cipher_bytes, encryption_key)

                username_length = int(padded_plain[:LENGTH_FIELD_SIZE])
                username = padded_plain[LENGTH_FIELD_SIZE:LENGTH_FIELD_SIZE + username_length]
                message_starts_at = username_length + LENGTH_FIELD_SIZE
                message_length = int(padded_plain[message_starts_at: message_starts_at + LENGTH_FIELD_SIZE])
                message = padded_plain[message_starts_at + LENGTH_FIELD_SIZE:]
                return True, command, message_type, {"username": username, "message": message}

        elif command == COMMAND_PRIVATE:
            if not encryption_enabled:
                username_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                username = _recv_fixed(sock, username_length)

                recipient_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                recipient_name = _recv_fixed(sock, recipient_length)

                message_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                message = _recv_fixed(sock, message_length)
                return True, command, message_type, {"username": username, "recipient": recipient_name, "message": message}
            else:
                payload_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
                payload = _recv_fixed(sock, payload_length)

                cipher_bytes = bytes.fromhex(payload)
                padded_plain = encryption_utils.decrypt_AES(cipher_bytes, encryption_key)

                username_length = int(padded_plain[:LENGTH_FIELD_SIZE])
                username = padded_plain[LENGTH_FIELD_SIZE:LENGTH_FIELD_SIZE + username_length]
                recipient_name_starts_at = username_length + LENGTH_FIELD_SIZE
                recipient_length = int(padded_plain[recipient_name_starts_at: recipient_name_starts_at + LENGTH_FIELD_SIZE])
                message_starts_at = recipient_name_starts_at + recipient_length + LENGTH_FIELD_SIZE
                recipient_name = padded_plain[recipient_name_starts_at + LENGTH_FIELD_SIZE:message_starts_at]
                message_length = int(padded_plain[message_starts_at: message_starts_at + LENGTH_FIELD_SIZE])
                message = padded_plain[message_starts_at + LENGTH_FIELD_SIZE:]
                return True, command, message_type, {"username": username, "recipient": recipient_name, "message": message}
        else:
            raise ValueError(f"Unknown command: {command}")

    except Exception as e:
        print(f"[Protocol ERROR] {e}. \n\t function: recv_client_msg")
        return False, None, None, None


def recv_server_msg(sock: socket.socket, encryption_enabled=False, AES_key=None):
    """
    Read a message from the server.
    :param sock: the server's socket
    :param encryption_enabled: A boolean controls whether there is encryption on the params or not.
    :param AES_key: The key to decrypt the server's message
    :return: (success: bool, code: int | None, message_type: int, message: str | None)
    """
    try:
        code = int(sock.recv(1).decode())  # read one digit - the response code
        message_type = int(sock.recv(1).decode())  # read one digit - the response code

        data_length = int(_recv_fixed(sock, LENGTH_FIELD_SIZE))
        data = _recv_fixed(sock, data_length)
        if not (encryption_enabled and AES_key):
            return True, code, message_type, data

        cipher_bytes = bytes.fromhex(data)
        padded_plain = encryption_utils.decrypt_AES(cipher_bytes, AES_key)
        length_field = padded_plain[:LENGTH_FIELD_SIZE]
        msg_len = int(length_field)
        data = padded_plain[LENGTH_FIELD_SIZE: LENGTH_FIELD_SIZE + msg_len]
        return True, code, message_type, data
    except Exception as e:
        print(f"[Protocol ERROR] {e}. \n\t function: recv_client_msg")
        return False, None, None, None