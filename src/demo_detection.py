import json
from vigilx.detection.pipeline import DetectionPipeline
from vigilx.detection.rules import (
    R01DuplicateBilling,
    R02Upcoding,
    R03Unbundling,
    R04PhantomClaims,
    R05ExcessiveUtilization,
    R06ImpossibleTiming,
    R07ReferralAnomalies,
    R08GeographicAnomalies,
    R09SharedIdentityDetection,
    R10BillingBursts
)

def run_demo():
    # 1. Initialize the rules
    rules = [
        R01DuplicateBilling(),
        R02Upcoding(),
        R03Unbundling(),
        R04PhantomClaims(),
        R05ExcessiveUtilization(),
        R06ImpossibleTiming(),
        R07ReferralAnomalies(),
        R08GeographicAnomalies(),
        R09SharedIdentityDetection(),
        R10BillingBursts()
    ]
    
    # 2. Initialize the pipeline
    pipeline = DetectionPipeline(rules=rules)
    
    # 3. Create some dummy claim data designed to trigger a few rules
    dummy_claims = [
        # Trigger R01 (Duplicate Billing)
        {
            "claim_id": "CLM-001",
            "patient_id": "PAT-123",
            "provider_id": "PRV-999",
            "date_of_service": "2026-10-01",
            "procedure_code": "99213",
            "billed_amount": 150.00
        },
        {
            "claim_id": "CLM-002",  # Exact duplicate of CLM-001
            "patient_id": "PAT-123",
            "provider_id": "PRV-999",
            "date_of_service": "2026-10-01",
            "procedure_code": "99213",
            "billed_amount": 150.00
        },
        # Trigger R04 (Phantom Claim - Male getting Hysterectomy)
        {
            "claim_id": "CLM-003",
            "patient_id": "PAT-456",
            "patient_metadata": {"gender": "M"},
            "provider_id": "PRV-888",
            "date_of_service": "2026-10-05",
            "procedure_code": "58150", # Hysterectomy
            "billed_amount": 5000.00
        },
        # Trigger R08 (Geographic Anomaly)
        {
            "claim_id": "CLM-004",
            "patient_id": "PAT-789",
            "patient_metadata": {"state": "NY"},
            "provider_id": "PRV-777",
            "service_location_state": "CA",
            "date_of_service": "2026-10-06",
            "procedure_code": "99214", # Routine office visit
            "billed_amount": 200.00
        }
    ]
    
    # 4. Dummy Provider Profiles (for baselines)
    provider_profiles = {
        "PRV-999": {"historical_weekly_avg_billing": 2000.0, "historical_monthly_avg_claims": 50},
        "PRV-888": {"historical_weekly_avg_billing": 10000.0, "historical_monthly_avg_claims": 100}
    }
    
    # 5. Run the pipeline
    print("Running Detection & Behavioral Intelligence Pipeline...\n")
    output = pipeline.run(raw_claims=dummy_claims, provider_profiles=provider_profiles)
    
    # 6. Print the Results
    print("="*50)
    print(f"ALERTS GENERATED: {len(output.alerts)}")
    print("="*50)
    for alert in output.alerts:
        print(f"[{alert.severity}] Rule {alert.rule_id} triggered for Provider {alert.provider_id}")
        
    print("\n" + "="*50)
    print("EVIDENCE DETAILS:")
    print("="*50)
    for ev in output.evidence:
        print(f"- {ev.rule_id}: {ev.description}")
        if ev.estimated_overpayment > 0:
            print(f"  Estimated Overpayment: ${ev.estimated_overpayment:.2f}")
        print(f"  Claims Involved: {', '.join(ev.claim_level_traceability)}")
        
    print("\n" + "="*50)
    print("BEHAVIORAL FEATURES EXTRACTED:")
    print("="*50)
    print(f"Provider Features: {len(output.provider_behavior_features)} records")
    print(f"Temporal Features: {len(output.temporal_features)} records")
    print(f"Geographic Features: {len(output.geographic_features)} records")
    print(f"Referral Features: {len(output.referral_features)} records")

if __name__ == "__main__":
    run_demo()
