#!/usr/bin/python3
# -*- coding: utf-8 -*- 
import tkinter
import tkinter.ttk
import tkinter.messagebox
from . import ScrolledFrame, Images
import PIL.Image
import PIL.ImageTk
from derpibooru_dl import parser, tagResponse
from .. import net, context
import config
import re

STATIC_IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
unsigned_number_validate = re.compile(r"^\s*\d+\s*$")
BACKGROUND_COLOR = '#ececec'

class CustomCheckbox(tkinter.Checkbutton):
	def __init__(self, root, data, tags, **kwargs):
		self.state = tkinter.BooleanVar()
		tkinter.Checkbutton.__init__(self,
			root,
			variable=self.state,
			onvalue=True,
			offvalue=False,
			background=BACKGROUND_COLOR,
			borderwidth=0,
			**kwargs
		)
		self.data = data
		self.tags = tags


class GUI:
	def __init__(self, root=None, query=None):
		if root is not None:
			self.root = tkinter.Toplevel(root)
			self._main = False
		else:
			self.root = tkinter.Tk()
			self._main = True
		self.root['bg']=BACKGROUND_COLOR
		self.root.title("Derpibooru-browser")
		self.root.geometry("1050x550")
		config_panel = tkinter.Frame(self.root, background=BACKGROUND_COLOR)
		self.search_field = tkinter.Entry(config_panel)
		self.hide_search_query()
		self.search_field.pack(side="left")
		self.search_field.bind("<Return>", self.search)
		self.search_field.bind("<FocusIn>", self.show_search_query)
		self.search_field.bind("<FocusOut>", self.hide_search_query)
		self.search_btn = tkinter.ttk.Button(
			config_panel,
			text="Search",
			command=self.search
		)
		self.search_btn.pack(side="left")
		if root is None:
			tkinter.ttk.Button(
				config_panel,
				text="New Window",
				command=self.__create_window).pack(side="left")
		config_panel.pack(side="top")
		self.img_gallery_wrapper = ScrolledFrame.VerticalScrolledFrame(
			self.root,
			width=1050,
			height=480,
			background=BACKGROUND_COLOR
		)
		#self.img_gallery_wrapper.interior['width'] = 1025
		#self.img_gallery_wrapper.interior['height'] = 480
		self.img_gallery_wrapper.pack(side="top")
		nav_panel = tkinter.Frame(self.root, bg=BACKGROUND_COLOR)
		nav_panel.pack(side="top")
		tkinter.Label(nav_panel, text="Page: ", bg=BACKGROUND_COLOR).pack(side="left")
		self.page_count_field = tkinter.Entry(nav_panel, width = 5)
		self.page_count_field.pack(side="left")
		self.page_count_field.bind("<Return>", self.__goto)
		self.page_count_field.bind("<KP_Enter>", self.__goto)
		self._of_text_label = tkinter.Label(nav_panel, bg=BACKGROUND_COLOR)
		self._of_text_label.pack(side="left")
		self._page_count_label = tkinter.Label(nav_panel, bg=BACKGROUND_COLOR)
		self._page_count_label.pack(side="left")
		self.goto_btn = tkinter.ttk.Button(nav_panel, text="go to", command=self.__goto)
		self.goto_btn.pack(side="left")
		self.prev_btn = tkinter.ttk.Button(nav_panel, text="prev", command=self.prev)
		self.prev_btn.pack(side="left")
		self.next_btn = tkinter.ttk.Button(nav_panel, text="next", command=self.next)
		self.next_btn.pack(side='left')
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)
		self.checkbox_array = []
		self.context = None
		self.width = 1050
		self.height = 550
		if type(query) is str:
			if len(query):
				self.context = context.Search(query)
				self.search_field.delete(0, tkinter.END)
				self.search_field.insert(0, query)
				self.__page_rendering()
			else:
				self.context = context.Images()
		self.root.bind("<FocusIn>", self.__focus)
		self.root.bind("<FocusOut>", self.__unfocus)
		self.root.bind("<Configure>", self.on_resize)
		if root is None:
			self.root.mainloop()

	def show_search_query(self, event = None):
		self.search_field['show'] = ''

	def hide_search_query(self, event = None):
		self.search_field['show'] = '�'
	
	def on_resize(self, event):
		if event.widget == self.root and (self.width != event.width or self.height != event.height):
			self.width  = event.width
			self.height = event.height
			self.img_gallery_wrapper['width'] = self.width
			self.img_gallery_wrapper['height'] = self.height - 70
			self.img_gallery_wrapper.resize(self.width, self.height - 70)
			self.img_gallery_wrapper.interior['width'] = self.width - 25
			self.img_gallery_wrapper.interior['height'] = self.height - 70
			self.__page_rendering(reflesh=False)

	def __page_rendering(self, reflesh=True):
		if context is None:
			return None
		Images.clear_video()
		self.img_gallery_wrapper.to_start()
		for widget in self.img_gallery_wrapper.interior.winfo_children():
			widget.destroy()
		self.page_count_field.delete(0, tkinter.END)
		try:
			self.page_count_field.insert(0, str(self.context.getPageNumber()))
		except AttributeError as e:
			if reflesh:
				raise e
			else:
				return
		if reflesh:
			try:
				if (config.key):
					self.data = self.context.makeRequest(key=config.key)
				else:
					self.data = self.context.makeRequest()
			except EOFError:
				tkinter.messagebox.showerror('EOFError', "end of images")
				return None
			except Exception as e:
				tkinter.messagebox.showerror('Exception', str(e))
				return None
		self.parsed_tags = []
		self.checkbox_array = []
		i = 0
		elemWidth = (self.width - 25)//250
		for elem in self.data:
			parsed_tags = tagResponse.tagIndex(elem['tags'])
			self.checkbox_array.append(
				CustomCheckbox(
					self.img_gallery_wrapper.interior,
					elem,
					parsed_tags,
				)
			)
			self.checkbox_array[-1].grid(row=i // elemWidth * 2, column=i % elemWidth)
			imglabel = None
			if {"safe", "suggestive"} & parsed_tags["category"]:
				if elem["original_format"] in STATIC_IMAGE_FORMATS:
					imglabel = Images.Image(
						self.img_gallery_wrapper.interior,
						file=elem["representations"]["thumb"],
						meta = {"tags": elem['tags'], "id": elem["id"]}
					)
				else:
					imglabel = Images.Video(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb"],
						{"tags": elem['tags'], "id": elem["id"]}
					)
			else:
				if elem["original_format"] in STATIC_IMAGE_FORMATS:
					imglabel = Images.SpoilerImage(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb_tiny"],
						elem["representations"]["thumb"],
						{"tags": elem['tags'], "id": elem["id"]}
					)
				else:
					imglabel = Images.SpoilerVideo(
						self.img_gallery_wrapper.interior,
						elem["representations"]["thumb"],
						elem["representations"]["thumb_tiny"],
						{"tags": elem['tags'], "id": elem["id"]}
					)
			imglabel['background']=BACKGROUND_COLOR
			imglabel.grid(row=i // elemWidth * 2+1, column=i % elemWidth)
			imglabel.bind("<Button-3>", self.showMeta)
			imglabel.update_idletasks()
			i += 1
		total_pages = self.context.getTotalPages()
		if total_pages is None:
			self._of_text_label['text'] = ''
			self._page_count_label['text'] = ''
		else:
			self._of_text_label['text'] = ' of'
			self._page_count_label['text'] = str(total_pages)

	def search(self, event = None):
		q = self.search_field.get()
		if len(q):
			self.context = context.Search(q)
		else:
			self.context = context.Images()
		self.__page_rendering()

	def next(self):
		if isinstance(self.context, context.Context):
			self.save()
			self.context.next_page()
			self.__page_rendering()

	def save(self):
		if len(self.checkbox_array):
			for item in self.checkbox_array:
				if item.state.get():
					out_dir = tagResponse.find_folder(item.tags)
					parser.append2queue(output_directory=out_dir, data=item.data, tags=item.tags)

	def prev(self):
		if isinstance(self.context, context.Context):
			self.save()
			self.context.prev_page()
			self.__page_rendering()

	def on_close(self):
		Images.clear_video()
		self.save()
		if self._main:
			net.clearCache()
			if parser.downloader_thread.isAlive():
				parser.downloader_thread.join()
		self.root.destroy()
	
	def __goto(self, event = None):
		self.save()
		if unsigned_number_validate.search(self.page_count_field.get()) is not None:
			page = int(re.search(r"\d+", self.page_count_field.get()).group(0))
			if self.context is None or page != self.context.getPageNumber():
				if not isinstance(self.context, context.Context):
					self.context = context.Images()
				self.context.go_to(page)
				self.__page_rendering()
		else:
			tkinter.messagebox.showerror('Browser', "invalid page number")

	def showMeta(self, event):
		TagList(self, event.widget.getMeta())

	def __focus(self, event):
		self.img_gallery_wrapper.rebind()
		self.search_field.bind("<Return>", self.search)
		self.search_btn['command'] = self.search
		self.page_count_field.bind("<Return>", self.__goto)
		self.page_count_field.bind("<KP_Enter>", self.__goto)
		self.goto_btn['command'] = self.__goto
		self.prev_btn['command'] = self.prev
		self.next_btn['command'] = self.next
		for widget in self.img_gallery_wrapper.interior.winfo_children():
			if isinstance(widget, (Images.BaseImage, Images.BaseVideo)):
				widget.rebind()
	
	def __unfocus(self, event):
		self.img_gallery_wrapper.unbind_scroll()
	
	def __create_window(self):
		GUI(self.root)

class TagList:
	def __init__(self, parent, meta):
		self.parent = parent
		self._root = tkinter.Toplevel(parent.root)
		self._root.title("List of tags")
		id_wrapper = tkinter.Frame(self._root)
		tkinter.Label(id_wrapper, text="Image ID: ").pack(side="left")
		id_btn = tkinter.ttk.Button(id_wrapper, text=meta['id'])
		id_btn.pack(side="left")
		id_btn.bind('<Button-1>', self.__copy_to_clipboard)
		id_wrapper.pack(side="top")
		list_wrapper = tkinter.Frame(self._root)
		self.vscrollbar = tkinter.Scrollbar(list_wrapper, orient=tkinter.VERTICAL)
		self.vscrollbar.pack(fill=tkinter.Y, side=tkinter.RIGHT, expand=tkinter.FALSE)
		self._taglist = tkinter.Listbox(
			list_wrapper,
			yscrollcommand=self.vscrollbar.set,
			width = 20,
			height = 20
		)
		self._taglist.pack()
		list_wrapper.pack(side="top")
		self.vscrollbar.config(command=self._taglist.yview)
		for tag in meta['tags'].split(', '):
			self._taglist.insert(tkinter.END, tag)
		self._taglist.bind("<Double-Button-1>", self.search)
		self._root.bind("<FocusIn>", self.__focus)

	def search(self, event = None):
		#self.parent.search_field.delete(0, tkinter.END)
		#self.parent.search_field.insert(0, 
		#	self._taglist.get(tkinter.ACTIVE)
		#)
		#self.parent.search()
		GUI(self.parent.root, self._taglist.get(tkinter.ACTIVE))

	def __copy_to_clipboard(self, event):
		self._root.clipboard_clear()
		self._root.clipboard_append(event.widget['text'])
		self._root.update()
		tkinter.messagebox.showinfo("Derpiboru-browser", "Image ID now in clipboard")
	
	def __focus(self, event):
		self.vscrollbar.config(command=self._taglist.yview)