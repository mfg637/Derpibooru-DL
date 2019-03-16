#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import os, threading, multiprocessing
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from . import parser, tagResponse, imgOptimizer

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

		self._data=[]
		self.dl_process = None

		self._root.mainloop()
	def add(self):
		self._list.insert(END, parser.get_ID_by_URL(self._root.clipboard_get()))
		if (self.dl_process is None) or (not self.dl_process.is_alive()):
			self.start_downloader()
	def start_downloader(self):
		self.dl_process=threading.Thread(target=self.download)
		self.dl_process.start()
	def download(self):
		self._dl_btn['state']=DISABLED
		pipe = multiprocessing.Pipe()
		while self._list.size()>0:
			id = self._list.get(0)
			self._list.delete(0)
			data=parser.parseJSON(id)
			parsed_tags=tagResponse.tagIndex(data['tags'])
			outdir=tagResponse.find_folder(parsed_tags)
			if not os.path.isdir(outdir):
				os.makedirs(outdir)
			process = multiprocessing.Process(target=parser.download, args=((outdir, data, parsed_tags, pipe[1])))
			process.start()
			imgOptimizer.sumos, imgOptimizer.sumsize, imgOptimizer.avq, imgOptimizer.items = pipe[0].recv()
			process.join()
		self._dl_btn['state']=NORMAL
