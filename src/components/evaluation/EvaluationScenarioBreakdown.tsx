import React from 'react';
import { ScenarioResult } from '@/types/eval';

interface EvaluationScenarioBreakdownProps {
  readonly scenarios?: readonly ScenarioResult[];
}

export const EvaluationScenarioBreakdown: React.FC<EvaluationScenarioBreakdownProps> = ({
  scenarios = [],
}) => {
  return (
    <div
      data-testid="eval-scenario-breakdown"
      className="bg-white border border-[#D3E0D6] rounded-[3px] p-5 space-y-4"
    >
      <div className="border-b border-[#D3E0D6] pb-2">
        <h3 className="font-serif text-[1.125rem] font-semibold text-[#0B1A12]">
          Planted Fraud Scenario Recovery
        </h3>
        <p className="text-[0.8125rem] text-[#4F5F55]">
          Recovery rate and Jaccard cluster fidelity across injected multi-provider fraud topologies.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-[0.8125rem] border-collapse">
          <thead>
            <tr className="border-b border-[#D3E0D6] text-[0.75rem] font-medium text-[#4F5F55]">
              <th className="py-2 pr-3">Scenario</th>
              <th className="py-2 px-3">Description</th>
              <th className="py-2 px-3">Expected Rules</th>
              <th className="py-2 px-3">Providers Detected</th>
              <th className="py-2 px-3">Jaccard Recovery</th>
              <th className="py-2 pl-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#D3E0D6]">
            {scenarios.map((sc) => (
              <tr key={sc.scenario_id} className="hover:bg-[#F3F8F4] transition-colors">
                <td className="py-2.5 pr-3 font-mono font-bold text-[#1B3A29]">
                  {sc.scenario_id}
                </td>
                <td className="py-2.5 px-3 text-[#14201A] max-w-xs">
                  {sc.description}
                </td>
                <td className="py-2.5 px-3">
                  <div className="flex flex-wrap gap-1">
                    {sc.expected_rules.map((r) => (
                      <span
                        key={r}
                        className="px-1.5 py-0.2 bg-[#F3F8F4] border border-[#D3E0D6] font-mono text-[0.6875rem] text-[#4F5F55] rounded-[2px]"
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-2.5 px-3 font-mono tabular-nums text-[#0B1A12]">
                  {sc.providers_detected} / {sc.providers_count}
                </td>
                <td className="py-2.5 px-3 font-mono font-semibold text-[#2A5A3F] tabular-nums">
                  {sc.recovery_jaccard !== undefined ? `${(sc.recovery_jaccard * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="py-2.5 pl-3">
                  <span className="px-2 py-0.5 text-[0.6875rem] font-semibold bg-[#E3EFE5] text-[#1B3A29] rounded-[2px]">
                    Detected
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
