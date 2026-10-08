"""
Investigation, Evidence Packet, Verifier, Brief, and Q&A Tests for Vigil-X.

Covers:
- Evidence packet construction with factual provenance
- Deterministic brief generation answering the 6 mandatory questions
- Deterministic verifier catching hallucinations and unsupported numbers
- Verifier rejecting forbidden conclusive fraud phrases
- Restricted investigator Q&A whitelist enforcement
- Q&A refusal of out-of-scope / free-form queries
"""
import pytest
from contracts.investigation import EvidencePacket
from db.database import get_db_connection, init_db
from db.loader import rebuild_database
from generator.synthetic_data import generate_synthetic_data
from investigation.brief_generator import generate_deterministic_brief, generate_investigation_brief
from investigation.evidence_packet import build_evidence_packet
from investigation.qa import answer_investigator_question
from investigation.verifier import verify_brief
from rules.runner import run_network_behavior_rules


@pytest.fixture(scope="module")
def sample_conn():
    """Create in-memory SQLite connection loaded with sample pipeline data."""
    test_db = "test_investigation.db"
    init_db(test_db)
    data = generate_synthetic_data(n_providers=20, n_members=200, n_facilities=5, n_months=6, seed=42)
    alerts = run_network_behavior_rules(data)
    rebuild_database(db_path=test_db, data_dict=data, alerts=alerts)

    conn = get_db_connection(test_db)
    yield conn
    conn.close()
    import os
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except OSError:
            pass


def test_evidence_packet_construction(sample_conn):
    """Evidence packet contains structured provenance boundaries."""
    # Find an active case
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    case_id = row["case_id"]

    packet = build_evidence_packet(sample_conn, case_id)
    assert packet.case_id == case_id
    assert packet.risk_score > 0
    assert packet.exposure_high >= packet.exposure_low
    assert len(packet.cited_rule_ids) > 0
    assert len(packet.cited_provider_ids) > 0
    assert isinstance(packet.top_reasons, list)
    assert packet.synthetic is True
    assert "as_of" in packet.model_dump()


def test_deterministic_brief_generation(sample_conn):
    """Deterministic brief answers all 6 questions and passes verification."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    case_id = row["case_id"]

    packet = build_evidence_packet(sample_conn, case_id)
    brief = generate_deterministic_brief(packet)

    assert brief.case_id == case_id
    assert "Prioritized for human investigation" in brief.why_prioritized
    assert len(brief.recommended_steps) >= 3
    assert len(brief.benign_explanations) > 0
    assert len(brief.limitations) > 0
    assert brief.generated_by == "deterministic_fallback"
    assert brief.verified is True
    assert brief.verification_report.verified is True
    assert brief.verification_report.issues == []


def test_verifier_catches_hallucinated_claim(sample_conn):
    """Verifier detects claim IDs not present in evidence packet."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    packet = build_evidence_packet(sample_conn, row["case_id"])

    bad_narrative = "Provider submitted fraudulent claim C9999999 for unsupported procedures."
    v_res = verify_brief(bad_narrative, packet)
    assert v_res.verified is False
    assert any("C9999999" in issue for issue in v_res.issues)


def test_verifier_catches_forbidden_phrases(sample_conn):
    """Verifier rejects conclusive fraud statements."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    packet = build_evidence_packet(sample_conn, row["case_id"])

    bad_narrative = "Analysis completed. Billing fraud confirmed for this clinic."
    v_res = verify_brief(bad_narrative, packet)
    assert v_res.verified is False
    assert any("Forbidden conclusive phrasing" in issue for issue in v_res.issues)


def test_verifier_catches_excessive_dollars(sample_conn):
    """Verifier rejects monetary amounts greatly exceeding evidence bounds."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    packet = build_evidence_packet(sample_conn, row["case_id"])

    huge_amount = f"${packet.exposure_high * 10:,.2f}"
    bad_narrative = f"The total unverified loss is {huge_amount}."
    v_res = verify_brief(bad_narrative, packet)
    assert v_res.verified is False
    assert any("exceeds case exposure bound" in issue for issue in v_res.issues)


def test_restricted_qa_whitelist_answers(sample_conn):
    """Q&A answers valid questions strictly using grounded facts."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    case_id = row["case_id"]

    # 1. Why flagged
    res_why = answer_investigator_question(sample_conn, case_id, "Why was this case flagged?")
    assert res_why.matched_intent == "WHY_FLAGGED"
    assert "risk score" in res_why.answer.lower()
    assert len(res_why.citations) > 0

    # 2. Financial exposure
    res_exp = answer_investigator_question(sample_conn, case_id, "What is the financial exposure?")
    assert res_exp.matched_intent == "FINANCIAL_EXPOSURE"
    assert "$" in res_exp.answer

    # 3. Supporting claims
    res_cl = answer_investigator_question(sample_conn, case_id, "Show supporting claims")
    assert res_cl.matched_intent == "SUPPORTING_CLAIMS"

    # 4. Member impact
    res_mem = answer_investigator_question(sample_conn, case_id, "What is the member impact?")
    assert res_mem.matched_intent == "MEMBER_IMPACT"


def test_restricted_qa_refuses_out_of_scope(sample_conn):
    """Q&A politely refuses out-of-scope or ungrounded queries."""
    row = sample_conn.execute("SELECT case_id FROM cases LIMIT 1;").fetchone()
    case_id = row["case_id"]

    res_sql = answer_investigator_question(sample_conn, case_id, "SELECT * FROM users WHERE admin = 1")
    assert res_sql.matched_intent == "UNKNOWN"
    assert "outside the whitelisted" in res_sql.answer
    assert "Free-form SQL" in res_sql.answer
