import os
import json
import logging

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from core.schemas import ExtractedClinicalProfile
from core.clinical_schema import ClinicalProfile

logger = logging.getLogger(__name__)


class LLMExtractor:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"

    def extract(self, timeline_json: str) -> ExtractedClinicalProfile:
        logger.info("Avvio estrazione LLM.")

        system_prompt = """
Sei un motore di estrazione di informazioni cliniche specializzato in tricologia.

Il tuo unico compito è trasformare il testo ricevuto in un oggetto JSON conforme allo schema fornito.

REGOLE OBBLIGATORIE

- Estrai esclusivamente informazioni esplicitamente presenti nel testo.
- Non inventare dati.
- Non fare inferenze cliniche.
- Non completare campi mancanti.
- Non interpretare ciò che non è scritto.
- Non correggere diagnosi, farmaci, dosaggi o date.
- Mantieni la terminologia originale quando possibile.

GESTIONE DEI DATI MANCANTI

- Se un valore non è presente, usa null.
- Se una lista è assente, restituisci [].
- Non inserire valori di default.
- Non creare informazioni plausibili.

QUALITÀ

- Ogni campo deve poter essere ricondotto al testo sorgente.
- In caso di ambiguità, preferisci null invece di indovinare.
- Non aggiungere spiegazioni, commenti o testo libero.

OUTPUT

Restituisci esclusivamente un JSON valido che rispetti rigorosamente lo schema fornito.
"""

        schema = ClinicalProfile.model_json_schema()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
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

        logger.info("Estrazione completata.")

        data = json.loads(content)

        return ExtractedClinicalProfile.model_validate(data)