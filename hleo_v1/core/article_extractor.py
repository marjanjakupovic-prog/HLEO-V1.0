"""
LLM extractor for scientific articles (PubMed / EuropePMC / ClinicalTrials).
Uses the general ClinicalProfile schema rather than the hair-loss-specific
ExtractedClinicalProfile schema.
"""
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ArticleExtractor:
    MODEL = "gpt-4o"

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None
            logger.warning("OPENAI_API_KEY not set — ArticleExtractor disabled.")

    def extract(self, title: str, abstract: str, source: str) -> dict:
        """
        Extract a structured clinical profile from an article title + abstract.
        Returns a plain dict matching ClinicalProfile (clinical_schema.py).
        Raises RuntimeError if no API key.
        """
        if self.client is None:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        from core.clinical_schema import ClinicalProfile

        schema = ClinicalProfile.model_json_schema()

        text = f"Source: {source}\nTitle: {title}\n\nAbstract:\n{abstract or '(no abstract available)'}"

        system_prompt = (
            "You are a clinical information extraction engine. "
            "Extract a structured clinical profile from the given article title and abstract.\n\n"
            "Rules:\n"
            "- Extract ONLY information explicitly stated in the text.\n"
            "- Do NOT invent data, make inferences, or fill fields not mentioned.\n"
            "- Use null for missing scalar fields; [] for missing list fields.\n"
            "- For 'treatments', list drug names, procedures, and interventions mentioned.\n"
            "- For 'outcomes', list efficacy results, response rates, survival data.\n"
            "- For 'adverse_effects', list side effects and toxicities.\n"
            "- For 'evidence_level', summarise study design (e.g. 'Phase III RCT', 'meta-analysis', 'case report').\n"
            "- Return ONLY a valid JSON object conforming strictly to the schema."
        )

        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"{text}\n\n"
                        f"JSON Schema:\n{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        raw = json.loads(response.choices[0].message.content)

        # Validate against Pydantic model to ensure shape correctness
        profile = ClinicalProfile.model_validate(raw)
        return profile.model_dump()
