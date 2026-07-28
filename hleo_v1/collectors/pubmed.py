import requests
import time

from core.search_result import SearchResult

class PubMedCollector:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    DETAIL_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def search(self, query: str, limit: int = 10):
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": limit,
            "retmode": "json",
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        ids = data["esearchresult"]["idlist"]

        if not ids:
            return []

        time.sleep(1)

        response = requests.get(
            self.DETAIL_URL,
            params={
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
            },
            timeout=15,
        )
        response.raise_for_status()

        details = response.json()

        results = []

        for pmid in ids:
            article = details["result"].get(pmid, {})

            results.append(
                SearchResult(
                    title=article.get("title", ""),
                    source="PubMed",
                    authors=[
                        author.get("name", "")
                        for author in article.get("authors", [])
                    ],
                    pmid=pmid,
                    metadata={
                        "journal": article.get("fulljournalname", ""),
                        "pubdate": article.get("pubdate", ""),
                    },
                )
            )

        return results