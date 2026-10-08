/**
 * Mock Queue fixtures and deterministic capacity-aware prioritization calculator.
 *
 * MOCK BEHAVIOR FORMULA NOTICE:
 * This heuristic is a deterministic mock prioritization model designed to reflect
 * investigator capacity allocation. It is NOT the production backend ranking formula.
 */
import { QueueItem, QueueQueryParams, QueueResponse } from '@/types/queue';

export const RAW_MOCK_QUEUE_ITEMS: readonly QueueItem[] = [
  {
    case_id: 'CASE-2024-0042',
    title: 'Multi-Entity Pain & Toxicology Network (Mercer)',
    name: 'Mercer Pain & Toxicology Network',
    subtitle: 'Network case · 6 providers',
    focal_provider_id: 'P0042',
    focal_provider_name: 'Dr. Victor Mercer, MD',
    specialty: 'pain_management',
    priority_score: 96,
    risk_index: 94,
    severity: 'CRITICAL',
    confidence: 'High',
    est_dollars: 412000.0,
    est_overpay: 126695.5,
    exposure_low: 3800000,
    exposure_high: 12000000,
    effort_hours: 31,
    pool: 'network',
    baseline_rank: 38,
    top_reasons: [
      { text: 'Lead doctor bills level-4/5 visits 58% of the time, peers 16%', evidence_chip: 'E7' },
      { text: 'Three providers share one bank account', evidence_chip: 'E3' },
      { text: '63% of referrals stay inside the group', evidence_chip: 'E32' },
    ],
    cost_of_delay_4w: 640000,
    members_affected: 412,
    rules_triggered: ['R06', 'R07', 'R08', 'R09', 'R10'],
    primary_indicator:
      'Indicators consistent with 6-entity shared banking ring, reciprocal PT referrals, and same-day toxicology surge',
    network_complexity_score: 98,
    requires_network_specialist: true,
    sla_status: 'on_track',
    sla_due_date: '2024-09-25T17:00:00Z',
    assigned_to: null,
    _sample: true,
  },
  {
    case_id: 'CASE-2024-0088',
    title: 'Concurrent Multi-Site Surgical Procedures (Chen)',
    name: 'Dr. Sarah Chen',
    subtitle: 'Dermatology · single provider',
    focal_provider_id: 'P0088',
    focal_provider_name: 'Dr. Sarah Chen, MD',
    specialty: 'dermatology',
    priority_score: 86,
    risk_index: 84,
    severity: 'HIGH',
    confidence: 'High',
    est_dollars: 185000.0,
    est_overpay: 42000.0,
    exposure_low: 900000,
    exposure_high: 3800000,
    effort_hours: 9,
    pool: 'general',
    baseline_rank: 12,
    top_reasons: [
      { text: 'Simultaneous procedural billing across distant facility locations', evidence_chip: 'E6' },
      { text: 'Outlier biopsy utilization exceeding specialty 99th percentile', evidence_chip: 'E8' },
    ],
    cost_of_delay_4w: 240000,
    members_affected: 188,
    rules_triggered: ['R06', 'R08'],
    primary_indicator:
      'Pattern similarity indicating simultaneous procedural billing across distant facility locations',
    network_complexity_score: 22,
    requires_network_specialist: false,
    sla_status: 'warning',
    sla_due_date: '2024-09-28T17:00:00Z',
    assigned_to: 'SIU Officer #108',
    _sample: true,
  },
  {
    case_id: 'CASE-2024-0115',
    title: 'Level 5 E&M Rapid Billing Surge (House)',
    name: 'Dr. Gregory House',
    subtitle: 'Internal medicine · single provider',
    focal_provider_id: 'P0115',
    focal_provider_name: 'Dr. Gregory House, MD',
    specialty: 'internal_medicine',
    priority_score: 78,
    risk_index: 76,
    severity: 'HIGH',
    confidence: 'Medium',
    est_dollars: 145000.0,
    est_overpay: 38500.0,
    exposure_low: 800000,
    exposure_high: 3000000,
    effort_hours: 9,
    pool: 'general',
    baseline_rank: 21,
    top_reasons: [
      { text: 'Sudden shift to 64% Level 5 complex visit billing vs specialty peer median of 12%', evidence_chip: 'E10' },
    ],
    cost_of_delay_4w: 190000,
    members_affected: 95,
    rules_triggered: ['R10'],
    primary_indicator:
      'Sudden shift to 64% Level 5 complex visit billing vs specialty peer median of 12%',
    network_complexity_score: 15,
    requires_network_specialist: false,
    sla_status: 'on_track',
    sla_due_date: '2024-10-02T17:00:00Z',
    assigned_to: 'SIU Officer #104',
    _sample: true,
  },
  {
    case_id: 'CASE-2024-0192',
    title: 'High-Concentration Diagnostic Imaging Loop (Croft)',
    name: 'Dr. Diana Croft',
    subtitle: 'Radiology · 6 providers',
    focal_provider_id: 'P0045',
    focal_provider_name: 'Dr. Diana Croft, MD',
    specialty: 'radiology',
    priority_score: 74,
    risk_index: 72,
    severity: 'MEDIUM',
    confidence: 'Medium',
    est_dollars: 112000.0,
    est_overpay: 28400.0,
    exposure_low: 600000,
    exposure_high: 2200000,
    effort_hours: 14,
    pool: 'network',
    baseline_rank: 44,
    top_reasons: [
      { text: '89% referral capture rate from affiliated orthopedic practices under common management', evidence_chip: 'E7' },
    ],
    cost_of_delay_4w: 160000,
    members_affected: 124,
    rules_triggered: ['R07', 'R09'],
    primary_indicator:
      '89% referral capture rate from affiliated orthopedic practices under common management',
    network_complexity_score: 82,
    requires_network_specialist: true,
    sla_status: 'on_track',
    sla_due_date: '2024-10-05T17:00:00Z',
    assigned_to: null,
    _sample: true,
  },
  {
    case_id: 'CASE-2024-0230',
    title: 'Dispersed Rural Patient Catchment Anomaly (Sterling)',
    name: 'Dr. Arthur Sterling',
    subtitle: 'Chiropractic · single provider',
    focal_provider_id: 'P0044',
    focal_provider_name: 'Dr. Arthur Sterling, DC',
    specialty: 'chiropractic',
    priority_score: 69,
    risk_index: 68,
    severity: 'MEDIUM',
    confidence: 'Medium',
    est_dollars: 78000.0,
    est_overpay: 19500.0,
    exposure_low: 400000,
    exposure_high: 1500000,
    effort_hours: 8,
    pool: 'general',
    baseline_rank: 52,
    top_reasons: [
      { text: 'Over 40% of patient panel traveling >120 miles for weekly routine maintenance therapy', evidence_chip: 'E8' },
    ],
    cost_of_delay_4w: 95000,
    members_affected: 68,
    rules_triggered: ['R08'],
    primary_indicator:
      'Over 40% of patient panel traveling >120 miles for weekly routine maintenance therapy',
    network_complexity_score: 35,
    requires_network_specialist: false,
    sla_status: 'on_track',
    sla_due_date: '2024-10-10T17:00:00Z',
    assigned_to: null,
    _sample: true,
  },
];

