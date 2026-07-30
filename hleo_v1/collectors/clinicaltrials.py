import requests

from core.search_result import SearchResult


class ClinicalTrialsCollector:
    API_URL = "https://clinicaltrials.gov/api/v2/studies"

    def search(self, query: str, limit: int = 5):
        r = requests.get(
            self.API_URL,
            params={"query.term": query, "pageSize": limit,
                    "fields": "NCTId,BriefTitle,BriefSummary,DetailedDescription,"
                              "OverallStatus,Condition,InterventionName"},
            timeout=20,
        )
        r.raise_for_status()
        studies = r.json().get("studies", [])

        results = []
        for study in studies:
            proto = study.get("protocolSection", {})
            ident = proto.get("identificationModule", {})
            status_mod = proto.get("statusModule", {})
            cond_mod = proto.get("conditionsModule", {})
            desc_mod = proto.get("descriptionModule", {})
            interv_mod = proto.get("armsInterventionsModule", {})

            brief = desc_mod.get("briefSummary", "")
            detailed = desc_mod.get("detailedDescription", "")
            abstract = (brief + "\n\n" + detailed).strip()

            interventions = [
                i.get("interventionName", "")
                for i in interv_mod.get("interventions", [])
            ]

            results.append(
                SearchResult(
                    title=ident.get("briefTitle", ""),
                    source="ClinicalTrials.gov",
                    abstract=abstract,
                    metadata={
                        "nct_id": ident.get("nctId", ""),
                        "condition": cond_mod.get("conditions", []),
                        "status": status_mod.get("overallStatus", ""),
                        "interventions": interventions,
                    },
                )
            )
        return results
