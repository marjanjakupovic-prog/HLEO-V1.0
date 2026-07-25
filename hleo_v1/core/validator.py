import re
from datetime import datetime, timezone
from typing import Dict
from core.schemas import ExtractedClinicalProfile, ValidationReport, ValidationItemResult

class HLEOValidator:
    MAX_LOOKBACK = 120

    @classmethod
    def validate(cls, profile: ExtractedClinicalProfile, raw_texts: Dict[str, str], ep_start: datetime) -> ValidationReport:
        errors = []
        quotes = profile.baseline_status.supporting_quotes + profile.post_treatment_status.supporting_quotes
        for q in quotes:
            if not re.match(r'^https?:\/\/', q.source_url):
                errors.append(ValidationItemResult(is_valid=False, error_code="VAL_E02", error_message="URL non valido."))
            try:
                q_date = datetime.fromisoformat(q.post_date.replace('Z', '+00:00'))
                if (ep_start - q_date).days > cls.MAX_LOOKBACK:
                    errors.append(ValidationItemResult(is_valid=False, error_code="VAL_E04", error_message="Baseline fuori finestra."))
            except ValueError:
                errors.append(ValidationItemResult(is_valid=False, error_code="VAL_E04", error_message="Data malformata."))
            raw = raw_texts.get(q.source_url, "")
            clean_verb = re.sub(r'\s+', ' ', q.verbatim_text.strip())
            clean_raw = re.sub(r'\s+', ' ', raw.strip())
            if clean_verb not in clean_raw:
                errors.append(ValidationItemResult(is_valid=False, error_code="VAL_E01", error_message="Citazione allucinata."))
        return ValidationReport(passed_validation=len(errors) == 0, errors=errors)
