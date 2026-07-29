import os
import json
import logging

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(self) -> None:
        self.model = "gpt-4o"
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        else:
            logger.warning(
                "OPENAI_API_KEY not set — LLM extraction disabled. "
                "Reddit posts will be skipped."
            )
            self.client = None

    def extract(self, timeline_json: str):
        if self.client is None:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Cannot perform LLM extraction."
            )

        from core.schemas import ExtractedClinicalProfile
        from core.clinical_schema import ClinicalProfile

        system_prompt = (
            "Sei un motore di estrazione di informazioni cliniche specializzato in tricologia.\n"
            "Il tuo unico compito è trasformare il testo ricevuto in un oggetto JSON conforme "
            "allo schema fornito.\n"
            "Estrai esclusivamente informazioni esplicitamente presenti nel testo. "
            "Non inventare dati. In caso di ambiguità usa null."
        )

        schema = ClinicalProfile.model_json_schema()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Timeline:\n{timeline_json}\n\n"
                        f"Schema JSON:\n{json.dumps(schema, ensure_ascii=False)}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        from core.schemas import ExtractedClinicalProfile
        return ExtractedClinicalProfile.model_validate(data)
