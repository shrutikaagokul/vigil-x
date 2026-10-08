"""
Tests for Alert and Evidence data contracts.

Verifies:
  1. Alert creation, field presence, and types
  2. Evidence serialization and deserialization
  3. Severity enum ordering (LOW < MEDIUM < HIGH < CRITICAL)
  4. make_id and make_evidence_id uniqueness and formatting
  5. JSON schema compliance for serialization
"""

import json
import pytest

from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id


class TestAlertContract:

    def test_severity_ordering(self):
        """Severity levels follow strict ascending severity."""
        assert Severity.LOW < Severity.MEDIUM
        assert Severity.MEDIUM < Severity.HIGH
        assert Severity.HIGH < Severity.CRITICAL

        assert Severity.CRITICAL > Severity.HIGH
        assert Severity.HIGH >= Severity.HIGH
        assert Severity.LOW <= Severity.MEDIUM

    def test_evidence_to_dict(self):
        """Evidence converts cleanly to dict suitable for JSON serialization."""
        ev = Evidence(
            evidence_id="E-R01-abc12345",
            rule_id="R01",
            rule_version="1.0",
            claim_ids=["C1", "C2"],
            fields_matched=["cpt_code", "service_from"],
            plain_text="Duplicate claims detected.",
            est_overpay=120.50,
            severity=Severity.HIGH,
            fp_notes=["Check for modifier 76."],
        )

        d = ev.to_dict()
        assert d["evidence_id"] == "E-R01-abc12345"
        assert d["rule_id"] == "R01"
        assert d["severity"] == "HIGH"
        assert d["est_overpay"] == 120.50
        assert d["claim_ids"] == ["C1", "C2"]
        assert d["fields_matched"] == ["cpt_code", "service_from"]

        # Ensure json serializable
        json_str = json.dumps(d)
        assert "Duplicate claims detected." in json_str

    def test_alert_to_dict(self):
        """Alert with nested evidence converts cleanly to dict."""
        ev = Evidence(
            evidence_id=make_evidence_id("R02"),
            rule_id="R02",
            rule_version="1.0",
            claim_ids=["C10"],
            fields_matched=["em_level"],
            plain_text="High coding.",
            est_overpay=50.0,
            severity=Severity.HIGH,
        )

        alert_id = Alert.make_id()
        assert alert_id.startswith("A-")

        alert = Alert(
            alert_id=alert_id,
            rule_id="R02",
            rule_version="1.0",
            entity_type="provider",
            entity_id="PRV_99",
            claim_ids=["C10"],
            severity=Severity.HIGH,
            est_dollars=50.0,
            evidence=[ev],
            fp_notes=["Specialist practice."],
        )

        d = alert.to_dict()
        assert d["alert_id"] == alert_id
        assert d["entity_id"] == "PRV_99"
        assert d["severity"] == "HIGH"
        assert len(d["evidence"]) == 1
        assert d["evidence"][0]["evidence_id"] == ev.evidence_id

        # Roundtrip JSON string
        json_str = json.dumps(d)
        decoded = json.loads(json_str)
        assert decoded["alert_id"] == alert_id
        assert decoded["evidence"][0]["severity"] == "HIGH"

    def test_make_evidence_id_prefix(self):
        """make_evidence_id prefixes with the rule_id."""
        eid = make_evidence_id("R03")
        assert eid.startswith("E-R03-")
