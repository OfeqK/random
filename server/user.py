import socket
from typing import Literal

from cryptography.hazmat.primitives.asymmetric import rsa

class User:
    """
    Represents a connected client with username, socket, and pending messages.
    """

    def __init__(self, sock: socket.socket, username: str = None):
        self.sock = sock
        self.username = username
        self.is_new_user: bool = False
        self.password_set: bool = False

        self.pending_messages: list[tuple[int, Literal[0, 1], str]]  = []
        # pending is a list of messages in the structure of: (response_code, message_type, message)

        self.public_RSA_encryption_key: rsa.RSAPublicKey | None = None
        self.symmetric_AES_key: bytes | None = None

    def close(self):
        print(f"Closing connection for '{self.username or self.sock.getpeername()}'")
        self.sock.close()