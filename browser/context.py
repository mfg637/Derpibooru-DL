#!/usr/bin/python3
# -*- coding: utf-8 -*- 

from . import net
from math import ceil

class Context:
	def __init__(self):
		raise NotImplementedError
	def next_page(self):
		self.page += 1
	def prev_page(self):
		if self.page>1:
			self.page -= 1
	def go_to(self, page):
		if page>1:
			self.page = page
		else:
			self.page = 1
	def makeRequest(self, **kwargs):
		raise NotImplementedError
	def getPageNumber(self):
		return self.page
	def getTotalPages(self):
		return None


class Images(Context):
	def __init__(self):
		self.page = 1
	def makeRequest(self, **kwargs):
		data = net.parse_json("images.json", page=self.page, **kwargs)
		if len(data["images"]) == 0:
			raise EOFError
		return data["images"]


class Search(Context):
	def __init__(self, query):
		self.page = 1
		self.query = query
		self._items_per_page = None
		self._total_items = 0
	def makeRequest(self, **kwargs):
		data = net.parse_json("search.json", q=self.query, page=self.page, **kwargs)
		if self._items_per_page is None:
			self._items_per_page = len(data["search"])
			if self._items_per_page == 0:
				raise EOFError
		self._total_items = data["total"]
		return data['search']
	def getTotalPages(self):
		if self._total_items > 0:
			return ceil(self._total_items/self._items_per_page)
		else:
			return None
