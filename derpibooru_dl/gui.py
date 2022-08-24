#!/usr/bin/python3
# -*- coding: utf-8 -*- 

import os
import random
import threading
import multiprocessing
import logging

import download_manager
import exceptions

import tkinter
from tkinter import *
from tkinter import ttk, filedialog, messagebox

import pyimglib.transcoding.statistics
from . import tagResponse
import parser
import config

logger = logging.getLogger(__name__)


class GUI:
    def __init__(self, id_list):
        self._root = Tk()

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
        #if (self.dl_process is None) or (not self.dl_process.is_alive()):
        #    self.start_downloader()

    def start_downloader(self):
        self.dl_process = threading.Thread(target=self.download)
        self.dl_process.start()

    def download(self):
        self._dl_btn['state']=DISABLED
        pipe = multiprocessing.Pipe()
        try:
            while self._list.size() > 0:
                id_list = self._list.get(0, tkinter.END)
                self._list.delete(0, tkinter.END)

                map_list = list()
                for raw_id in id_list:
                    _parser = None
                    try:
                        _parser = parser.get_parser(raw_id, config.use_medialib_db)
                    except parser.exceptions.NotBoorusPrefixError as e:
                        logger.exception("invalid prefix in {}".format(e.url))
                        continue
                    except parser.exceptions.SiteNotSupported as e:
                        logger.exception("Site not supported {}".format(e.url))
                        continue
                    try:
                        data = _parser.get_data()
                    except IndexError:
                        continue
                    try:
                        parsed_tags = _parser.tagIndex()
                    except KeyError:
                        continue
                    outdir = tagResponse.find_folder(parsed_tags)
                    if not os.path.isdir(outdir):
                        os.makedirs(outdir)
                    dm = download_manager.make_download_manager(_parser)
                    map_list.append((dm, outdir, data, parsed_tags))
                random.shuffle(map_list)
                dl_pool = multiprocessing.Pool(processes=config.workers)
                results = dl_pool.map(download_manager.save_call, map_list, chunksize=1)
                pyimglib.transcoding.statistics.update_stats(results)
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