/**
 * Deterministically computes queue ranking based on capacity constraints and filter parameters.
 */
export function calculateMockQueue(params: QueueQueryParams = {}): QueueResponse {
  const generalHours = params.general_hours ?? 40;
  const networkHours = params.network_hours ?? 20;
  const horizon = params.horizon ?? '30d';
  const sort = params.sort ?? 'priority';

  // Horizon multiplier for long-tail exposure
  const horizonMultiplier = horizon === '90d' ? 1.15 : horizon === '60d' ? 1.08 : 1.0;

  // Network capacity ratio: network_hours / (network_hours + general_hours)
  const totalCapacity = Math.max(1, generalHours + networkHours);
  const networkCapacityRatio = networkHours / totalCapacity;

  // Compute dynamic priority for each item
  let items: QueueItem[] = RAW_MOCK_QUEUE_ITEMS.map((item) => {
    let dynamicPriority: number;

    if (item.requires_network_specialist) {
      // When network specialist capacity is available, complex multi-entity networks scale priority
      const networkBoost = (item.network_complexity_score / 100) * (networkCapacityRatio * 45);
      const exposureWeight = Math.min(12, (item.est_dollars / 500000) * 12);
      const baseScore = item.risk_index * 0.72 + networkBoost + exposureWeight;
      dynamicPriority = Math.min(100, Math.round(baseScore * horizonMultiplier));
    } else {
      // Generalist cases are prioritized by generalist capacity availability and risk
      const generalCapacityRatio = generalHours / totalCapacity;
      const generalBoost = generalCapacityRatio * 14;
      const exposureWeight = Math.min(10, (item.est_dollars / 500000) * 10);
      const baseScore = item.risk_index * 0.72 + generalBoost + exposureWeight;
      dynamicPriority = Math.min(100, Math.round(baseScore * horizonMultiplier));
    }

    return {
      ...item,
      priority_score: dynamicPriority,
    };
  });

  // Apply filters
  if (params.severity) {
    items = items.filter((item) => item.severity.toLowerCase() === params.severity?.toLowerCase());
  }
  if (params.rule_id) {
    items = items.filter((item) => item.rules_triggered.includes(params.rule_id!));
  }
  if (params.search) {
    const q = params.search.toLowerCase();
    items = items.filter(
      (item) =>
        item.case_id.toLowerCase().includes(q) ||
        item.title.toLowerCase().includes(q) ||
        (item.name && item.name.toLowerCase().includes(q)) ||
        item.focal_provider_name.toLowerCase().includes(q) ||
        item.focal_provider_id.toLowerCase().includes(q),
    );
  }

  // Apply sorting
  items = [...items].sort((a, b) => {
    switch (sort) {
      case 'risk':
        return b.risk_index - a.risk_index;
      case 'exposure':
        return b.exposure_high - a.exposure_high;
      case 'network_complexity':
        return b.network_complexity_score - a.network_complexity_score;
      case 'sla':
        return new Date(a.sla_due_date).getTime() - new Date(b.sla_due_date).getTime();
      case 'priority':
      default:
        return b.priority_score - a.priority_score;
    }
  });

  // Compute capacity fill: assign slots (addressable vs deferred) based on available hours
  let accumulatedGeneral = 0;
  let accumulatedNetwork = 0;
  let addressableCount = 0;

  items = items.map((item) => {
    let fits = false;
    if (item.pool === 'network') {
      if (accumulatedNetwork + item.effort_hours <= networkHours || accumulatedNetwork + accumulatedGeneral + item.effort_hours <= totalCapacity) {
        fits = true;
        accumulatedNetwork += item.effort_hours;
      }
    } else {
      if (accumulatedGeneral + item.effort_hours <= generalHours || accumulatedNetwork + accumulatedGeneral + item.effort_hours <= totalCapacity) {
        fits = true;
        accumulatedGeneral += item.effort_hours;
      }
    }

    if (fits) {
      addressableCount++;
      return { ...item, slot: 'addressable' as const };
    } else {
      return { ...item, slot: 'deferred' as const };
    }
  });

  return {
    items,
    total_count: items.length,
    capacity_settings: {
      general_hours: generalHours,
      network_hours: networkHours,
      horizon,
      sort,
    },
    capacity_summary: {
      general_hours: generalHours,
      network_hours: networkHours,
      total_hours: totalCapacity,
      estimated_cases_addressable: Math.max(1, addressableCount),
      network_backlog_hours: Math.max(0, 80 - networkHours * 2),
    },
  };
}

