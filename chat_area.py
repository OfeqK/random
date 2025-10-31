import tkinter as tk
from typing import Literal, Callable
import gui_config
import protocol
from scrollable_canvas_frame import ScrollableCanvasWithFrame
from audio_manager import play_audio, get_audio_duration_str

class ChatArea:
    def __init__(self, parent: tk.Tk):
        self.frame: tk.Frame = tk.Frame(parent, bg=gui_config.BG_COLOR)
        self.scrollable_frame = ScrollableCanvasWithFrame(self.frame)


    def clear(self):
        """
        Clears the entire chat area from all widgets - that is, removes them from the frame...
        :return:
        """
        for widget in self.scrollable_frame.scroll_frame.winfo_children():
            widget.destroy()

    def load_messages(self, messages: list[(str, str)]):
        """
        Loads all the messages to the chat area.
        :param messages: The messages to be loaded
        :return:
        """
        for sender, text, message_type in messages:
            self.add_message(sender, text, message_type)

    def add_message(self, sender: str, message_type: Literal[0, 1], content: str):
        """
        Adds the specific message to the chat area
        :param sender: The sender of the message
        :param message_type: The type of the message. i.e: voice message, or text message.
        :param content: The content of the message
        :return:
        """
        if message_type == protocol.MESSAGE_TEXT:
            widget = self.create_text_message(sender, content)
        elif message_type == protocol.MESSAGE_VOICE:
            widget = self.create_voice_message(sender, content)
        else:
            raise ValueError(f"message_type must be of type string, and one of two values: 0 or 1.\n\t"
                             f"Provided: {message_type}")
        widget.pack(anchor="w", fill=tk.X, padx=5, pady=5)
        self.scrollable_frame.scroll_canvas_to_bottom()


    def create_text_message(self, sender: str, text: str) -> tk.Widget:
        """
        Creates a text widget that looks like this: sender (in bold): text
        :param sender: The sender of the message
        :param text: The message itself
        :return: The text widget representing that message to be displayed on the canvas
        """
        text_widget: tk.Text = tk.Text(
            self.scrollable_frame.scroll_frame,
            wrap="word",
            font=gui_config.MSG_FONT,
            bg=gui_config.BG_COLOR,
            bd=0,
            relief="flat",
            height=10,
        )

        text_widget.tag_configure("sender", font=gui_config.MSG_SENDER_FONT, foreground=gui_config.TEXT_COLOR)
        text_widget.tag_configure("message", font=gui_config.MSG_FONT, foreground=gui_config.TEXT_COLOR)

        # "sender (bold): then message"
        text_widget.insert("end", f"{sender}\n", "sender")
        text_widget.insert("end", f"{text}", "message")
        text_widget.config(state="disabled")

        # according to ChatGPT:
        text_widget.update_idletasks()
        num_lines = int(text_widget.index('end-1c').split('.')[0])
        text_widget.config(height=num_lines)
        return text_widget

    def create_voice_message(self, sender, audio_data: str) -> tk.Widget:
        """
        Creates a widget that represents the voice message.
        :param sender: The sender of the message
        :param audio_data: The hex representation of the audio
        :return:
        """
        frame = tk.Frame(self.scrollable_frame.scroll_frame, bg="red")
        sender_label = tk.Label(frame, text=sender, font=gui_config.MSG_SENDER_FONT, bg="green")
        container = tk.Frame(frame, bg="blue", relief="ridge", bd=1)

        mp3_bytes = bytes.fromhex(audio_data)
        play_button = tk.Button(
            container,
            text="➤",
            bg=gui_config.BG_COLOR,
            fg=gui_config.TEXT_COLOR,
            activebackground=gui_config.BG_COLOR,
            activeforeground=gui_config.TEXT_COLOR,
            bd=0,
            command=lambda: play_audio(mp3_bytes),
            width=2
        )
        duration_str  = get_audio_duration_str(mp3_bytes=mp3_bytes)
        duration_label = tk.Label(container, text=duration_str, bg="orange", font=gui_config.MSG_FONT)

        sender_label.pack(anchor="w")
        play_button.pack(side="left", padx=4, pady=2)
        duration_label.pack(side="right", padx=4)
        container.pack(anchor="w", pady=2)

        return frame
