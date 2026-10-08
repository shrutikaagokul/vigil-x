/**
 * Mock Dashboard Summary fixtures.
 */
import { DashboardSummary } from '@/types/api';

export const MOCK_SUMMARY: DashboardSummary = {
  total_exposure_dollars: 932000.0,
  estimated_recoverable_overpay: 255095.5,
  prioritized_cases_count: 5,
  active_alerts_count: 24,
  identified_rings_count: 3,
  capacity_utilization_pct: 78.5,
  top_risk_categories: [
    {
      category: 'Shared Banking & Entity Rings',
      rule_id: 'R09',
      count: 7,
      exposure_dollars: 412000.0,
    },
    {
      category: 'Reciprocal Referral Loops',
      rule_id: 'R07',
      count: 6,
      exposure_dollars: 215000.0,
    },
    {
      category: 'Impossible Timing & Velocity',
      rule_id: 'R06',
      count: 5,
      exposure_dollars: 185000.0,
    },
    {
      category: 'Burst & Surge Volume',
      rule_id: 'R10',
      count: 4,
      exposure_dollars: 120000.0,
    },
  ],
  metrics: [
    {
      label: 'Financial Exposure',
      value: '₹932,000',
      delta: '+14.2%',
      trend: 'up',
      subtitle: 'Trailing 90-day window',
    },
    {
      label: 'Prioritized Cases',
      value: 5,
      delta: '+2',
      trend: 'up',
      subtitle: '3 require network specialist',
    },
    {
      label: 'Active Risk Alerts',
      value: 24,
      delta: '-1',
      trend: 'neutral',
      subtitle: 'Across 14 providers',
    },
    {
      label: 'Recoverable Overpay Estimate',
      value: '₹255,096',
      delta: '+8.6%',
      trend: 'up',
      subtitle: 'Direct line-item overpayment',
    },
  ],
  last_updated: '2024-09-18T14:30:00Z',
};
