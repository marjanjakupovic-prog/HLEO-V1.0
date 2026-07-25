import os
import json
from openai import OpenAI
from core.schemas import ExtractedClinicalProfile
import logging

logger = logging.getLogger(__name__)

class LLMExtractor:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"

    def extract(self, timeline_json: str) -> ExtractedClinicalProfile:
        logger.info("Avvio estrazione LLM.")
        system_prompt = "Sei un estrattore clinico in tricologia. Estrai il profilo clinico nel formato JSON richiesto."
        schema = ExtractedClinicalProfile.model_json_schema()
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Timeline: {timeline_json}\nSchema: {json.dumps(schema)}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return ExtractedClinicalProfile.model_validate_json(response.choices[0].message.content)
