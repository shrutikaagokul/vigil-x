import React from 'react';
import { Link } from 'react-router-dom';

interface RuleItem {
  id: string;
  name: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  alertCount: number;
  description: string;
}

const RULES_DATA: RuleItem[] = [
  { id: 'R01', name: 'Duplicate Billing', category: 'Utilization', severity: 'HIGH', alertCount: 4, description: 'Identical claim items submitted within 24h window' },
  { id: 'R02', name: 'Upcoding Severity Inflation', category: 'Utilization', severity: 'HIGH', alertCount: 3, description: 'Disproportionate 99215 coding vs specialty peer norms' },
  { id: 'R03', name: 'Unbundled Procedure Codes', category: 'Utilization', severity: 'MEDIUM', alertCount: 3, description: 'Fragmented NCCI edit pairs billed on same encounter' },
  { id: 'R04', name: 'Phantom Services & Inactive Patients', category: 'Utilization', severity: 'CRITICAL', alertCount: 2, description: 'Services billed for deceased or inactive members' },
  { id: 'R05', name: 'Excessive Volume & Daily Caps', category: 'Utilization', severity: 'MEDIUM', alertCount: 1, description: 'Billed face-time exceeding physical 24-hour limit' },
  { id: 'R06', name: 'Impossible Transit Velocity', category: 'Behavioral', severity: 'CRITICAL', alertCount: 28, description: 'Encounters across distant clinics (>100 mph speed)' },
  { id: 'R07', name: 'Reciprocal Referral Anomaly', category: 'Network', severity: 'HIGH', alertCount: 34, description: 'Circular referral loops between collaborating providers' },
  { id: 'R08', name: 'Geographic Outlier Surges', category: 'Behavioral', severity: 'MEDIUM', alertCount: 22, description: 'Patients traveling >150 miles for routine primary care' },
  { id: 'R09', name: 'Shared Identity & Collusion Rings', category: 'Network', severity: 'CRITICAL', alertCount: 46, description: 'Providers linked via shared banking and tax hashes' },
  { id: 'R10', name: 'Billing Volume Burst & Spikes', category: 'Temporal', severity: 'HIGH', alertCount: 33, description: 'Sudden exponential claim volume surges (>3.0 sigma)' },
];

function getSeverityBadge(severity: string) {
  switch (severity) {
    case 'CRITICAL':
      return 'bg-[#FEE2E2] text-[#B91C1C] border-[#FCA5A5]';
    case 'HIGH':
      return 'bg-[#FEF3C7] text-[#B45309] border-[#FCD34D]';
    default:
      return 'bg-[#E0F2FE] text-[#0369A1] border-[#BAE6FD]';
  }
}

export const DashboardRuleActivity: React.FC = () => {
  return (
    <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 space-y-6 shadow-xs">
      <div className="border-b border-[#E0E8DF] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-serif text-2xl font-bold text-[#183B2A] tracking-tight">
            Rule Activity (R01–R10)
          </h2>
          <p className="text-base text-[#68766B] mt-1">
            Active alerts and operational status across clinical, behavioral, network, and temporal detection rules.
          </p>
        </div>
        <Link
          to="/rules"
          className="text-base font-semibold text-[#285239] hover:text-[#183B2A] transition-colors shrink-0"
        >
          Explore Rule Engine
        </Link>
      </div>

      {/* Wide, Highly Readable R01–R10 Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-base">
          <thead>
            <tr className="border-b border-[#E0E8DF] bg-[#F5F8F4] text-xs font-mono uppercase text-[#68766B]">
              <th className="py-3.5 px-5 font-semibold">Rule ID</th>
              <th className="py-3.5 px-5 font-semibold">Rule Name</th>
              <th className="py-3.5 px-5 font-semibold">Category</th>
              <th className="py-3.5 px-5 font-semibold">Severity</th>
              <th className="py-3.5 px-5 font-semibold text-right">Active Alerts</th>
              <th className="py-3.5 px-5 font-semibold">Detection Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E0E8DF] text-[#24352A]">
            {RULES_DATA.map((rule) => (
              <tr key={rule.id} className="hover:bg-[#F5F8F4] transition-colors">
                <td className="py-4 px-5 font-mono font-bold text-[#183B2A]">
                  <span className="bg-white px-2.5 py-1 rounded border border-[#E0E8DF]">
                    {rule.id}
                  </span>
                </td>
                <td className="py-4 px-5 font-semibold text-[#183B2A]">
                  {rule.name}
                </td>
                <td className="py-4 px-5 font-mono text-sm text-[#68766B]">
                  {rule.category}
                </td>
                <td className="py-4 px-5">
                  <span className={`text-xs font-mono px-2.5 py-1 rounded border font-semibold ${getSeverityBadge(rule.severity)}`}>
                    {rule.severity}
                  </span>
                </td>
                <td className="py-4 px-5 text-right font-mono font-bold text-[#183B2A] tabular-nums">
                  {rule.alertCount} alerts
                </td>
                <td className="py-4 px-5 text-sm text-[#68766B]">
                  {rule.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
