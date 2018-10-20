#!/usr/bin/python3
# -*- coding: utf-8 -*- 
import tkinter
import tkinter.ttk
import tkinter.messagebox
from . import ScrolledFrame, Images
import PIL.Image
import PIL.ImageTk
from derpibooru_dl import parser, tagResponse
from .. import net
import config
import re

unsigned_number_validate = re.compile(r"^\s*\d+\s*$")


class CustomCheckbox(tkinter.Checkbutton):
	def __init__(self, root, data, tags, **kwargs):
		self.state = tkinter.BooleanVar()
		tkinter.Checkbutton.__init__(self, root, variable=self.state, onvalue=True, offvalue=False, **kwargs)
		self.data = data
		self.tags = tags


class GUI:
	def __init__(self):
		self.root = tkinter.Tk()
		self.root.geometry("1050x550")
		config_panel = tkinter.Frame(self.root)
		self.search_field = tkinter.Entry(config_panel)
		self.search_field.pack(side="left")
		self.search_field.bind("<Return>", self.search)
		search_btn = tkinter.ttk.Button(config_panel, text="Search", command=self.search)
		search_btn.pack(side="left")
		config_panel.pack(side="top")
		self.img_gallery_wrapper = ScrolledFrame.VerticalScrolledFrame(self.root, width=1050, height=480)
		self.img_gallery_wrapper.interior['width'] = 1024
		self.img_gallery_wrapper.interior['height'] = 480
		self.img_gallery_wrapper.pack(side="top")
		nav_panel = tkinter.Frame(self.root)
		nav_panel.pack(side="top")
		tkinter.Label(nav_panel, text="Page: ").pack(side="left")
		self.page_count_field = tkinter.Entry(nav_panel, width = 5)
		self.page_count_field.pack(side="left")
		self.page_count_field.bind("<Return>", self.__goto)
		self.page_count_field.bind("<KP_Enter>", self.__goto)
		goto_btn = tkinter.ttk.Button(nav_panel, text="go to", command=self.__goto)
		goto_btn.pack(side="left")
		prev_btn = tkinter.ttk.Button(nav_panel, text="prev", command=self.prev)
		prev_btn.pack(side="left")
		next_btn = tkinter.ttk.Button(nav_panel, text="next", command=self.next)
		next_btn.pack(side='left')
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)
		self.checkbox_array = []
		self.root.mainloop()

	def __search(self):
		Images.clear_video()
		self.img_gallery_wrapper.to_start()
		for widget in self.img_gallery_wrapper.interior.winfo_children():
			widget.destroy()
		self.page_count_field.delete(0, tkinter.END)
		self.page_count_field.insert(0, str(net.page))
		q = self.search_field.get()
		if len(q):
			self.data = net.get_page(q, key=config.key)
		else:
			self.data = net.get_page(key=config.key)
		self.parsed_tags = []
		self.checkbox_array = []
		i = 0
		for elem in self.data:
			parsed_tags = tagResponse.tagIndex(elem['tags'])
			self.checkbox_array.append(CustomCheckbox(self.img_gallery_wrapper.interior, elem, parsed_tags))
			self.checkbox_array[-1].grid(row=i // 4 * 2, column=i % 4)
			imglabel = None
			if {"safe", "suggestive"} & parsed_tags["category"]:
				if elem["original_format"] in {'png', 'jpg', 'jpeg', 'gif'}:
					imglabel = Images.Image(
						self.img_gallery_wrapper.interior,
						file=elem["representations"]["thumb"],
						tags = elem['tags']
					)
				else:
					imglabel = Images.Video(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb"],
						elem['tags']
					)
			else:
				if elem["original_format"] in {'png', 'jpg', 'jpeg', 'gif'}:
					imglabel = Images.SpoilerImage(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb_tiny"],
						elem["representations"]["thumb"],
						elem['tags']
					)
				else:
					imglabel = Images.SpoilerVideo(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb"],
						elem["representations"]["thumb_tiny"],
						elem['tags']
					)
			imglabel.grid(row=i // 4 * 2+1, column=i % 4)
			imglabel.bind("<Button-3>", self.showTags)
			imglabel.update_idletasks()
			i += 1

	def search(self, event = None):
		net.page = 1
		self.__search()

	def next(self):
		self.save()
		net.page += 1
		self.__search()

	def save(self):
		if len(self.checkbox_array):
			for item in self.checkbox_array:
				if item.state.get():
					out_dir = tagResponse.find_folder(item.tags)
					parser.append2queue(outdir=out_dir, data=item.data, tags=item.tags)

	def prev(self):
		self.save()
		net.page -= 1
		self.__search()

	def on_close(self):
		if parser.downloader_thread.isAlive():
			parser.downloader_thread.join()
		self.root.destroy()
	
	def __goto(self, event = None):
		self.save()
		if unsigned_number_validate.search(self.page_count_field.get()) is not None:
			page = int(re.search(r"\d+", self.page_count_field.get()).group(0))
			if page != net.page or page==1:
				net.page = page
				self.__search()
		else:
			tkinter.messagebox.showerror('Browser', "invalid page number")

	def showTags(self, event):
		TagList(self, event.widget.tags)

class TagList:
	def __init__(self, parent, tags):
		self.parent = parent
		self._root = tkinter.Toplevel(parent.root)
		vscrollbar = tkinter.Scrollbar(self._root, orient=tkinter.VERTICAL)
		vscrollbar.pack(fill=tkinter.Y, side=tkinter.RIGHT, expand=tkinter.FALSE)
		self._taglist = tkinter.Listbox(self._root, yscrollcommand=vscrollbar.set, width = 20, height = 20)
		self._taglist.pack()
		vscrollbar.config(command=self._taglist.yview)
		for tag in tags.split(', '):
			self._taglist.insert(tkinter.END, tag)
		self._taglist.bind("<Double-Button-1>", self.search)

	def search(self, event = None):
		self.parent.search_field.delete(0, tkinter.END)
		self.parent.search_field.insert(0, 
			self._taglist.get(tkinter.ACTIVE)
		)
		self.parent.search()