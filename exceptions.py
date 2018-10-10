#!/usr/bin/python3
# -*- coding: utf-8 -*-
#exceptions by mfg637

class invalidFilename(Exception):
	def __init__(self, filename):
		self.filename=filename