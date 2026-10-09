import React, { useState } from 'react';
import { Link } from 'react-router-dom';

interface RuleDefinition {
  id: string;
  name: string;
  category: 'Utilization & Billing' | 'Behavioral & Timing' | 'Entity & Network' | 'Temporal & Velocity';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  summary: string;
  howItWorks: string;
  whyItMatters: string;
  benignExplanations: string;
  alertCount: number;
}

const RULES_CATALOG: RuleDefinition[] = [
  {
    id: 'R01',
    name: 'Duplicate Billing',
    category: 'Utilization & Billing',
    severity: 'HIGH',
    summary: 'Identifies identical or near-identical claim submissions for the same patient, provider, and service date.',
    howItWorks: 'Scans for overlapping line items with identical CPT codes, modifiers, and service dates billed within a 24-hour window.',
    whyItMatters: 'Accidental or intentional resubmissions drain insurance reserves and result in double payments.',
    benignExplanations: 'Legitimate repeat procedures on the same date (e.g. bilateral treatments without modifier -50, or sequential lab draws).',
    alertCount: 4,
  },
  {
    id: 'R02',
    name: 'Upcoding & Severity Inflation',
    category: 'Utilization & Billing',
    severity: 'HIGH',
    summary: 'Detects systematic billing of highest-level evaluation & management (E&M) codes without medical complexity.',
    howItWorks: 'Compares a provider’s ratio of high-complexity codes (e.g. 99215 vs 99213) against regional specialty peer distributions (>3 standard deviations).',
    whyItMatters: 'Artificially inflates reimbursement rates by 40–120% per encounter.',
    benignExplanations: 'Specialized tertiary clinics catering exclusively to severe, complex chronic disease cohorts.',
    alertCount: 3,
  },
  {
    id: 'R03',
    name: 'Unbundling of Comprehensive Codes',
    category: 'Utilization & Billing',
    severity: 'MEDIUM',
    summary: 'Flags component services billed separately when a single comprehensive bundled CPT code exists.',
    howItWorks: 'Evaluates National Correct Coding Initiative (NCCI) edit pairs billed on the same encounter date by the same billing entity.',
    whyItMatters: 'Unbundling fragments procedures to bypass single-payment limits, generating illegitimate fee totals.',
    benignExplanations: 'Distinct procedural services performed during separate operative sessions on the same date (proper modifier -59 usage).',
    alertCount: 3,
  },
  {
    id: 'R04',
    name: 'Phantom Services & Dead Beneficiaries',
    category: 'Utilization & Billing',
    severity: 'CRITICAL',
    summary: 'Flags services billed for patients who were deceased, inactive, or not present during the service window.',
    howItWorks: 'Cross-references service dates against member enrollment status, date of death registries, and facility admission logs.',
    whyItMatters: 'Direct indicator of fabricated billing where no medical service occurred.',
    benignExplanations: 'Data entry clerical errors in dates of death or mistyped member identification numbers.',
    alertCount: 2,
  },
  {
    id: 'R05',
    name: 'Excessive Utilization & Daily Caps',
    category: 'Utilization & Billing',
    severity: 'MEDIUM',
    summary: 'Detects encounters exceeding physically plausible volume thresholds for a single human clinician.',
    howItWorks: 'Calculates cumulative clinical face-time per provider per calendar day based on standard work RVU time estimates.',
    whyItMatters: 'Providers billing >24 hours of clinical services in a single day indicate automated billing mills.',
    benignExplanations: 'Group practices billing under a single supervising physician’s NPI before proper incident-to credentialing.',
    alertCount: 1,
  },
  {
    id: 'R06',
    name: 'Impossible Timing & Transit Velocity',
    category: 'Behavioral & Timing',
    severity: 'CRITICAL',
    summary: 'Detects the same patient or provider appearing in geographically distant clinics within physically impossible transit times.',
    howItWorks: 'Calculates Haversine distance between clinic facilities and required transit velocity (>100 mph) between timestamped claims.',
    whyItMatters: 'Definitive indicator of shared credential theft, ghost clinics, or remote automated claims injection.',
    benignExplanations: 'Telehealth virtual appointments billed with physical clinic place-of-service (POS 11) codes.',
    alertCount: 28,
  },
  {
    id: 'R07',
    name: 'Reciprocal Referral Loop Anomaly',
    category: 'Entity & Network',
    severity: 'HIGH',
    summary: 'Uncovers circular or highly concentrated patient referral rings between collaborating providers and diagnostic labs.',
    howItWorks: 'Constructs directed referral graphs and computes clustering coefficients, reciprocal edge densities, and patient recirculation rates.',
    whyItMatters: 'Violates Anti-Kickback and Stark regulations; creates artificial demand for unnecessary diagnostics.',
    benignExplanations: 'Integrated care teams and specialized multidisciplinary oncology/cardiology care pathways.',
    alertCount: 34,
  },
  {
    id: 'R08',
    name: 'Geographic Outlier & Out-of-Area Surges',
    category: 'Behavioral & Timing',
    severity: 'MEDIUM',
    summary: 'Identifies sudden surges of patients traveling unusually long distances (>150 miles) for routine primary care.',
    howItWorks: 'Evaluates patient residential zip codes relative to provider practice location against regional baseline travel radiuses.',
    whyItMatters: 'Hallmark of patient recruitment schemes, pill mills, or stolen patient ID batches.',
    benignExplanations: 'Rare specialty regional centers of excellence or destination telemedicine practices.',
    alertCount: 22,
  },
  {
    id: 'R09',
    name: 'Shared Identity & Collusion Rings',
    category: 'Entity & Network',
    severity: 'CRITICAL',
    summary: 'Links seemingly independent providers through shared bank routing numbers, tax IDs, phone numbers, or addresses.',
    howItWorks: 'Deterministic and fuzzy entity resolution on billing hashes, identifying co-controlled enterprise rings.',
    whyItMatters: 'Exposes syndicated healthcare fraud rings operating multiple shell corporations to conceal volume.',
    benignExplanations: 'Management Services Organizations (MSOs) providing legitimate centralized billing for independent clinics.',
    alertCount: 46,
  },
  {
    id: 'R10',
    name: 'Billing Volume Burst & Trajectory Spike',
    category: 'Temporal & Velocity',
    severity: 'HIGH',
    summary: 'Flags sudden exponential spikes in claim volume or dollar totals compared to historical baseline trajectories.',
    howItWorks: 'Applies cumulative sum (CUSUM) and rolling Z-score anomaly detectors across weekly claim volume curves (>3.0 sigma).',
    whyItMatters: '"Bust-out" fraud patterns where new entities bill aggressively for 60–90 days before abandoning credentials.',
    benignExplanations: 'Practice expansion, seasonal flu clinics, pandemic response pop-ups, or acquisition of new patient rosters.',
    alertCount: 33,
  },
];

