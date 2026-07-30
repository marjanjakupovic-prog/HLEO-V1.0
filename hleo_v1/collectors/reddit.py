import requests
from datetime import datetime
from typing import List

from collectors.base import RawTestimonial


class RedditCollector:

    def search(self, query: str, limit: int = 10) -> List[RawTestimonial]:

        url = (
            f"https://www.reddit.com/search.json"
            f"?q={requests.utils.quote(query)}&limit={limit}&type=link&sort=relevance"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
            ),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
        }

        try:
            r = requests.get(url, headers=headers, timeout=20)
        except Exception:
            return []

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