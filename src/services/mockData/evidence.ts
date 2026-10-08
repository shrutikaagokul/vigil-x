/**
 * Mock Evidence fixtures.
 * Strictly adheres to contracts/alert.py and non-accusatory terminology rules.
 */
import { Evidence } from '@/types/alert';

export const MOCK_EVIDENCE: readonly Evidence[] = [
  // Hero Case Evidence (CASE-2024-0042 / P0042 Mercer)
  {
    evidence_id: 'E-R06-TIMING-001',
    rule_id: 'R06',
    rule_version: '1.0.0',
    claim_ids: ['C1023', 'C1026', 'C1027'],
    fields_matched: ['service_start_ts', 'service_end_ts', 'service_minutes', 'provider_id'],
    plain_text:
      'Daily direct patient service minutes reached 1,120 minutes (18.7 hours) across 24 claims on 2024-09-12, exceeding the operational physiological threshold of 960 minutes.',
    est_overpay: 3840.0,
    severity: 'HIGH',
    fp_notes: 'Evaluate whether mid-level providers (PA/NP) billed under supervising physician NPI without modifier.',
  },
  {
    evidence_id: 'E-R06-TRAVEL-002',
    rule_id: 'R06',
    rule_version: '1.0.0',
    claim_ids: ['C1026', 'C1027'],
    fields_matched: ['service_end_ts', 'service_start_ts', 'latitude', 'longitude', 'facility_id'],
    plain_text:
      'Required travel speed of 78.4 mph calculated between consecutive in-person services in Fulton County and Nelson County (95.2 miles elapsed in 45 minutes).',
    est_overpay: 855.5,
    severity: 'CRITICAL',
    fp_notes: 'Verify if service location on claim C1027 corresponds to a secondary branch office billing error.',
  },
  {
    evidence_id: 'E-R07-RECLOOP-003',
    rule_id: 'R07',
    rule_version: '1.0.0',
    claim_ids: ['C1024', 'C1028'],
    fields_matched: ['referring_provider_id', 'target_provider_id', 'referral_count'],
    plain_text:
      'Indicators consistent with reciprocal referral concentration: 82.4% of P0042 physical therapy referrals directed to P0043, while P0043 referred 38 patients back to P0042 in trailing 90 days.',
    est_overpay: 14200.0,
    severity: 'HIGH',
    fp_notes: 'Check for legitimate co-located multidisciplinary practice arrangement.',
  },
  {
    evidence_id: 'E-R07-LABSAME-004',
    rule_id: 'R07',
    rule_version: '1.0.0',
    claim_ids: ['C1023', 'C1025'],
    fields_matched: ['service_date', 'procedure_code', 'referring_provider_id', 'paid_amount'],
    plain_text:
      'Same-day referral pattern identified: 94.6% of patient visits at P0042 resulted in same-day definitive high-complexity toxicology panel G0483 billed by BioMatrix Labs (P0046).',
    est_overpay: 36900.0,
    severity: 'CRITICAL',
    fp_notes: 'Review medical necessity documentation for routine multi-class drug testing.',
  },
  {
    evidence_id: 'E-R08-GEODIST-005',
    rule_id: 'R08',
    rule_version: '1.0.0',
    claim_ids: ['C1027'],
    fields_matched: ['member_latitude', 'member_longitude', 'provider_latitude', 'provider_longitude'],
    plain_text:
      'Geographic distribution anomaly: Provider billed routine pain management claims across 6 non-contiguous counties with average patient travel distance of 94.8 miles (peer median 18.2 miles).',
    est_overpay: 8400.0,
    severity: 'MEDIUM',
    fp_notes: 'Subspecialty regional referral catchment area may partially account for wide distribution.',
  },
  {
    evidence_id: 'E-R09-SHARDBK-006',
    rule_id: 'R09',
    rule_version: '1.0.0',
    claim_ids: ['C1023', 'C1024', 'C1028', 'C1030'],
    fields_matched: ['bank_hash', 'provider_id', 'group_id'],
    plain_text:
      'Shared financial routing link: Exact bank account hash match (9a8b7c6d5e4f3a21) resolves across 4 ostensibly independent billing providers (P0042, P0043, P0044, P0047).',
    est_overpay: 0.0, // Identity link establishes network risk, dollar exposure calculated across claims
    severity: 'CRITICAL',
    fp_notes: 'Confirm if providers share an authorized management service organization (MSO) banking arrangement.',
  },
  {
    evidence_id: 'E-R09-SHARDON-007',
    rule_id: 'R09',
    rule_version: '1.0.0',
    claim_ids: ['C1025', 'C1029'],
    fields_matched: ['owner_entity', 'registered_agent', 'tin_hash'],
    plain_text:
      'Common corporate ownership structure: Entity resolution links P0045 (Radiology) and P0046 (Toxicology) under identical parent holding entity Apex Healthcare Holdings LLC.',
    est_overpay: 0.0,
    severity: 'HIGH',
    fp_notes: 'Check state corporate filing history and Stark Law self-referral disclosure declarations.',
  },
  {
    evidence_id: 'E-R10-BURSTSP-008',
    rule_id: 'R10',
    rule_version: '1.0.0',
    claim_ids: ['C1023', 'C1024', 'C1025', 'C1026', 'C1027', 'C1030'],
    fields_matched: ['paid_amount', 'service_date', 'weekly_panel_total'],
    plain_text:
      'Surge billing volume: Trailing 4-week billing total ($184,200) represents a 4.2x spike over historical 12-week median baseline ($43,800/month), exceeding the 3.0x anomaly threshold.',
    est_overpay: 62500.0,
    severity: 'CRITICAL',
    fp_notes: 'Check for recent onboarding of new clinic locations or provider panel expansion.',
  },
  // Additional case evidence
  {
    evidence_id: 'E-R06-DERM-009',
    rule_id: 'R06',
    rule_version: '1.0.0',
    claim_ids: ['C2088'],
    fields_matched: ['service_start_ts', 'service_end_ts', 'member_id'],
    plain_text:
      'Overlapping in-person surgical and evaluation service hours billed across two separate facility locations simultaneously for distinct members.',
    est_overpay: 4200.0,
    severity: 'HIGH',
    fp_notes: 'Check if procedure was performed by resident or fellow under teaching physician.',
  },
  {
    evidence_id: 'E-R10-BURST-010',
    rule_id: 'R10',
    rule_version: '1.0.0',
    claim_ids: ['C3115'],
    fields_matched: ['paid_amount', 'service_date'],
    plain_text:
      'Rapid surge in Level 5 E&M code (99215) billing proportion from 8% to 64% over a 14-day rolling window.',
    est_overpay: 11800.0,
    severity: 'MEDIUM',
    fp_notes: 'Check for EHR template change or billing coder system upgrade.',
  },
];
