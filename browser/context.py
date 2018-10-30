#!/usr/bin/python3
# -*- coding: utf-8 -*- 

from . import net

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


class Images(Context):
	def __init__(self):
		self.page = 1
	def makeRequest(self, **kwargs):
		return net.parse_json("images.json", page=self.page, **kwargs)["images"]


class Search(Context):
	def __init__(self, query):
		self.page = 1
		self.query = query
	def makeRequest(self, **kwargs):
		return net.parse_json("search.json", q=self.query, page=self.page, **kwargs)["search"]
