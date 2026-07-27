import requests
from datetime import datetime
from typing import List

from collectors.base import RawTestimonial


class RedditCollector:

    def search(self, query: str, limit: int = 10) -> List[RawTestimonial]:

        url = f"https://www.reddit.com/search.json?q={query}&limit={limit}"

        headers = {
            "User-Agent": "HLEO/1.0"
        }

        r = requests.get(url, headers=headers, timeout=20)

        if r.status_code != 200:
            return []

        data = r.json()

        risultati = []

        for post in data["data"]["children"]:

            p = post["data"]

            risultati.append(
                RawTestimonial(
                    source="reddit",
                    url="https://reddit.com" + p["permalink"],
                    title=p["title"],
                    text=p["selftext"],
                    author=p["author"],
                    created_at=datetime.fromtimestamp(p["created_utc"]),
                )
            )

        return risultati