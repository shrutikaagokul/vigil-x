import React from 'react';

interface MetricComparisonRow {
  readonly metric: string;
  readonly rulesOnly: string;
  readonly nexus: string;
  readonly delta: string;
  readonly note: string;
}

const COMPARISON_ROWS: readonly MetricComparisonRow[] = [
  {
    metric: 'Precision @ Top 10 Triage',
    rulesOnly: '30.0% (3 / 10)',
    nexus: '40.0% (4 / 10)',
    delta: '+33.3% relative (+10.0% abs)',
    note: 'Initial investigator caseload captures 33% more true targets',
  },
  {
    metric: 'Precision @ Top 25 Triage',
    rulesOnly: '12.0% (3 / 25)',
    nexus: '16.0% (4 / 25)',
    delta: '+33.3% relative (+4.0% abs)',
    note: 'Sustained precision across weekly investigation batches',
  },
  {
    metric: 'Precision @ Top 50 Triage',
    rulesOnly: '6.0% (3 / 50)',
    nexus: '10.0% (5 / 50)',
    delta: '+66.7% relative (+4.0% abs)',
    note: '67% higher hit rate across monthly team capacity',
  },
  {
    metric: 'Recall @ Top 100 Triage',
    rulesOnly: '21.1% (4 / 19 targets)',
    nexus: '36.8% (7 / 19 targets)',
    delta: '+75.0% relative (+15.7% abs)',
    note: 'Nexus captures nearly double the ground-truth targets',
  },
  {
    metric: 'Claim-Level PR-AUC',
    rulesOnly: '0.0182 (Amount baseline)',
    nexus: '0.7025 (LightGBM OOF)',
    delta: '+38.6× improvement',
    note: 'Out-of-fold cross-validated claim anomaly discrimination',
  },
  {
    metric: '6-Provider Ring Prioritization',
    rulesOnly: 'Rank #38',
    nexus: 'Rank #1',
    delta: '+37 rank promotion',
    note: 'Elevates coordinated ring ahead of isolated volume alerts',
  },
];

export const EvaluationComparisonCenterpiece: React.FC = () => {
  return (
    <div
      data-testid="eval-comparison-centerpiece"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-4"
    >
      <div className="border-b border-[#D3E0D6] pb-3">
        <div className="flex items-center gap-2">
          <h2 className="font-serif text-[1.375rem] font-semibold text-[#0B1A12]">
            Rules-Only Baseline vs. Nexus Prioritization
          </h2>
          <span className="px-2 py-0.5 text-[0.75rem] font-mono bg-[#E3EFE5] text-[#1B3A29] border border-[#D3E0D6] rounded-[2px]">
            Benchmark Comparison
          </span>
        </div>
        <p className="text-[0.875rem] text-[#4F5F55] mt-1">
          Direct comparative evaluation between static rule alert thresholds and Nexus multi-signal unified risk scoring across controlled ground truth benchmarks.
        </p>
      </div>

      {/* Structured Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[0.875rem] border-collapse">
          <thead>
            <tr className="border-b-2 border-[#12291C] text-[0.8125rem] font-medium text-[#4F5F55]">
              <th className="py-2.5 pr-4">Evaluation Metric / Triage Cutoff</th>
              <th className="py-2.5 px-4">Rules-Only (Baseline)</th>
              <th className="py-2.5 px-4">Nexus (Unified Risk)</th>
              <th className="py-2.5 px-4 font-semibold text-[#1B3A29]">Observed Lift (Delta)</th>
              <th className="py-2.5 pl-4">Investigation Impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D3E0D6]">
            {COMPARISON_ROWS.map((row, idx) => (
              <tr
                key={idx}
                className={`hover:bg-[#F3F8F4] transition-colors ${
                  idx === 0 ? 'bg-[#E3EFE5]/30 font-medium' : ''
                }`}
              >
                <td className="py-3 pr-4 font-medium text-[#0B1A12]">
                  {row.metric}
                </td>
                <td className="py-3 px-4 font-mono text-[#4F5F55] tabular-nums">
                  {row.rulesOnly}
                </td>
                <td className="py-3 px-4 font-mono font-semibold text-[#1B3A29] tabular-nums">
                  {row.nexus}
                </td>
                <td className="py-3 px-4 font-semibold text-[#2A5A3F] tabular-nums">
                  {row.delta}
                </td>
                <td className="py-3 pl-4 text-[#4F5F55] text-[0.8125rem]">
                  {row.note}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
