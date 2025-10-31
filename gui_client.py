import queue
import socket
import threading
from typing import Literal

import select

import encryption_utils
import protocol

class GuiChatClient:
    def __init__(self, host=protocol.SERVER_ADDRESS, port=protocol.PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.username = None

        self.incoming_messages = queue.Queue()
        self.running = False

        # cryptography related variables
        self.private_key = None
        self.public_key = None
        self.AES_key = None
        self.encryption_ready = False

    def connect(self, username):
        """
        Connects to the server,
        :param username: The username to connect as
        :return:
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.username = username

        # get first hello message from the server
        success, code, msg_type, data = protocol.recv_server_msg(self.sock)
        if not success or code != protocol.RESPONSE_HELLO or msg_type != protocol.MESSAGE_TEXT:
            print("[ ERROR ] Something went wrong connecting to the server.")
            exit()

        # generate RSA keypair and send public key to server
        self.private_key, self.public_key = encryption_utils.generate_RSA_keys()
        public_pem = encryption_utils.serialize_public_RSA_key(self.public_key)
        self.sock.send(protocol.create_user_msg_handshake(public_pem))

        # get the AES key
        success, code, msg_type, encrypted_data = protocol.recv_server_msg(self.sock)
        encrypted_hex = encrypted_data.split("SESSION_KEY:", 1)[1]
        encrypted_AES = bytes.fromhex(encrypted_hex)
        # decrypt with RSA private key
        decrypted_AES_hex = encryption_utils.decrypt_RSA(encrypted_AES, self.private_key)
        self.AES_key = encryption_utils.deserialize_AES_key(decrypted_AES_hex)
        self.encryption_ready = True
        print("[Client] Handshake complete. AES session key established.")

        # send over username
        self.sock.send(protocol.create_user_msg_set_username(self.username, True, self.AES_key))

        # get response from server and show it to the client
        success, code, msg_type, data = protocol.recv_server_msg(self.sock, self.encryption_ready, self.AES_key)
        self.incoming_messages.put((code, msg_type, data))

        self.running = True
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        """
        background thread: receive messages and push to queue
        """
        while self.running:
            ready_to_read, _, _ = select.select([self.sock], [], [], protocol.SELECT_TIMEOUT)

            # if a message was received
            if self.sock in ready_to_read:
                success, code, msg_type, data = protocol.recv_server_msg(self.sock)
                if not success:
                    continue

                # decrypt message because AES is enabled
                try:
                    cipher_bytes = bytes.fromhex(data)
                    padded_plain = encryption_utils.decrypt_AES(cipher_bytes, self.AES_key)
                    length_field = padded_plain[:protocol.LENGTH_FIELD_SIZE]
                    msg_len = int(length_field)
                    data = padded_plain[protocol.LENGTH_FIELD_SIZE: protocol.LENGTH_FIELD_SIZE + msg_len]
                except Exception as e:
                    print(f"[Client ERROR] AES decryption failed: {e}")
                    exit()

                self.incoming_messages.put((code, msg_type, data))

    def send_message(self, msg_type: Literal[0, 1], message):
        """
        Sends broadcast or a private message to the server
        :param msg_type: The message type (0 for "text", 1 for "voice")
        :param message: The message to be sent to the serer.
        :return: bool - True if message was sent successfully, False otherwise
        """
        message = message.strip()
        if not message:
            return False

        if msg_type == protocol.MESSAGE_TEXT and message.strip().lower().startswith("/set_password"):
            # format: /set_password <password>
            try:
                _, password = message.split(" ")
                raw = protocol.create_user_msg_set_password(self.username, password, self.encryption_ready, self.AES_key)
            except ValueError:
                print("Invalid setting password message format. Please use: \"/set_password <password>\"")
                return False

        elif message.strip().lower().startswith("/msg"):
            # format: /msg <recipient> <message>
            try:
                _, recipient, *msg_parts = message.split(" ")
                msg_text = " ".join(msg_parts)
                raw = protocol.create_user_msg_private(self.username,recipient, msg_type, msg_text,
                                                       self.encryption_ready, self.AES_key)
            except ValueError:
                print("Invalid private message format. Please use: \"/msg <recipient> <message>\"")
                return False
        else:
            # default: broadcast
            raw = protocol.create_user_msg_broadcast(self.username, msg_type, message, self.encryption_ready, self.AES_key)

        self.sock.send(raw)
        return True

    def close(self):
        self.running = False
        self.sock.close()
