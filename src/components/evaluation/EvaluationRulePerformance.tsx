import React from 'react';
import { MetricScore } from '@/types/eval';

interface EvaluationRulePerformanceProps {
  readonly rulePerformance?: Readonly<Record<string, MetricScore>>;
}

function getRuleName(code: string): string {
  switch (code) {
    case 'R06':
      return 'Impossible Velocity & Transit';
    case 'R07':
      return 'Reciprocal Referral Loops';
    case 'R08':
      return 'Geographic Outlier Dispersal';
    case 'R09':
      return 'Shared Banking & Entity Rings';
    case 'R10':
      return 'Burst & Surge Volume';
    default:
      return 'Detection Rule';
  }
}

export const EvaluationRulePerformance: React.FC<EvaluationRulePerformanceProps> = ({
  rulePerformance = {},
}) => {
  const rules = Object.keys(rulePerformance);

  return (
    <div
      data-testid="eval-rule-performance"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-4"
    >
      <div className="border-b border-[#D3E0D6] pb-2">
        <h3 className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
          Detection Rule Precision & Recall
        </h3>
        <p className="text-[0.8125rem] text-[#4F5F55]">
          Performance metrics across individual rule detection components.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-[0.8125rem] border-collapse">
          <thead>
            <tr className="border-b border-[#D3E0D6] text-[0.75rem] font-medium text-[#4F5F55]">
              <th className="py-2 pr-3">Rule ID</th>
              <th className="py-2 px-3">Rule Name</th>
              <th className="py-2 px-3">Precision</th>
              <th className="py-2 px-3">Recall</th>
              <th className="py-2 px-3">F1 Score</th>
              <th className="py-2 pl-3">True Positives</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D3E0D6]">
            {rules.map((ruleId) => {
              const m = rulePerformance[ruleId];
              return (
                <tr key={ruleId} className="hover:bg-[#F3F8F4] transition-colors">
                  <td className="py-2.5 pr-3 font-mono font-bold text-[#1B3A29]">
                    {ruleId}
                  </td>
                  <td className="py-2.5 px-3 text-[#14201A] font-medium">
                    {getRuleName(ruleId)}
                  </td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-[#0B1A12]">
                    {(m.precision * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3 font-mono tabular-nums text-[#0B1A12]">
                    {(m.recall * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 px-3 font-mono font-semibold text-[#2A5A3F] tabular-nums">
                    {(m.f1_score * 100).toFixed(1)}%
                  </td>
                  <td className="py-2.5 pl-3 font-mono text-[#4F5F55] tabular-nums">
                    {m.true_positives.toLocaleString()}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
