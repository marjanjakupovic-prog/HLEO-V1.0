import requests

from core.search_result import SearchResult


class EuropePMCCollector:
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def search(self, query: str, limit: int = 5):
        params = {
            "query": query,
            "format": "json",
            "pageSize": limit,
        }

        response = requests.get(
            self.BASE_URL,
            params=params,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("resultList", {}).get("result", []):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    source="Europe PMC",
                    year=int(item["pubYear"]) if item.get("pubYear") else None,
                    doi=item.get("doi"),
                    metadata={
                        "journal": item.get("journalTitle", ""),
                        "id": item.get("id"),
                    },
                )
            )

        return results