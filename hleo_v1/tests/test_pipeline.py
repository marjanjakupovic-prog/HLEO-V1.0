import pytest
from datetime import datetime, timezone
from core.validator import HLEOValidator
from core.schemas import ExtractedClinicalProfile, ClinicalStatus, EvidenceQuote
from core.judge import HLEOJudge, ClinicalCategory

def test_validator_detects_hallucination():
    profile = ExtractedClinicalProfile(
        episode_id="T1", user_id="U1", conflict_detected=False,
        baseline_status=ClinicalStatus(value="moderata", support_strength=0.9, supporting_quotes=[
            EvidenceQuote(verbatim_text="capelli perfetti", source_url="http://x.com", post_date="2023-01-01T12:00:00Z")
        ]),
        post_treatment_status=ClinicalStatus(value="tornata_come_prima", support_strength=0.9, supporting_quotes=[])
    )
    raw = {"http://x.com": "ho perso i capelli"}
    report = HLEOValidator.validate(profile, raw, datetime.now(timezone.utc))
    assert not report.passed_validation
    assert report.errors[0].error_code == "VAL_E01"

def test_judge_logic_cat_b():
    res = HLEOJudge.evaluate("moderata", "tornata_come_prima", True, 0.8, False, "T1")
    assert res.assigned_category == ClinicalCategory.CAT_B
    assert not res.adjudication_required
