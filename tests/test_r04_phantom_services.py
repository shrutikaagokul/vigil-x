"""
Tests for R04 — Phantom Services Detection.

Covers:
  1. Service after member death (CRITICAL)
  2. Service after member termination (HIGH)
  3. Service during overlapping inpatient stay at different facility (HIGH)
  4. Service at facility before open / after close (HIGH)
  5. Service on facility non-operating day (MEDIUM)
  6. Orphan ambulance without ER/facility claim (MEDIUM)
  7. Empty inputs & edge cases
"""

import pandas as pd
import pytest

from vigilx.models.alert import Severity
from vigilx.rules.r04_phantom_services import PhantomServicesRule

_TEST_CONFIG = {
    "rules": {
        "R04": {
            "enabled": True,
            "version": "1.0",
            "severity_deceased": "CRITICAL",
            "severity_terminated": "HIGH",
            "severity_inpatient_overlap": "HIGH",
            "severity_facility_closed": "HIGH",
            "severity_non_operating_day": "MEDIUM",
            "severity_orphan_ambulance": "MEDIUM",
            "severity_ghost_member": "LOW",
            "termination_grace_days": 0,
            "ambulance_match_window_days": 1,
            "ambulance_cpt_prefixes": ["A042"],
            "facility_cpt_prefixes": ["9928"],
        }
    }
}


