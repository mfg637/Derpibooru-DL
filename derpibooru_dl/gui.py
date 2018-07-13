#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import os, threading
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from . import parser, tagResponse

class GUI:
	def __init__(self):
		self._root=Tk()

		self._listbox = Frame(self._root)
		self._listbox_scroll = ttk.Scrollbar(self._listbox)
		self._listbox_scroll.pack(side=RIGHT, fill=Y)
		self._list=Listbox(self._listbox)
		self._list.pack(side="left")
		self._list.config(yscrollcommand=self._listbox_scroll.set)
		self._listbox_scroll.config(command=self._list.yview)
		self._listbox.pack(side="top")

		self._add_btn = Button(self._root, text="add", command=self.add)
		self._add_btn.pack(side="top")
		self._dl_btn = Button(self._root, text="download", command=self.start_downloader)
		self._dl_btn.pack(side="top")
		self._progressbar = ttk.Progressbar(self._root, orient="horizontal", length=175)
		self._progressbar.pack()

		self._data=[]
		self._root.after(60000, self.au_dl)

		self._root.mainloop()
	def add(self):
		self._list.insert(0, parser.get_ID_by_URL(self._root.clipboard_get()))
	def start_downloader(self):
		self.dl_process=threading.Thread(target=self.download)
		self.dl_process.start()
	def download(self):
		self._add_btn['state']=DISABLED
		self._dl_btn['state']=DISABLED
		id_list=self._list.get(0, END)
		self._list.delete(0, END)
		self._add_btn['state']=NORMAL
		self._progressbar['maximum']=len(id_list)
		self._progressbar['value']=0
		for id in id_list:
			print('open connection')
			data=parser.parseJSON(id)
			parsed_tags=tagResponse.tagIndex(data['tags'])
			print(parsed_tags)
			outdir=tagResponse.find_folder(parsed_tags)
			print(outdir)
			if not os.path.isdir(outdir):
				os.makedirs(outdir)
			parser.download(outdir, data)
			self._progressbar.step()
		self._dl_btn['state']=NORMAL
	def au_dl(self):
		if self._list.size():
			self.dl_process=threading.Thread(target=self.download)
			self.dl_process.start()
		self._root.after(60000, self.au_dl)