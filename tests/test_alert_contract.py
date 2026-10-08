"""Tests for the shared Alert/Evidence contract."""
import pytest
from contracts.alert import Alert, Evidence, Severity


def test_alert_creation():
    ev = Evidence(
        evidence_id="E-R06-001", rule_id="R06", rule_version="1.0.0",
        claim_ids=["C001"], fields_matched=["service_minutes"],
        plain_text="Test evidence", est_overpay=0, severity="HIGH",
    )
    alert = Alert(
        alert_id="A-R06-001", rule_id="R06", rule_version="1.0.0",
        entity_type="provider", entity_id="P001",
        claim_ids=["C001"], severity="HIGH",
        est_dollars=0, evidence=[ev],
    )
    assert alert.rule_id == "R06"
    assert len(alert.evidence) == 1


def test_alert_validation_pass():
    ev = Evidence(
        evidence_id="E-R06-001", rule_id="R06", rule_version="1.0.0",
        claim_ids=["C001"], fields_matched=["field1"],
        plain_text="Valid evidence",
    )
    alert = Alert(
        alert_id="A-R06-001", rule_id="R06", rule_version="1.0.0",
        entity_type="provider", entity_id="P001",
        claim_ids=["C001"], severity="HIGH",
        est_dollars=0, evidence=[ev],
    )
    errors = alert.validate()
    assert errors == []


def test_alert_validation_fail():
    alert = Alert(
        alert_id="", rule_id="", rule_version="1.0.0",
        entity_type="", entity_id="",
        claim_ids=[], severity="INVALID",
        est_dollars=0, evidence=[],
    )
    errors = alert.validate()
    assert len(errors) >= 4  # missing id, rule, entity_type, entity_id, evidence, severity


def test_alert_to_dict():
    ev = Evidence(
        evidence_id="E-R06-001", rule_id="R06", rule_version="1.0.0",
        claim_ids=["C001"], fields_matched=["field1"],
        plain_text="Test",
    )
    alert = Alert(
        alert_id="A-R06-001", rule_id="R06", rule_version="1.0.0",
        entity_type="provider", entity_id="P001",
        claim_ids=["C001"], severity="HIGH",
        est_dollars=0, evidence=[ev],
    )
    d = alert.to_dict()
    assert d["rule_id"] == "R06"
    assert len(d["evidence"]) == 1
    assert d["evidence"][0]["plain_text"] == "Test"


def test_severity_enum():
    assert Severity.LOW.value == "LOW"
    assert Severity.MEDIUM.value == "MEDIUM"
    assert Severity.HIGH.value == "HIGH"
    assert Severity.CRITICAL.value == "CRITICAL"


def test_evidence_generate_id():
    eid = Evidence.generate_id("R06")
    assert eid.startswith("E-R06-")


def test_alert_generate_id():
    aid = Alert.generate_id("R07")
    assert aid.startswith("A-R07-")
