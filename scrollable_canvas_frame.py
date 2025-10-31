import tkinter as tk
import gui_config

class ScrollableCanvasWithFrame:
	def __init__(self, parent):
		self.canvas = tk.Canvas(parent, bg=gui_config.BG_COLOR)
		self.canvas.pack(side="left", fill=tk.BOTH, expand=True)

		scrollbar = tk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
		self.canvas.configure(yscrollcommand=scrollbar.set)
		scrollbar.pack(side="right", fill="y")

		self.scroll_frame = tk.Frame(self.canvas, bg=gui_config.BG_COLOR)
		# place the frame on the canvas - the top left of the frame is 0,0
		self.canvas.create_window(0, 0, window=self.scroll_frame, anchor="nw")

		# allow mouse-wheel scrolling
		self.canvas.bind(
			"<MouseWheel>",
			lambda event: self.canvas.yview_scroll(-int(event.delta / 60), "units")
		)

		# auto-updating the scroll region when fram size changes
		self.scroll_frame.bind(
			"<Configure>",
			# changes the scroll region of the canvas to be everything that is inside of it..
			lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
		)

	def scroll_canvas_to_bottom(self):
		"""
		Scrolls to the bottom of the canvas.
		:return:
		"""
		self.canvas.update_idletasks()  # Ensure all items are rendered to get correct bbox
		self.canvas.config(scrollregion=self.canvas.bbox("all"))
		self.canvas.yview_moveto(1.0)
		# self.canvas.yview_scroll(-20, "units")
