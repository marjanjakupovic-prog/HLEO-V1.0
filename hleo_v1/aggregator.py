from collectors.pubmed import PubMedCollector
from collectors.europepmc import EuropePMCCollector


class HLEOAggregator:

    def __init__(self):
        self.pubmed = PubMedCollector()
        self.europepmc = EuropePMCCollector()

    def create_key(self, article):
        # 1. DOI
        if article.doi:
            return f"doi:{article.doi.strip().lower()}"

        # 2. PMID
        if article.pmid:
            return f"pmid:{article.pmid}"

        # 3. Europe PMC ID
        if article.metadata.get("id"):
            return f"id:{article.metadata['id']}"

        # 4. Titolo normalizzato
        if article.title:
            return " ".join(article.title.lower().split())

        return None

    def search(self, query: str, limit: int = 5):
        all_results = []

        try:
            all_results.extend(self.pubmed.search(query, limit))
        except Exception as e:
            print(f"PubMed errore: {e}")

        try:
            all_results.extend(self.europepmc.search(query, limit))
        except Exception as e:
            print(f"Europe PMC errore: {e}")

        unique = {}
        final_results = []

        for article in all_results:
            key = self.create_key(article)

            if key not in unique:
                unique[key] = True
                final_results.append(article)

        return final_results