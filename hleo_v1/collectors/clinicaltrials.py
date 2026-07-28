import requests

from core.search_result import SearchResult


class ClinicalTrialsCollector:
    BASE_URL = "https://clinicaltrials.gov/api/query/studies"

    def search(self, query: str, limit: int = 5):
        url = "https://clinicaltrials.gov/api/v2/studies"

        params = {
            "query.term": query,
            "pageSize": limit,
        }

        response = requests.get(
            url,
            params=params,
            timeout=20,
        )
        response.raise_for_status()

        data = response.json()

        studies = data.get("studies", [])

        results = []

        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            conditions = protocol.get("conditionsModule", {})

            results.append(
                SearchResult(
                    title=identification.get("briefTitle", ""),
                    source="ClinicalTrials.gov",
                    metadata={
                        "nct_id": identification.get("nctId", ""),
                        "condition": conditions.get("conditions", []),
                        "status": status.get("overallStatus", ""),
                    },
                )
            )

        return results