import tkinter as tk
from typing import Callable
import gui_config
import protocol
from GUI.audio_manager import AudioManager


class InputArea:
    def __init__(self, parent: tk.Tk, callback: Callable):
        self.frame: tk.Frame = tk.Frame(parent, bg=gui_config.BG_COLOR)
        self.callback = callback # App.send_message_from_current_username(text)
        self.placeholder = "Enter your message"
        self.placeholder_active = True

        self.entry: tk.Entry = tk.Entry(self.frame, font=gui_config.ENTRY_FONT, bd=1,
                                        relief="groove", fg=gui_config.PLACEHOLDER_COLOR)
        self.entry.pack(padx=(12, 8), pady=12, side=tk.LEFT, expand=True, fill=tk.X)
        self.entry.insert(0, self.placeholder)
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._add_placeholder)

        self.send_button: tk.Button = tk.Button(
            self.frame,
            text="➤",
            font=gui_config.MSG_SENDER_FONT,
            bg=gui_config.BG_COLOR,
            fg=gui_config.TEXT_COLOR,
            activebackground=gui_config.BG_COLOR,
            activeforeground=gui_config.TEXT_COLOR,
            bd=0,
            padx=14,
            pady=8,
            command=self.on_send_click
        )
        self.send_button.pack(padx=0, pady=12, side=tk.RIGHT)

        # bind 'Enter' key to sending
        self.entry.bind("<Return>", lambda ev: self.on_send_click())

        # buttons related to sending voice messages
        self.recording = False
        self.audio_placeholder = "Recording audio..."
        self.start_stop_recording_button: tk.Button = tk.Button(
            self.frame,
            text="🎤",
            font=gui_config.MSG_SENDER_FONT,
            bg=gui_config.BG_COLOR,
            fg=gui_config.TEXT_COLOR,
            activebackground=gui_config.BG_COLOR,
            activeforeground=gui_config.TEXT_COLOR,
            bd=0,
            padx=14,
            pady=8,
            command=self.on_recorder_click
        )
        self.start_stop_recording_button.pack(padx=0, pady=12, side=tk.RIGHT)
        self.audio_manager = AudioManager()

    def _clear_placeholder(self, event):
        if self.entry.get() == self.placeholder or self.entry.get() == self.audio_placeholder:
            self.placeholder_active = False
            self.entry.delete(0, "end")
            self.entry.config(fg=gui_config.TEXT_COLOR)

    def _add_placeholder(self, event):
        if not self.entry.get() or self.entry.get() == '':
            self.placeholder_active = True
            self.entry.insert(0, self.placeholder)
            self.entry.config(fg=gui_config.PLACEHOLDER_COLOR)

    def get_text(self) -> str:
        """
        Gets the contents of the user entry
        :return: The text in the entry that the user has entered
        """
        return self.entry.get()

    def clear_input(self):
        """
        Clears the entry after sending a message
        :return:
        """
        self.entry.delete(0, tk.END)

    def on_send_click(self):
        """
        Notifies the app that a message has been sent.
        :return:
        """
        if self.recording:
            return
        if self.placeholder_active:
            self._clear_placeholder(None)
        text = self.get_text()
        if not text.strip():
            return

        self.callback(protocol.MESSAGE_TEXT, self.get_text())

    def on_recorder_click(self):
        """
        Changes mode to recording
        :return:
        """
        self.recording = not self.recording
        if self.recording: # voice mode
            self.start_stop_recording_button.configure(text="➤")

            self.audio_manager.start_recording()
            self._clear_placeholder(None)
            self.entry.insert(0, self.audio_placeholder)
            self.entry.config(state="disabled")
            self.send_button.config(state="disabled")

        else: # stopped recording
            self.start_stop_recording_button.configure(text="🎤")
            raw_bytes = self.audio_manager.stop_recording()
            self.entry.config(state="normal")
            self.entry.configure(fg=gui_config.TEXT_COLOR)
            self._clear_placeholder(None)
            self._add_placeholder(None)
            self.send_button.config(state="normal")

            if len(raw_bytes) > (10 ** protocol.LENGTH_FIELD_SIZE - 1):
                print("file is way to large!")
            elif raw_bytes:
                self.callback(protocol.MESSAGE_VOICE, raw_bytes.hex())
