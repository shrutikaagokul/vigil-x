from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class Evidence(BaseModel):
    """
    Evidence details explaining why an alert triggered.
    """
    evidence_id: str = Field(..., description="Unique identifier for the evidence")
    rule_id: str = Field(..., description="ID of the rule that generated this evidence")
    description: str = Field(..., description="Human-readable explanation of the evidence")
    false_positive_notes: Optional[str] = Field(None, description="Notes to mitigate false positive risks")
    estimated_overpayment: float = Field(0.0, description="Estimated financial impact in dollars")
    claim_level_traceability: List[str] = Field(default_factory=list, description="List of Claim IDs related to this evidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    """
    Actionable flags raised by rule triggers.
    """
    alert_id: str = Field(..., description="Unique identifier for the alert")
    provider_id: str = Field(..., description="NPI or unique ID of the provider")
    rule_id: str = Field(..., description="ID of the rule that triggered the alert")
    severity: str = Field(..., description="Severity level: LOW, MEDIUM, HIGH, CRITICAL")
    evidence_ids: List[str] = Field(default_factory=list, description="List of evidence IDs associated with this alert")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ClaimBehaviorFeatures(BaseModel):
    claim_id: str
    features: Dict[str, float] = Field(default_factory=dict)

class ProviderBehaviorFeatures(BaseModel):
    provider_id: str
    features: Dict[str, float] = Field(default_factory=dict)

class TemporalFeatures(BaseModel):
    entity_id: str
    entity_type: str = Field(..., description="'provider' or 'claim'")
    features: Dict[str, float] = Field(default_factory=dict)

class GeographicFeatures(BaseModel):
    entity_id: str
    entity_type: str
    features: Dict[str, float] = Field(default_factory=dict)

class ReferralFeatures(BaseModel):
    provider_id: str
    features: Dict[str, float] = Field(default_factory=dict)

class DetectionOutput(BaseModel):
    """
    The final output payload from the Detection & Behavioral Intelligence module.
    """
    alerts: List[Alert] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    claim_behavior_features: List[ClaimBehaviorFeatures] = Field(default_factory=list)
    provider_behavior_features: List[ProviderBehaviorFeatures] = Field(default_factory=list)
    temporal_features: List[TemporalFeatures] = Field(default_factory=list)
    geographic_features: List[GeographicFeatures] = Field(default_factory=list)
    referral_features: List[ReferralFeatures] = Field(default_factory=list)
