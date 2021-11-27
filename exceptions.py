#!/usr/bin/python3
# -*- coding: utf-8 -*-
#exceptions by mfg637


class InvalidFileName(Exception):
	def __init__(self, filename):
		self.filename = filename


class SiteNotSupported(Exception):
	def __init__(self, url):
		self.url = url


class NotBoorusPrefixError(Exception):
	def __init__(self, url):
		self.url = url
