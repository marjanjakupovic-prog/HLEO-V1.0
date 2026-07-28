from collectors.reddit import RedditCollector
from collectors.pubmed import PubMedCollector
from collectors.europepmc import EuropePMCCollector
from collectors.clinicaltrials import ClinicalTrialsCollector
from core.extractor import LLMExtractor
from core.validator import HLEOValidator
from core.judge import HLEOJudge
from search.source_fetcher import SourceFetcher


import logging

logger = logging.getLogger(__name__)


class HLEOPipeline:

    def __init__(self):
        self.collector = RedditCollector()
        self.pubmed = PubMedCollector()
        self.europepmc = EuropePMCCollector()
        self.clinicaltrials = ClinicalTrialsCollector()
        self.extractor = LLMExtractor()
        self.validator = HLEOValidator()
        self.judge = HLEOJudge()
        self.fetcher = SourceFetcher()

    def collect(self, query: str):
    reddit_posts = self.collector.search(query, limit=10)
    pubmed_articles = self.pubmed.search(query, limit=3)
    europepmc_articles = self.europepmc.search(query, limit=3)
    clinical_trials = self.clinicaltrials.search(query, limit=3)

    return {
        "reddit": reddit_posts,
        "pubmed": pubmed_articles,
        "europepmc": europepmc_articles,
        "clinicaltrials": clinical_trials,
    }

    def process(self, query: str):
        logger.info("Pipeline avviata")

        data = self.collect(query)

        posts = data["reddit"]
        articles = data["pubmed"]
        europe_articles = data["europepmc"]
        clinical_trials = data["clinicaltrials"]

        logger.info(f"Post Reddit: {len(posts)}")
        logger.info(f"Articoli PubMed: {len(articles)}")

    if (
        not posts
        and not articles
        and not europe_articles
        and not clinical_trials
    ):
    logger.warning("Nessun dato trovato")
    return []

        results = []

        # Salva gli articoli PubMed
        for article in articles:
            results.append({
                "type": "pubmed",
                "article": article,
            })

        for article in europe_articles:
            results.append({
            "type": "europepmc",
            "article": article,
            })

        for trial in clinical_trials:
            results.append({
            "type": "clinicaltrials",
            "trial": trial,
            })
        # Elabora i post Reddit
        for post in posts:
            try:
                raw_sources = self.fetcher.fetch(post.url)

                profile = self.extractor.extract(post.text)
                logger.info("Estrazione completata")

                validation = self.validator.validate(
                    profile,
                    raw_sources,
                    post.created_at,
                )
                logger.info("Validazione completata")

                judge_result = self.judge.evaluate(
                    profile.baseline_status.value,
                    profile.post_treatment_status.value,
                    validation.passed_validation,
                    profile.post_treatment_status.support_strength,
                    profile.conflict_detected,
                    profile.episode_id,
                )
                logger.info("Giudizio completato")

                results.append({
                    "type": "reddit",
                    "post": post,
                    "profile": profile,
                    "validation": validation,
                    "judge": judge_result,
                })

            except Exception as e:
                logger.exception(
                    f"Errore durante l'elaborazione del post {post.url}: {e}"
                )

        return results