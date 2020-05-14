#!/usr/bin/python3
# -*- coding: utf-8 -*- 

from . import net
from math import ceil
import abc


class Context(abc.ABC):
	def __init__(self):
		pass

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

	@abc.abstractmethod
	def make_request(self, **kwargs):
		raise NotImplementedError

	def get_page_number(self):
		return self.page

	def get_total_pages(self):
		return None


class Search(Context):

	def __init__(self, query):
		super().__init__()
		self.page = 1
		self.query = query
		self._items_per_page = None
		self._total_items = 0

	def make_request(self, **kwargs):
		data = net.parse_json("api/v1/json/search/images", q=self.query, page=self.page, **kwargs)
		#print(data)
		#exit()
		if self._items_per_page is None:
			self._items_per_page = len(data["images"])
			if self._items_per_page == 0:
				raise EOFError
		self._total_items = data["total"]
		return data['images']

	def get_total_pages(self):
		if self._total_items > 0:
			return ceil(self._total_items/self._items_per_page)
		else:
			return None
