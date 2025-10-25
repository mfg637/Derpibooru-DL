import unittest
from interactive_mode import types


class TestUrlRegex(unittest.TestCase):
    def test_url(self):
        test_wikipedia = types.url_regex.fullmatch("https://www.wikipedia.org/")
        self.assertIsNotNone(test_wikipedia)
        test_local_ftp = types.url_regex.fullmatch(
            "ftp://192.168.1.12/file.txt"
        )
        self.assertIsNotNone(test_local_ftp)
        test_params = types.url_regex.fullmatch(
            "http://example.com/?pi=3.14&sky=blue"
        )
        self.assertIsNotNone(test_params)
        test_hashtag = types.url_regex.fullmatch(
            "http://example.com/#chapter-2"
        )
        self.assertIsNotNone(test_hashtag)
        test_path = types.url_regex.fullmatch("http://a.com/path/to/page.html")
        self.assertIsNotNone(test_path)
        test_path_2 = types.url_regex.fullmatch("http://a.com/path/to/page/")
        self.assertIsNotNone(test_path_2)
        test_string = types.url_regex.fullmatch("Lorem ipsum")
        self.assertIsNone(test_string)
        test_lowercase_string = types.url_regex.fullmatch("foo")
        self.assertIsNone(test_lowercase_string)
        test_natural_number = types.url_regex.fullmatch("128")
        self.assertIsNone(test_natural_number)
        test_real_number = types.url_regex.fullmatch("1.25")
        self.assertIsNone(test_real_number)
        test_poxis_path = types.url_regex.fullmatch("/usr/local/bin")
        self.assertIsNone(test_poxis_path)
        test_poxis_path_2 = types.url_regex.fullmatch("/usr/local/bin/")
        self.assertIsNone(test_poxis_path_2)

    def test_url_https(self):
        test_wikipedia = types.https_url_regex.fullmatch(
            "https://www.wikipedia.org/"
        )
        self.assertIsNotNone(test_wikipedia)
        test_params = types.https_url_regex.fullmatch(
            "https://example.com/?pi=3.14&sky=blue"
        )
        self.assertIsNotNone(test_params)
        test_hashtag = types.https_url_regex.fullmatch(
            "https://example.com/#chapter-2"
        )
        self.assertIsNotNone(test_hashtag)
        test_path = types.https_url_regex.fullmatch(
            "https://a.com/path/to/page.html"
        )
        self.assertIsNotNone(test_path)
        test_path_2 = types.https_url_regex.fullmatch(
            "https://a.com/path/to/page/"
        )
        self.assertIsNotNone(test_path_2)
        test_string = types.https_url_regex.fullmatch("Lorem ipsum")
        self.assertIsNone(test_string)
        test_lowercase_string = types.https_url_regex.fullmatch("foo")
        self.assertIsNone(test_lowercase_string)
        test_natural_number = types.https_url_regex.fullmatch("128")
        self.assertIsNone(test_natural_number)
        test_real_number = types.https_url_regex.fullmatch("1.25")
        self.assertIsNone(test_real_number)
        test_poxis_path = types.https_url_regex.fullmatch("/usr/local/bin")
        self.assertIsNone(test_poxis_path)
        test_poxis_path_2 = types.https_url_regex.fullmatch("/usr/local/bin/")
        self.assertIsNone(test_poxis_path_2)

        test_image_id = types.https_url_regex.fullmatch(
            "https://derpibooru.org/images/199890"
        )
        self.assertIsNotNone(test_image_id)
        test_image_with_parameters = types.https_url_regex.fullmatch(
            "https://derpibooru.org/images/252754?sort[]=0.9957869&sort[]=252754&sd=desc&sf=random%3A3923451479&q=sb+%26%26+ts"
        )
        self.assertIsNotNone(test_image_with_parameters)
