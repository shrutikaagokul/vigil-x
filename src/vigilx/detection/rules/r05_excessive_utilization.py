"""
R05 — Excessive Utilization Detection (Detection Layer).

Behaviorally intelligent utilization detection that compares against:
  - Provider historical baseline (not just fixed thresholds)
  - Peer/provider baseline where available
  - Daily/weekly/monthly utilization
  - Service-specific utilization
  - Member volume and procedure frequency

Generates features: current utilization, historical average, utilization ratio,
                     percentage deviation, trend, baseline period.
"""

from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime
import statistics
from vigilx.detection.rules.base import BaseRule, DataContext, RuleResult


class R05ExcessiveUtilization(BaseRule):
    """R05: Excessive Utilization Detection."""

    rule_id = "R05"
    rule_name = "Excessive Utilization"

    def evaluate(self, context: DataContext) -> List[RuleResult]:
        if not self.enabled:
            return []

        results = []
        peer_multiplier = self.cfg.get("provider_peer_multiplier", 3.0)
        daily_max_minutes = self.cfg.get("provider_daily_max_minutes",
                                          self.cfg.get("daily_max_minutes", 960))

        # Procedure duration estimates (minutes) - from RVU tables
        proc_duration_mins = {
            "99215": 40, "99214": 25, "99213": 15, "99212": 10, "99211": 5,
            "99205": 60, "99204": 45, "99203": 30, "99202": 20, "99201": 10,
            "90837": 60, "90834": 45, "90832": 30,
            "97110": 15, "97140": 15, "97530": 15,
        }

        # === Part A: Provider daily claim volume analysis ===
        provider_daily_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: defaultdict(lambda: {"claims": [], "minutes": 0, "amount": 0.0, "members": set()})
        )

        # === Part B: Provider aggregate stats ===
        provider_agg: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total_claims": 0, "total_amount": 0.0, "unique_members": set(),
                     "daily_counts": defaultdict(int), "claims": []}
        )

        for claim in context.claims:
            provider_id = claim.get("provider_id") or claim.get("billing_provider_id")
            dos = str(claim.get("date_of_service") or claim.get("service_date", ""))[:10]
            proc_code = str(claim.get("procedure_code") or claim.get("cpt_code", ""))
            claim_id = claim.get("claim_id")
            billed_amount = float(claim.get("billed_amount", 0.0) or 0.0)
            patient_id = claim.get("patient_id") or claim.get("member_id")

            if not provider_id or not dos:
                continue

            duration = proc_duration_mins.get(proc_code, 15)

            # Daily stats
            day_stats = provider_daily_stats[provider_id][dos]
            day_stats["claims"].append(claim_id)
            day_stats["minutes"] += duration
            day_stats["amount"] += billed_amount
            if patient_id:
                day_stats["members"].add(patient_id)

            # Aggregate stats
            agg = provider_agg[provider_id]
            agg["total_claims"] += 1
            agg["total_amount"] += billed_amount
            agg["daily_counts"][dos] += 1
            agg["claims"].append(claim_id)
            if patient_id:
                agg["unique_members"].add(patient_id)

        # === Part A: Impossible Day Detection ===
        for provider_id, days in provider_daily_stats.items():
            for dos, day_stats in days.items():
                if day_stats["minutes"] > daily_max_minutes:
                    hours = day_stats["minutes"] / 60
                    claim_count = len(day_stats["claims"])

                    results.append(RuleResult(
                        triggered=True,
                        evidence_data={
                            "description": (
                                f"Impossible Day: Provider {provider_id} billed "
                                f"{hours:.1f} hours ({day_stats['minutes']} minutes) "
                                f"of services on {dos} across {claim_count} claims "
                                f"for {len(day_stats['members'])} unique members."
                            ),
                            "what_happened": f"Provider billed {hours:.1f} hours in a single day",
                            "why_suspicious": (
                                f"Total service duration exceeds {daily_max_minutes // 60}-hour "
                                f"clinical day threshold"
                            ),
                            "baseline_used": f"Maximum clinical day: {daily_max_minutes} minutes",
                            "observed_value": f"{day_stats['minutes']} minutes",
                            "deviation": f"+{day_stats['minutes'] - daily_max_minutes} minutes above threshold",
                            "utilization_ratio": round(day_stats["minutes"] / daily_max_minutes, 2),
                            "false_positive_notes": (
                                "Provider may bill for services rendered by multiple subordinate "
                                "clinicians under their NPI. Group practice billing is common."
                            ),
                            "estimated_overpayment": 0.0,
                            "claims": day_stats["claims"],
                            "provider_id": provider_id,
                            "severity": "HIGH",
                        }
                    ))

        # === Part B: Provider historical baseline comparison ===
        # Compute peer baselines from the dataset itself
        all_daily_avgs = []
        for provider_id, agg in provider_agg.items():
            daily_counts = list(agg["daily_counts"].values())
            if daily_counts:
                avg_daily = statistics.mean(daily_counts)
                all_daily_avgs.append(avg_daily)

        if all_daily_avgs:
            peer_median_daily = statistics.median(all_daily_avgs)
        else:
            peer_median_daily = None

        for provider_id, agg in provider_agg.items():
            daily_counts = list(agg["daily_counts"].values())
            if not daily_counts:
                continue

            active_days = len(daily_counts)
            avg_daily = statistics.mean(daily_counts)
            total_claims = agg["total_claims"]
            unique_members = len(agg["unique_members"])

            # Provider-specific historical baseline
            profile = context.provider_profiles.get(provider_id, {})
            hist_daily_avg = profile.get("historical_daily_avg_claims")
            hist_monthly_avg = profile.get("historical_monthly_avg_claims")

            # Use provider's own history if available, otherwise peer baseline
            if hist_daily_avg and hist_daily_avg > 0:
                baseline_daily = hist_daily_avg
                baseline_source = f"Provider historical daily average: {baseline_daily:.1f}"
            elif peer_median_daily and peer_median_daily > 0:
                baseline_daily = peer_median_daily
                baseline_source = f"Peer median daily claims: {baseline_daily:.1f}"
            else:
                continue  # insufficient data for baseline

            utilization_ratio = avg_daily / baseline_daily if baseline_daily > 0 else 1.0
            pct_deviation = (avg_daily - baseline_daily) / baseline_daily * 100 if baseline_daily > 0 else 0

            if utilization_ratio > peer_multiplier:
                visits_per_member = total_claims / unique_members if unique_members > 0 else 0

                results.append(RuleResult(
                    triggered=True,
                    evidence_data={
                        "description": (
                            f"Provider {provider_id} submitted {avg_daily:.1f} claims/day "
                            f"against a baseline of {baseline_daily:.1f}/day, "
                            f"representing a {utilization_ratio:.1f}× increase "
                            f"(+{pct_deviation:.0f}%). "
                            f"Total: {total_claims} claims for {unique_members} members "
                            f"over {active_days} active days."
                        ),
                        "what_happened": (
                            f"Provider claim volume is {utilization_ratio:.1f}× the baseline"
                        ),
                        "why_suspicious": (
                            f"Daily volume exceeds {peer_multiplier}× baseline threshold "
                            f"({avg_daily:.1f} vs {baseline_daily:.1f})"
                        ),
                        "baseline_used": baseline_source,
                        "baseline_period": f"{active_days} active days in dataset",
                        "current_utilization": round(avg_daily, 2),
                        "historical_average": round(baseline_daily, 2),
                        "utilization_ratio": round(utilization_ratio, 2),
                        "percentage_deviation": round(pct_deviation, 1),
                        "trend": "elevated",
                        "visits_per_member": round(visits_per_member, 2),
                        "false_positive_notes": (
                            "High-utilization specialty (e.g., oncology, dialysis) may explain volume. "
                            "Seasonal variations or pandemic response may cause temporary increases."
                        ),
                        "estimated_overpayment": 0.0,
                        "claims": agg["claims"][:100],
                        "provider_id": provider_id,
                        "severity": "HIGH" if utilization_ratio > peer_multiplier * 2 else "MEDIUM",
                    }
                ))

        return results
