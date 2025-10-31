import tkinter as tk
from typing import Callable
import gui_config
from scrollable_canvas_frame import ScrollableCanvasWithFrame


class Sidebar:
    def __init__(self, parent: tk.Tk, chats: list[str], callback: Callable):
        # self.frame: tk.Frame = tk.Frame(parent, bg='lightgreen')
        self.frame: tk.Frame = tk.Frame(parent, bg=gui_config.BG_COLOR, bd=0)
        self.chat_buttons: dict[str, tk.Button] = dict() # { chat_name: str -> button: Button }
        self.callback = callback # App.switch_chat()

        self.scrollable_frame = ScrollableCanvasWithFrame(self.frame)

        # create the chats buttons:
        for chat_name in chats:
            self.add_chat(chat_name)

    def add_chat(self, chat_name: str):
        """
        Adds the chat to the list of chats available in the sidebar
        :param chat_name: The name of the chat to be added
        :return: None
        """
        # if the chat is already added
        if chat_name in self.chat_buttons:
            return

        chat_button = tk.Button(
            self.scrollable_frame.scroll_frame,
            text=chat_name,
            command=lambda: self.on_chat_click(chat_name),
            anchor="w",
            relief="flat",
            bd=0,
            highlightthickness=0,
            bg=gui_config.BG_COLOR,
            fg=gui_config.TEXT_COLOR,
            font=gui_config.SIDEBAR_FONT,
            padx=15,
            pady=10,
        )
        chat_button.pack(pady=5, fill=tk.X)
        self.chat_buttons[chat_name] = chat_button


    def highlight_chat(self, chat_name: str):
        """
        Highlights only the specified chat name, de-highlighting everything else.
        :param chat_name: The chosen chat to be highlighted
        :return:
        """

        if chat_name not in self.chat_buttons:
            return

        for name, chat_button in self.chat_buttons.items():
            text_color = gui_config.TEXT_COLOR if name != chat_name else gui_config.HIGHLIGHTED_CHAT_BLUE_COLOR
            font = gui_config.SIDEBAR_FONT if name != chat_name else gui_config.SIDEBAR_HIGHLIGHTED_FONT
            chat_button.config(fg=text_color, font=font)

    def on_chat_click(self, chat_name: str):
        self.callback(chat_name)
