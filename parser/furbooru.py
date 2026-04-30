from . import philomena, Parser


FILENAME_PREFIX = "fb"
ORIGIN = "furbooru"


class FurbooruParser(philomena.Philomena):
    @staticmethod
    def get_domain_name_s():
        return "furbooru.org"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return FurbooruParser.get_domain_name_s()

    def get_auto_copyright_tags(self):
        return set()

    def custom_tag_processing(self):
        return None

    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict | None:
        return None

    def make_rate_limiter(self):
        return Parser.OneRequestPerSecondRateLimiter()

    def enable_html_parsing(self) -> bool:
        return True
