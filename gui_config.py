"""
Here we save constants such as colors, widget width, widget height, etc.
"""

# Util functions
def _from_rgb(rgb: tuple[int, int, int]):
    """
    Translates an rgb tuple of int to a tkinter friendly color code
    """
    if not rgb or len(rgb) != 3:
        raise ValueError(f"[Error] Provided rgb: {rgb} is not valid!\n\t function: _from_rgb in gui_config.py")
    r, g, b = rgb
    return f'#{r:02x}{g:02x}{b:02x}'

# --- Constants ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# --- Colors ---
# white mode:
BG_COLOR = _from_rgb((236, 234, 217))
# HEADER_BG = _from_rgb((248, 247, 250))
HEADER_BG = _from_rgb((53, 77, 89))
HIGHLIGHTED_CHAT_BLUE_COLOR = _from_rgb((61, 131, 210))
TEXT_COLOR = _from_rgb((0, 0, 0))
BUTTON_HOVER = _from_rgb((232, 241, 255))
PLACEHOLDER_COLOR = _from_rgb((156, 163, 175))

MESSAGE_GRAY = _from_rgb((0, 0, 0))
MESSAGE_LIGHTBLUE = _from_rgb((0, 0, 0))

# dark mode:


# --- Fonts ---
TITLE_FONT = ("Segoe UI", 25, "bold")
TITLE_USERNAME_FONT = ("Segoe UI", 20)
SIDEBAR_FONT = ("Segoe UI", 20)
SIDEBAR_HIGHLIGHTED_FONT = ("Segoe UI", 20, "bold")
MSG_SENDER_FONT = ("Segoe UI", 14, "bold")
MSG_FONT = ("Segoe UI", 16)
ENTRY_FONT = ("Segoe UI", 16)

#TODO: in the future, change all widgets from tk.widget to ttk.widget (themed tk)