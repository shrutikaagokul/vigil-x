/**
 * Mock Risk Intelligence fixtures.
 */
import { RiskResponse } from '@/types/api';

export const MOCK_RISK_RESPONSES: Record<string, RiskResponse> = {
  P0042: {
    entity_id: 'P0042',
    entity_type: 'provider',
    risk_index: 94,
    horizon: '30d',
    risk_tier: 'Critical',
    primary_factors: [
      {
        name: 'Shared Financial Routing Cluster',
        rule_id: 'R09',
        weight: 0.35,
        score: 98,
        plain_text: 'Exact bank account hash matches 4 independent billing entities.',
      },
      {
        name: 'Reciprocal Referral Loop',
        rule_id: 'R07',
        weight: 0.25,
        score: 92,
        plain_text: '82.4% physical therapy referrals directed to co-banked entity P0043.',
      },
      {
        name: 'Impossible Physical Travel',
        rule_id: 'R06',
        weight: 0.2,
        score: 95,
        plain_text: '78.4 mph required transit speed between consecutive service sites.',
      },
      {
        name: 'Billing Volume Surge',
        rule_id: 'R10',
        weight: 0.2,
        score: 88,
        plain_text: '4.2x weekly billing surge over trailing 12-week baseline median.',
      },
    ],
    trend: 'increasing',
    peer_group_percentile: 99.4,
    calculated_at: '2024-09-18T14:00:00Z',
  },
  P0088: {
    entity_id: 'P0088',
    entity_type: 'provider',
    risk_index: 84,
    horizon: '30d',
    risk_tier: 'High',
    primary_factors: [
      {
        name: 'Overlapping Service Times',
        rule_id: 'R06',
        weight: 0.55,
        score: 90,
        plain_text: 'Simultaneous surgical procedures billed across distinct facilities.',
      },
      {
        name: 'Multi-County Patient Distribution',
        rule_id: 'R08',
        weight: 0.45,
        score: 78,
        plain_text: 'Patients traveling >90 miles for routine dermatological excision.',
      },
    ],
    trend: 'stable',
    peer_group_percentile: 95.3,
    calculated_at: '2024-09-18T14:00:00Z',
  },
};
