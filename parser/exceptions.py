

class SiteNotSupported(Exception):
	def __init__(self, url):
		self.url = url


class NotBoorusPrefixError(Exception):
	def __init__(self, url):
		self.url = url


class NotProperlyInitialisedParser(Exception):
	def __init__(self):
		super(NotProperlyInitialisedParser, self).__init__("Tag Indexer instance is not set")
