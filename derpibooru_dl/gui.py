#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import os, threading, multiprocessing
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from . import tagResponse
import parser
import config


class GUI:
    def __init__(self, id_list):
        self._root=Tk()

        self._listbox = Frame(self._root)
        self._listbox_scroll = ttk.Scrollbar(self._listbox)
        self._listbox_scroll.pack(side=RIGHT, fill=Y)
        self._list = Listbox(self._listbox)
        for list_item in id_list:
            self._list.insert(END, list_item)
        self._list.pack(side="left")
        self._list.config(yscrollcommand=self._listbox_scroll.set)
        self._listbox_scroll.config(command=self._list.yview)
        self._listbox.pack(side="top")

        self._add_btn = Button(self._root, text="add", command=self.add)
        self._add_btn.pack(side="top")
        self._dl_btn = Button(self._root, text="download", command=self.start_downloader)
        self._dl_btn.pack(side="top")
        self._save_list_btn = Button(self._root, text="save list", command=self.save_list)
        self._save_list_btn.pack(side="top")

        self._data=[]
        self._current_item = None
        self.dl_process = None

        self._root.mainloop()

    def add(self):
        self._list.insert(END, self._root.clipboard_get())
        if (self.dl_process is None) or (not self.dl_process.is_alive()):
            self.start_downloader()

    def start_downloader(self):
        self.dl_process = threading.Thread(target=self.download)
        self.dl_process.start()

    def download(self):
        self._dl_btn['state']=DISABLED
        pipe = multiprocessing.Pipe()
        try:
            while self._list.size()>0:
                self._current_item = self._list.get(0)
                self._list.delete(0)
                _parser = parser.get_parser(self._current_item)
                data = _parser.parseJSON()
                parsed_tags = _parser.tagIndex()
                outdir = tagResponse.find_folder(parsed_tags)
                if not os.path.isdir(outdir):
                    os.makedirs(outdir)
                if config.enable_multiprocessing:
                    process = multiprocessing.Process(target=_parser.save_image, args=(
                        outdir, data, parsed_tags, pipe[1]
                    ))
                    process.start()
                    if config.enable_images_optimisations:
                        import pyimglib.transcoding.statistics as stats
                        stats.sumos, stats.sumsize, stats.avq, stats.items = pipe[0].recv()
                    process.join()
                else:
                    _parser.save_image(outdir, data, parsed_tags, None)
        except Exception as e:
            self._add_btn['state'] = DISABLED
            messagebox.showerror(e.__class__.__name__, str(e))
            raise e
        self._current_item = None
        self._dl_btn['state'] = NORMAL

    def save_list(self):
        list_copy = []
        if self._current_item is not None:
            list_copy.append(self._current_item)
        list_copy += self._list.get(0, END)
        file = filedialog.asksaveasfile(defaultextension=".txt")
        for list_item in list_copy:
            file.write(list_item+'\n')
        file.close()
