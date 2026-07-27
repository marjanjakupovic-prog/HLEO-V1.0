from pydantic import BaseModel
from typing import List, Optional


class ClinicalProfile(BaseModel):

    patient_age: Optional[str] = None
    patient_sex: Optional[str] = None

    diagnosis: List[str] = []

    hair_loss_type: List[str] = []

    disease_stage: Optional[str] = None

    triggers: List[str] = []

    symptoms: List[str] = []

    treatments: List[str] = []

    dosages: List[str] = []

    treatment_duration: List[str] = []

    outcomes: List[str] = []

    adverse_effects: List[str] = []

    laboratory_findings: List[str] = []

    biopsy_findings: List[str] = []

    imaging_findings: List[str] = []

    timeline: List[str] = []

    evidence_level: Optional[str] = None

    citations: List[str] = []

    source_url: Optional[str] = None