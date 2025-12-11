from . import philomena, Parser

FILENAME_PREFIX = "ta"
ORIGIN = "tantabus"


class TantabusAIParser(philomena.Philomena):
    @staticmethod
    def get_domain_name_s():
        return "tantabus.ai"

    def get_filename_prefix(self):
        return FILENAME_PREFIX

    def get_origin_name(self):
        return ORIGIN

    def get_domain_name(self) -> str:
        return TantabusAIParser.get_domain_name_s()

    def custom_tag_processing(self):
        return None

    def custom_data_loading(
        self, _id: int, request_type="images"
    ) -> dict | None:
        return None

    def get_auto_copyright_tags(self) -> set[str]:
        return {"my little pony"}

    def make_rate_limiter(self):
        return Parser.OneRequestPerSecondRateLimiter()

    def enable_html_parsing(self) -> bool:
        return True