class TestR04PhantomServices:

    def test_service_after_member_death(self):
        """Claims billed with service_from > death_date trigger CRITICAL alert."""
        members = pd.DataFrame([
            {"member_id": "M_DECEASED", "death_date": pd.Timestamp("2024-01-10")},
            {"member_id": "M_ALIVE", "death_date": pd.NaT},
        ])
        claims = pd.DataFrame([
            {
                "claim_id": "C_GHOST",
                "member_id": "M_DECEASED",
                "billing_provider_id": "P01",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-01-20"),  # 10 days after death
                "allowed_amount": 150.0,
            },
            {
                "claim_id": "C_VALID_BEFORE",
                "member_id": "M_DECEASED",
                "billing_provider_id": "P01",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-01-05"),  # Before death: valid
                "allowed_amount": 150.0,
            },
            {
                "claim_id": "C_ALIVE",
                "member_id": "M_ALIVE",
                "billing_provider_id": "P01",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-01-20"),
                "allowed_amount": 150.0,
            },
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "members": members})

        death_alerts = [a for a in alerts if "deceased" in a.evidence[0].plain_text.lower() or "death" in a.evidence[0].plain_text.lower()]
        assert len(death_alerts) == 1
        assert death_alerts[0].claim_ids == ["C_GHOST"]
        assert death_alerts[0].severity == Severity.CRITICAL

    def test_service_after_termination(self):
        """Claims billed after coverage termination trigger HIGH alert."""
        members = pd.DataFrame([
            {"member_id": "M_TERM", "termination_date": pd.Timestamp("2024-02-01"), "death_date": pd.NaT},
        ])
        claims = pd.DataFrame([
            {
                "claim_id": "C_POST_TERM",
                "member_id": "M_TERM",
                "billing_provider_id": "P01",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-02-15"),
                "allowed_amount": 200.0,
            },
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "members": members})

        term_alerts = [a for a in alerts if "termination" in a.evidence[0].plain_text.lower() or "terminated" in a.evidence[0].plain_text.lower()]
        assert len(term_alerts) == 1
        assert term_alerts[0].claim_ids == ["C_POST_TERM"]
        assert term_alerts[0].severity == Severity.HIGH

    def test_inpatient_overlap_detection(self):
        """Outpatient service billed during inpatient stay at another facility triggers alert."""
        inpatient_stays = pd.DataFrame([
            {
                "member_id": "M_INPATIENT",
                "facility_id": "HOSPITAL_A",
                "admit_date": pd.Timestamp("2024-02-01"),
                "discharge_date": pd.Timestamp("2024-02-10"),
            }
        ])
        claims = pd.DataFrame([
            {
                "claim_id": "C_CLINIC_OVERLAP",
                "member_id": "M_INPATIENT",
                "billing_provider_id": "CLINIC_B",
                "facility_id": "CLINIC_B",
                "cpt_code": "99214",
                "service_from": pd.Timestamp("2024-02-05"),  # During Hospital A stay
                "allowed_amount": 300.0,
            },
            {
                "claim_id": "C_VALID_POST_DISCHARGE",
                "member_id": "M_INPATIENT",
                "billing_provider_id": "CLINIC_B",
                "facility_id": "CLINIC_B",
                "cpt_code": "99214",
                "service_from": pd.Timestamp("2024-02-15"),  # After discharge
                "allowed_amount": 300.0,
            },
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "inpatient_stays": inpatient_stays})

        overlap_alerts = [a for a in alerts if "inpatient" in a.evidence[0].plain_text.lower()]
        assert len(overlap_alerts) == 1
        assert overlap_alerts[0].claim_ids == ["C_CLINIC_OVERLAP"]

    def test_orphan_ambulance(self):
        """Ambulance claim with no hospital/ER claim in ±1 day flags alert."""
        claims = pd.DataFrame([
            {
                "claim_id": "C_AMB_ORPHAN",
                "member_id": "M200",
                "billing_provider_id": "AMB_CO",
                "cpt_code": "A0428",
                "service_from": pd.Timestamp("2024-03-10"),
                "allowed_amount": 800.0,
            },
            {
                "claim_id": "C_AMB_VALID",
                "member_id": "M201",
                "billing_provider_id": "AMB_CO",
                "cpt_code": "A0428",
                "service_from": pd.Timestamp("2024-03-10"),
                "allowed_amount": 800.0,
            },
            {
                "claim_id": "C_ER_MATCHING",
                "member_id": "M201",
                "billing_provider_id": "ER_HOSP",
                "cpt_code": "99284",  # ER visit on same day
                "service_from": pd.Timestamp("2024-03-10"),
                "allowed_amount": 1200.0,
            },
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims})

        amb_alerts = [a for a in alerts if "ambulance" in a.evidence[0].plain_text.lower()]
        assert len(amb_alerts) == 1
        assert amb_alerts[0].claim_ids == ["C_AMB_ORPHAN"]

    def test_service_at_closed_facility(self):
        """Service billed after facility close date triggers alert."""
        facilities = pd.DataFrame([
            {
                "facility_id": "FAC_CLOSED",
                "open_date": pd.Timestamp("2020-01-01"),
                "close_date": pd.Timestamp("2023-12-31"),
            }
        ])
        claims = pd.DataFrame([
            {
                "claim_id": "C_AFTER_CLOSE",
                "member_id": "M300",
                "facility_id": "FAC_CLOSED",
                "service_from": pd.Timestamp("2024-02-01"),
                "allowed_amount": 500.0,
            }
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "facilities": facilities})

        fac_alerts = [a for a in alerts if "closure" in a.evidence[0].plain_text.lower() or "facility" in a.evidence[0].plain_text.lower()]
        assert len(fac_alerts) >= 1
        assert fac_alerts[0].claim_ids == ["C_AFTER_CLOSE"]

    def test_service_on_non_operating_day(self):
        """Service on Sunday when facility only operates Mon-Fri triggers alert."""
        facilities = pd.DataFrame([
            {
                "facility_id": "FAC_WEEKDAY",
                "operating_days": "Mon,Tue,Wed,Thu,Fri",
            }
        ])
        claims = pd.DataFrame([
            {
                "claim_id": "C_SUNDAY",
                "member_id": "M300",
                "facility_id": "FAC_WEEKDAY",
                "service_from": pd.Timestamp("2024-03-03"),  # Sunday
                "allowed_amount": 250.0,
            }
        ])

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": claims, "facilities": facilities})

        day_alerts = [a for a in alerts if "operates on" in a.evidence[0].plain_text.lower()]
        assert len(day_alerts) >= 1
        assert day_alerts[0].claim_ids == ["C_SUNDAY"]

    def test_ghost_member_weak_signal(self):
        """Member with no claims for a year then 5 claims with same provider is flagged as LOW."""
        # Claims in 2024 only (no history)
        claims_rows = [
            {
                "claim_id": f"C_GHOST_{i}",
                "member_id": "M_GHOST_NEW",
                "billing_provider_id": "PRV_SUS",
                "cpt_code": "99213",
                "service_from": pd.Timestamp("2024-06-01") + pd.Timedelta(days=i),
                "allowed_amount": 100.0,
            }
            for i in range(5)
        ]
        # Historical claim for another member in 2022
        claims_rows.append({
            "claim_id": "C_OLD",
            "member_id": "M_HISTORICAL",
            "billing_provider_id": "PRV_NORM",
            "cpt_code": "99213",
            "service_from": pd.Timestamp("2022-01-01"),
            "allowed_amount": 100.0,
        })

        rule = PhantomServicesRule(config=_TEST_CONFIG)
        alerts = rule.detect({"claims": pd.DataFrame(claims_rows)})

        ghost_alerts = [a for a in alerts if "ghost member" in a.evidence[0].plain_text.lower()]
        assert len(ghost_alerts) >= 1
        assert ghost_alerts[0].severity == Severity.LOW

    def test_empty_inputs(self):
        rule = PhantomServicesRule(config=_TEST_CONFIG)
        assert rule.detect({}) == []
        assert rule.detect({"claims": pd.DataFrame()}) == []