export const RuleEnginePage: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  const categories = ['ALL', 'Utilization & Billing', 'Behavioral & Timing', 'Entity & Network', 'Temporal & Velocity'];

  const filteredRules = selectedCategory === 'ALL'
    ? RULES_CATALOG
    : RULES_CATALOG.filter(r => r.category === selectedCategory);

  const totalAlerts = RULES_CATALOG.reduce((acc, r) => acc + r.alertCount, 0);

  return (
    <div className="space-y-8 pb-16">
      {/* Header */}
      <div className="bg-white border border-[#E0E8DF] rounded-xl p-8 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-xs font-mono uppercase tracking-wider text-[#285239] font-bold bg-[#E8F2E8] px-3 py-1 rounded border border-[#B8D2B8]">
              Detection Intelligence Engine
            </span>
            <span className="text-xs text-[#68766B] font-mono">10 Specialized Rules</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-bold text-[#183B2A] tracking-tight">
            FWA Rule Engine (R01–R10)
          </h1>
          <p className="text-base text-[#68766B] mt-1.5 max-w-4xl leading-relaxed">
            Deterministic and behavioral intelligence detection rules covering clinical coding anomalies, impossible travel, collusion rings, and volume bursts.
          </p>
        </div>

        {/* Global Summary Badge */}
        <div className="flex items-center gap-4 shrink-0">
          <div className="p-4 bg-[#F5F8F4] border border-[#E0E8DF] rounded-lg text-right">
            <div className="text-xs text-[#68766B] uppercase font-mono font-semibold">Active Rule Alerts</div>
            <div className="font-serif text-3xl font-bold text-[#B45309] tabular-nums mt-0.5">
              {totalAlerts} Alerts
            </div>
          </div>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center gap-3 overflow-x-auto pb-1">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setSelectedCategory(cat)}
            className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-colors border shadow-xs ${
              selectedCategory === cat
                ? 'bg-[#477A58] text-white border-[#477A58]'
                : 'bg-white text-[#68766B] border-[#E0E8DF] hover:bg-[#F5F8F4] hover:text-[#183B2A]'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {filteredRules.map((rule) => {
          const isCritical = rule.severity === 'CRITICAL';
          const isHigh = rule.severity === 'HIGH';

          return (
            <div
              key={rule.id}
              className="bg-white border border-[#E0E8DF] hover:border-[#B8D2B8] rounded-xl p-8 space-y-5 shadow-xs transition-colors flex flex-col justify-between"
            >
              <div>
                {/* Card Header */}
                <div className="flex items-start justify-between gap-3 border-b border-[#E0E8DF] pb-4">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-base font-bold bg-[#F5F8F4] px-3 py-1 rounded border border-[#E0E8DF] text-[#183B2A]">
                      {rule.id}
                    </span>
                    <div>
                      <h2 className="text-xl font-bold text-[#183B2A]">
                        {rule.name}
                      </h2>
                      <span className="text-xs font-mono text-[#68766B]">
                        {rule.category}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <span
                      className={`text-xs font-mono px-2.5 py-1 rounded border font-semibold ${
                        isCritical
                          ? 'bg-[#FEE2E2] border-[#FCA5A5] text-[#B91C1C]'
                          : isHigh
                          ? 'bg-[#FEF3C7] border-[#FCD34D] text-[#B45309]'
                          : 'bg-[#E0F2FE] border-[#BAE6FD] text-[#0369A1]'
                      }`}
                    >
                      {rule.severity}
                    </span>
                    <span className="font-mono text-sm font-bold text-[#183B2A] bg-[#F5F8F4] px-2.5 py-1 rounded border border-[#E0E8DF]">
                      {rule.alertCount} alerts
                    </span>
                  </div>
                </div>

                {/* Explanation Content */}
                <div className="mt-4 space-y-3 text-base">
                  <p className="text-[#24352A] font-medium leading-relaxed">
                    {rule.summary}
                  </p>

                  <div className="p-4 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] space-y-1">
                    <div className="text-xs font-mono text-[#285239] uppercase font-bold">
                      Detection Logic:
                    </div>
                    <p className="text-[#68766B] leading-relaxed text-sm">
                      {rule.howItWorks}
                    </p>
                  </div>

                  <div className="p-4 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] space-y-1">
                    <div className="text-xs font-mono text-[#B45309] uppercase font-bold">
                      Investigative Impact:
                    </div>
                    <p className="text-[#68766B] leading-relaxed text-sm">
                      {rule.whyItMatters}
                    </p>
                  </div>

                  <div className="p-4 bg-[#F5F8F4] rounded-lg border border-[#E0E8DF] space-y-1">
                    <div className="text-xs font-mono text-[#68766B] uppercase font-bold">
                      Benign / False Positive Context:
                    </div>
                    <p className="text-[#68766B] leading-relaxed text-sm">
                      {rule.benignExplanations}
                    </p>
                  </div>
                </div>
              </div>

              {/* Action Footer */}
              <div className="pt-4 border-t border-[#E0E8DF] flex items-center justify-between text-sm">
                <span className="text-xs text-[#68766B] font-mono">
                  Engine Version 2.4 | Calibrated
                </span>
                <Link
                  to="/queue"
                  className="text-base font-semibold text-[#285239] hover:text-[#183B2A] transition-colors"
                >
                  View in SIU Queue
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
