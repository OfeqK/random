from typing import Literal

import protocol
from header import HeaderBar
from sidebar import Sidebar
from chat_area import ChatArea
from input_area import InputArea
import tkinter as tk
from gui_client import GuiChatClient

import gui_config

# documentation of tkinter widgets and stuff: : https://www.tcl-lang.org/man/tcl8.6/TkCmd/contents.htm
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.username = None
        self.set_password = False

        # TODO: the following lines are temporary
        # self.chats = dict() # { chat_name_1: [(user1, type=0, text), (user2, type=1, audio_stuff), ...], ...}
        self.chats = {
            "Server Messages": [("Setup", 0, "Please enter your username.")],
            # "General": [],
        }
        self.active_chat = "Server Messages"

        self.header = HeaderBar(self.root, '')
        self.sidebar = Sidebar(self.root, list(self.chats.keys()), self.switch_chat)
        self.chat_area = ChatArea(self.root)
        self.input_area = InputArea(self.root, self.send_message_to_server)

        # networking
        self.client = GuiChatClient()
        self.root.after(100, self.poll_messages)

        self._create_component_layout()
        self.switch_chat(self.active_chat)

    def _create_component_layout(self):
        self.root.title("whispr")
        self.root.geometry(f"{gui_config.SCREEN_WIDTH}x{gui_config.SCREEN_HEIGHT}")
        self.root.configure(bg=gui_config.BG_COLOR)
        self.root.resizable(False, False)

        self.root.rowconfigure(1, weight=1)  # middle row (chat area) expands
        self.root.columnconfigure(0, weight=1)  # chat area expands
        self.root.columnconfigure(1, weight=0)  # sidebar stays fixed

        self.header.frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.chat_area.frame.grid(row=1, column=0, sticky='nsew')
        self.sidebar.frame.grid(row=1, column=1, sticky="nsew")
        self.input_area.frame.grid(row=2, column=0, sticky='ew')


    def _send_first_message(self, username):
        self.username = username
        self.client.connect(username)

    def _first_connection_to_server(self):
        """
        Updates everything to match the user's correctly inputted username
        :return:
        """
        if self.username is None:
            raise Exception("[Application ERROR] Tried to call _first_connection_to_server with self.username = None.")


        self.header.set_username(self.username)
        self.add_chat("General")


    def switch_chat(self, chat_name: str):
        """
        Updates the header, sidebar and the chat area with messages from the chosen chat name.
        :param chat_name: The chosen chat to be loaded
        :return: None
        """

        # make sure chat_name is valid
        if chat_name not in self.chats:
            return

        self.active_chat = chat_name

        # update header
        self.header.set_chat_name(chat_name)

        # update sidebar
        self.sidebar.highlight_chat(chat_name)

        # update chat_area
        self.chat_area.clear()
        self.chat_area.load_messages(self.chats[chat_name])


    def new_message(self, sender: str, message_type: Literal[0, 1], text: str, chat="General"):
        """
        Adds the new message. If the correct chat is active, also displays it
        :param sender: The sender of the message.
        :param message_type: The type of the message.
        :param text: The message chat to be sent.
        :param chat: The chat where the message should be added to
        :return:
        """
        if not text.strip():
            return
        self.chats[chat].append((sender, message_type, text))
        if self.active_chat == chat:
            self.chat_area.add_message(sender, message_type, text)

    def add_chat(self, chat_name: str):
        if chat_name in self.chats:
            return

        self.chats[chat_name] = []
        self.sidebar.add_chat(chat_name)

    def poll_messages(self, keepalive=True):
        while not self.client.incoming_messages.empty(): # while !q.isEmpty()
            response_code, message_type, raw_msg  = self.client.incoming_messages.get()

            # TODO: move this somewhere else - it does not belong here!
            # if the message is private
            if raw_msg.startswith("[Private Message from "):
                # Format: [Private Message from <username>]: <msg>
                try:
                    prefix, msg_text = raw_msg.split("]:", 1)
                    sender = prefix.replace("[Private Message from ", "").strip()
                    msg_text = msg_text.strip()

                    if sender not in self.chats:
                        self.add_chat(sender)

                    self.new_message(sender, message_type, msg_text, sender)

                except ValueError:
                    # fallback: treat as general
                    self.new_message("Server", message_type, raw_msg, "Server Messages")

            # case 2: server message
            elif raw_msg.startswith("SERVER:"):

                # if not self.set_password and (
                #         response_code == protocol.RESPONSE_USER_EXISTS or
                #         response_code == protocol.RESPONSE_USER_DOES_NOT_EXIST):
                #     _, msg_text = raw_msg.split(": ", 1)
                #     self.new_message("Server", msg_text, "Server Messages")
                #     return

                if self.username and not self.set_password and response_code in [protocol.RESPONSE_CORRECT_PASSWORD,
                                                                                 protocol.RESPONSE_CREATED_USER]:
                    # the user had logged in successfully
                    self.set_password = True
                    self._first_connection_to_server()

                _, msg_text = raw_msg.split(": ", 1)
                self.new_message("Server", message_type, msg_text, "Server Messages")


            # case 3: broadcast (username: msg)
            else:
                try:
                    sender, msg_text = raw_msg.split(":", 1)
                    sender = sender.strip()
                    msg_text = msg_text.strip()

                    if "General" not in self.chats:
                        self.add_chat("General")

                    # to enable the user the option of sending this guy a private message
                    if sender.strip().lower() != "server" and sender not in self.chats:
                        self.add_chat(sender)

                    # always log broadcast in General
                    self.new_message(sender, message_type, msg_text, "General")


                except ValueError:
                    # fallback to General
                    self.new_message("ERROR", protocol.MESSAGE_TEXT, raw_msg, "General")


        # keep polling again
        if keepalive:
            self.root.after(100, self.poll_messages)

    def send_message_to_server(self, message_type: Literal[0, 1], text: str):
        """
        If the username is not set yet, then it tries to set the username.
        else:
        Sends a message to the server from this active username, also updates the chat.
        :param message_type: The type of the message.
        :param text: The message chat to be sent.
        :return:
        """
        self.input_area.clear_input()

        text = text.strip()
        if not text:
            return

        if self.username is None:
            if message_type == protocol.MESSAGE_VOICE:
                return

            # try to send this message as a username
            requested_username = text
            self._send_first_message(requested_username)
            return


        if self.active_chat == "Server Messages":
            if self.set_password or message_type == protocol.MESSAGE_VOICE:
                return

            # the user is trying to set a new password
            msg_text = f"/set_password {text}"
            success = self.client.send_message(protocol.MESSAGE_TEXT, msg_text)
            if success:
                self.new_message(self.username, protocol.MESSAGE_TEXT, text, self.active_chat)

        elif self.active_chat == "General":
            success = self.client.send_message(message_type, text)
            if success:
                self.new_message(self.username, message_type,text, "General") # updates the gui chat

        else:
            msg_text = f"/msg {self.active_chat} {text}"
            success = self.client.send_message(message_type, msg_text)
            if success:
                self.new_message(self.username, message_type, text, self.active_chat)



    def run(self):
        self.root.mainloop() # a blocking function



def main():
    # username = utils.read_string_safe("Enter your name: ")
    app = App()
    app.run()
    if app.client.sock: app.client.close()


if __name__ == '__main__':
    main()