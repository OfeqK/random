import socket
from typing import Literal

import select
import database_utils
import encryption_utils
import protocol
from user import User

class ChatServer:
    def __init__(self, host = "0.0.0.0", port = protocol.PORT):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: list[User] = []

    def _accept_new_client(self):
        new_sock, new_addr = self.server_socket.accept()
        client = User(new_sock)
        self.clients.append(client)
        print(f"New client connected from {new_addr}")

        client.pending_messages.append((
            protocol.RESPONSE_HELLO,
            protocol.MESSAGE_TEXT,
            f"SERVER: Hello! Please send your RSA key."
        ))

    def _flush_pending(self, user: User):
        """
        Sends the pending messages of this user
        :param user: The user who needs to receive messages
        """
        try:
            while user.pending_messages:
                response_code, message_type, message = user.pending_messages.pop(0)

                encryption_enabled = True if (response_code != protocol.RESPONSE_HANDSHAKE and
                                              user.symmetric_AES_key) else False
                user.sock.send(protocol.create_server_msg(response_code, message_type, message,
                                                          encryption_enabled, user.symmetric_AES_key))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self._remove_user(user)

    def _remove_user(self, user: User):
        user.close()
        if user in self.clients:
            self.clients.remove(user)

        if user.username:
            self._send_broadcast_message(None, protocol.MESSAGE_TEXT,
                                         "User '{user.username}' has left the general chat!")

    def _send_broadcast_message(self, user: User | None, message_type: Literal[0,1], message: str):
        """
        Sends a broadcast message from user to everybody else (not to the user itself tho).
        :param user: The user that sends the message. If user is None then it is the server that sent that message
        :param message_type: The type of the message
        :param message: The message to be sent
        :return:
        """
        username = user.username if user else "Server"
        if message_type == protocol.MESSAGE_TEXT:
            print(f"[Broadcast] {username}: {message}")
        else:
            print(f"[Broadcast] {username}: voice or image message!")

        for other in self.clients:
            if other.username and other is not user:
                other.pending_messages.append((
                    protocol.RESPONSE_OK,
                    message_type,
                    f"{username}: {message}"
                ))

    def _handle_user_message(self, user: User):
        encryption_enabled = True if user.symmetric_AES_key else False
        success, command, message_type, params = protocol.recv_client_msg(user.sock, encryption_enabled,
                                                                      user.symmetric_AES_key)

        if not success or command is None:
            self._remove_user(user)
            return

        if command == protocol.COMMAND_HANDSHAKE:
            # store the RSA key of the client
            public_key = encryption_utils.deserialize_public_RSA_key(params["RSA_key"])
            user.public_RSA_encryption_key = public_key

            # print(f"User {user.username} has set his public key: {params['RSA_key']}")

            AES_key = encryption_utils.generate_AES_key()
            user.symmetric_AES_key = AES_key

            # encrypt AES key with client's RSA public key
            serialized_AES = encryption_utils.serialize_AES_key(AES_key)
            print(f"Created AES key for {user.sock.getpeername()}. It is: {serialized_AES}")
            encrypted_AES = encryption_utils.encrypt_RSA(serialized_AES, user.public_RSA_encryption_key)

            # send it to the client (hex encoded)
            user.pending_messages.append((
                protocol.RESPONSE_HANDSHAKE,
                message_type,
                f"SESSION_KEY:{encrypted_AES.hex()}"
            ))

            print(f"Handshake complete with {user.username}. AES session key established.")
            return

        elif user.symmetric_AES_key and command == protocol.COMMAND_SET_USERNAME:
            username = params["username"]
            user_exists = database_utils.check_if_user_exists(username)
            user.password_set = False

            if user_exists:
                user.pending_messages.append((
                    protocol.RESPONSE_USER_EXISTS,
                    message_type,
                    f"SERVER: User exists in the database. Please send password."
                ))
                return

            # user does not exist in the database
            user.pending_messages.append((
                protocol.RESPONSE_USER_DOES_NOT_EXIST,
                message_type,
                f"SERVER: User does not exist in the database.\nPlease set a new password."
            ))
            user.is_new_user = True
            return

        elif user.symmetric_AES_key and command == protocol.COMMAND_SET_PASSWORD and not user.password_set:
            # if later i decide to remove the username from here - as it is unwanted, i can remove the next line and update
            # the protocol
            username = params["username"]
            password = params["password"]
            salt, hashed_password = database_utils.hash_password(password)

            if user.is_new_user: # add this user to the database
                added_user_successfully = database_utils.add_user(username, salt, hashed_password)
                if not added_user_successfully:
                    # TODO change this to be better
                    self._remove_user(user)
                    return

                user.username = username
                print(f"Client {user.sock.getpeername()} set new username: '{username}' and password.")
                user.pending_messages.append((
                    protocol.RESPONSE_CREATED_USER,
                    message_type,
                    f"SERVER: User created successfully!"
                ))

                user.pending_messages.append((
                    protocol.RESPONSE_OK,
                    message_type,
                    f"SERVER: Clients connected to general are: {[user.username for user in self.clients if user.username] or 'None'}"
                ))
                user.password_set = True
                self._send_broadcast_message(user=None, message_type= protocol.MESSAGE_TEXT,
                                             message=f"User '{username}' has joined the general chat!")
                return

            # check if the user's credentials are matching to the ones in the database
            is_authenticated = database_utils.authenticate_user(username, password)
            if is_authenticated: # the user is validated
                user.username = username
                user.password_set = True

                print(f"Client {user.sock.getpeername()} signed in as: '{username}'.")
                user.pending_messages.append((
                    protocol.RESPONSE_CORRECT_PASSWORD,
                    message_type,
                    f"SERVER: Correct password! You may start sending messages in the global chat."
                ))

                user.pending_messages.append((
                    protocol.RESPONSE_OK,
                    message_type,
                    f"SERVER: Clients connected to general are: {[user.username for user in self.clients if user.username] or 'None'}"
                ))
                self._send_broadcast_message(user=None, message_type= protocol.MESSAGE_TEXT,
                                             message=f"User '{username}' has joined the general chat!")
                return

            # user is wrong
            user.pending_messages.append((
                protocol.RESPONSE_INCORRECT_PASSWORD,
                message_type,
                f"SERVER: Incorrect password! Please try again."
            ))
            return

        elif user.symmetric_AES_key and user.username and user.password_set and command == protocol.COMMAND_BROADCAST:
            msg = params["message"]
            self._send_broadcast_message(user, message_type, msg)
            return

        elif user.symmetric_AES_key and user.username and user.password_set and command == protocol.COMMAND_PRIVATE:
            recipient = params["recipient"]
            msg = params["message"]

            # find recipient
            target = next((c for c in self.clients if c.username == recipient), None)
            if target is None:
                user.pending_messages.append((
                    protocol.RECIPIENT_NOT_FOUND,
                    message_type,
                    f"SERVER: User '{recipient}' not found."
                ))
                return

            print(f"[Private] {user.username} → {recipient}: {msg}")
            target.pending_messages.append((
                protocol.RESPONSE_OK,
                message_type,
                f"[Private Message from {user.username}]: {msg}"
            ))
            # user.pending_messages.append((protocol.RESPONSE_OK, f"[PM to {recipient}]: {msg}"))
        else:
            print("SERVER ERROR.. Unkown command -_-")


    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Chat server listening on {self.host}:{self.port}")

        while True:
            client_sockets = [c.sock for c in self.clients]
            read_list = client_sockets + [self.server_socket]
            ready_to_read, ready_to_write, in_error = select.select(read_list, client_sockets, [])

            # accept a new connections
            if self.server_socket in ready_to_read:
                self._accept_new_client()
                ready_to_read.remove(self.server_socket)

            # handle incoming messages
            for user in [u for u in self.clients if u.sock in ready_to_read]:
                self._handle_user_message(user)

            # send pending messages
            for user in [u for u in self.clients if u.sock in ready_to_write]:
                self._flush_pending(user)


def main():
    server = ChatServer()
    server.start()


if __name__ == '__main__':
    main()