from collectors.reddit import RedditCollector
from collectors.base import RawTestimonial

from core.extractor import LLMExtractor
from core.validator import HLEOValidator
from core.judge import HLEOJudge


class HLEOPipeline:

    def __init__(self):
        self.collector = RedditCollector()
        self.extractor = LLMExtractor()
        self.validator = HLEOValidator()
        self.judge = HLEOJudge()

def collect(self, query: str):
    return self.collector.search(query, limit=10)

    def process(self, query: str):
    posts = self.collect(query)

    results = []

    for post in posts:
        try:
            profile = self.extractor.extract(post.text)

            results.append({
                "post": post,
                "profile": profile,
            })

        except Exception as e:
            print(f"Pipeline error: {e}")

    return results