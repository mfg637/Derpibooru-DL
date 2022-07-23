

class SiteNotSupported(Exception):
	def __init__(self, url):
		self.url = url


class NotBoorusPrefixError(Exception):
	def __init__(self, url):
		self.url = url

