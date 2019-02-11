#!/usr/bin/python3
# -*- coding: utf-8 -*-
from platform import system
from tkinter import Frame, Scrollbar, VERTICAL, Y, RIGHT, FALSE, Canvas, LEFT, BOTH, TRUE, NW
from tkinter import ttk

# http://tkinter.unpythonic.net/wiki/VerticalScrolledFrame

class VerticalScrolledFrame(Frame):
	"""A pure Tkinter scrollable frame that actually works!
	* Use the 'interior' attribute to place widgets inside the scrollable frame
	* Construct and pack/place/grid normally
	* This frame only allows vertical scrolling

	"""
	def __init__(self, parent, background, width=None, height=None, *args, **kw):
		Frame.__init__(self, parent, background=background, *args, **kw)            

		# create a canvas object and a vertical scrollbar for scrolling it
		vscrollbar = Scrollbar(self, orient=VERTICAL)
		vscrollbar.pack(fill=Y, side=RIGHT, expand=FALSE)
		self.canvas = Canvas(self, bd=0, highlightthickness=0,
						yscrollcommand=vscrollbar.set, width=width, height=height)
		self.canvas.pack(side=LEFT, fill=BOTH, expand=TRUE)
		vscrollbar.config(command=self.canvas.yview)
		if system() == 'Windows':
			self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
		else:
			self.canvas.bind_all("<Button-4>", self._on_mousewheelb4)
			self.canvas.bind_all("<Button-5>", self._on_mousewheelb5)

		# reset the view
		self.canvas.xview_moveto(0)
		self.canvas.yview_moveto(0)

		# create a frame inside the canvas which will be scrolled with it
		self.interior = interior = Frame(self.canvas, background=background)
		interior_id = self.canvas.create_window(0, 0, window=interior,
										   anchor=NW)

		# track changes to the canvas and frame width and sync them,
		# also updating the scrollbar
		def _configure_interior(event):
			# update the scrollbars to match the size of the inner frame
			size = (interior.winfo_reqwidth(), interior.winfo_reqheight())
			self.canvas.config(scrollregion="0 0 %s %s" % size)
			if interior.winfo_reqwidth() != self.canvas.winfo_width():
				# update the canvas's width to fit the inner frame
				self.canvas.config(width=interior.winfo_reqwidth())
		interior.bind('<Configure>', _configure_interior)

		def _configure_canvas(event):
			if interior.winfo_reqwidth() != self.canvas.winfo_width():
				# update the inner frame's width to fill the canvas
				self.canvas.itemconfigure(interior_id, width=self.canvas.winfo_width())
		self.canvas.bind('<Configure>', _configure_canvas)
	def _on_mousewheel(self, event):
		self.canvas.yview_scroll(-1*(event.delta//120), "units")
	def _on_mousewheelb4(self, event):
		self.canvas.yview_scroll(-1, "units")
	def _on_mousewheelb5(self, event):
		self.canvas.yview_scroll(1, "units")
	def to_start(self):
		self.canvas.yview_moveto(0)
	def rebind(self):
		if system() == 'Windows':
			self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
		else:
			self.canvas.bind_all("<Button-4>", self._on_mousewheelb4)
			self.canvas.bind_all("<Button-5>", self._on_mousewheelb5)

	def unbind_scroll(self):
		if system() == 'Windows':
			self.canvas.unbind_all("<MouseWheel>")
		else:
			self.canvas.unbind_all("<Button-4>")
			self.canvas.unbind_all("<Button-5>")

	def resize(self, width, height):
		self.canvas['width'] = width
		self.canvas['height'] = height