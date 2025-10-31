import tkinter as tk
import gui_config


class HeaderBar:
    def __init__(self, parent: tk.Tk, username: str):
        self.frame: tk.Frame = tk.Frame(parent, bg=gui_config.HEADER_BG)

        self.chat_name_label: tk.Label = tk.Label(self.frame, text="General", bg=gui_config.HEADER_BG,
                                                  fg="white", font=gui_config.TITLE_FONT)
        self.username_label: tk.Label = tk.Label(self.frame, text=username, bg=gui_config.HEADER_BG,
                                                   fg="white", font=gui_config.TITLE_USERNAME_FONT)

        self.chat_name_label.pack(padx=30, pady=15, side=tk.LEFT)
        self.username_label.pack(padx=15, side=tk.RIGHT)

    def set_chat_name(self, chat_name: str):
        """
        Updates the chat name label according to the chat name provided.
        :param chat_name: The chosen chat.
        :return: None
        """
        self.chat_name_label.config(text=chat_name)

    def set_username(self, username: str):
        """
        Updates the username label according to the username provided.
        :param username: The chosen username.
        :return: None
        """
        self.username_label.config(text=username)