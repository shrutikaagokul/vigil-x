"""
R03 — Unbundling Detection.

Detects when a provider bills the comprehensive AND component CPT code
on the same member-date without a valid override modifier (59, 25, XE).

Provider-level escalation when unbundling rate exceeds peer p95.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from vigilx.features.provider_features import compute_provider_unbundling_rate
from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id
from vigilx.rules.base import BaseRule


class UnbundlingRule(BaseRule):
    """R03 — Unbundling Detection."""

    rule_id = "R03"

    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """Run unbundling detection."""
        if not self.enabled:
            return []

        claims = data.get("claims")
        bundling_pairs = data.get("bundling_pairs")
        if claims is None or claims.empty:
            return []
        if bundling_pairs is None or bundling_pairs.empty:
            return []

        cfg = self.cfg
        base_severity = Severity(cfg.get("base_severity", "MEDIUM"))
        escalated_severity = Severity(cfg.get("escalated_severity", "HIGH"))
        override_mods = set(cfg.get("allowed_override_modifiers", ["59", "25", "XE"]))
        rate_pct = cfg.get("provider_rate_percentile", 95)

        # Step 1: Find all member-provider-date groups with bundleable codes
        alerts = self._find_unbundled_claims(
            claims, bundling_pairs, override_mods, base_severity,
        )

        if not alerts:
            return []

        # Step 2: Compute provider unbundling rates for escalation
        prov_rates = compute_provider_unbundling_rate(
            claims, bundling_pairs, list(override_mods),
        )
        if not prov_rates.empty:
            p95_threshold = prov_rates["unbundling_rate"].quantile(rate_pct / 100.0)
            high_rate_providers = set(
                prov_rates[prov_rates["unbundling_rate"] > p95_threshold]["billing_provider_id"]
            )

            # Escalate alerts for high-rate providers
            for alert in alerts:
                if alert.entity_id in high_rate_providers or \
                   (alert.entity_id.isdigit() and int(alert.entity_id) in high_rate_providers):
                    alert.severity = escalated_severity
                    prov_row = prov_rates[
                        prov_rates["billing_provider_id"].astype(str) == alert.entity_id
                    ]
                    if not prov_row.empty:
                        rate = prov_row.iloc[0]["unbundling_rate"] * 100
                        alert.evidence.append(Evidence(
                            evidence_id=make_evidence_id(self.rule_id),
                            rule_id=self.rule_id,
                            rule_version=self.rule_version,
                            claim_ids=alert.claim_ids,
                            fields_matched=["unbundling_rate", "peer_p95"],
                            plain_text=(
                                f"Provider {alert.entity_id} unbundling rate "
                                f"{rate:.1f}% exceeds peer p95 ({p95_threshold * 100:.1f}%)."
                            ),
                            severity=escalated_severity,
                        ))

        return alerts

    def _find_unbundled_claims(
        self,
        claims: pd.DataFrame,
        bundling_pairs: pd.DataFrame,
        override_mods: set[str],
        base_severity: Severity,
    ) -> list[Alert]:
        """Find claim groups with unbundled comprehensive + component codes."""
        # Required columns
        req_cols = {"member_id", "billing_provider_id", "cpt_code", "service_from", "claim_id"}
        if not req_cols.issubset(set(claims.columns)):
            return []

        # Build lookup of bundling pairs
        pairs = set(
            zip(bundling_pairs["comprehensive_cpt"], bundling_pairs["component_cpt"])
        )
        all_comp_codes = set(bundling_pairs["comprehensive_cpt"])
        all_component_codes = set(bundling_pairs["component_cpt"])
        all_bundle_codes = all_comp_codes | all_component_codes

        # Filter to relevant claims
        bundle_claims = claims[claims["cpt_code"].isin(all_bundle_codes)].copy()
        if bundle_claims.empty:
            return []

        # Ensure service_from is datetime
        if not pd.api.types.is_datetime64_any_dtype(bundle_claims["service_from"]):
            bundle_claims["service_from"] = pd.to_datetime(
                bundle_claims["service_from"], errors="coerce"
            )

        # Parse modifiers
        def _has_override(mod) -> bool:
            if pd.isna(mod):
                return False
            return bool(set(str(mod).split(",")) & override_mods)

        bundle_claims["_has_override"] = bundle_claims["modifier"].apply(_has_override) \
            if "modifier" in bundle_claims.columns else False

        alerts: list[Alert] = []

        # Group by member, provider, date
        for (member, provider, svc_date), group in bundle_claims.groupby(
            ["member_id", "billing_provider_id", "service_from"]
        ):
            cpts_in_group = set(group["cpt_code"])
            has_override = group["_has_override"].any()

            # Check each bundling pair
            for comp_cpt, component_cpt in pairs:
                if comp_cpt not in cpts_in_group or component_cpt not in cpts_in_group:
                    continue

                # Skip if valid override modifier present
                if has_override:
                    continue

                # Get claim IDs for both codes
                comp_claims = group[group["cpt_code"] == comp_cpt]
                component_claims = group[group["cpt_code"] == component_cpt]

                claim_ids = sorted(
                    comp_claims["claim_id"].tolist() + component_claims["claim_id"].tolist()
                )

                # Estimate overpayment: component code amount is the excess
                amount_col = next(
                    (c for c in ["allowed_amount", "paid_amount", "billed_amount"]
                     if c in component_claims.columns),
                    None,
                )
                est_overpay = float(component_claims[amount_col].sum()) if amount_col else 0.0

                modifier_text = ""
                if "modifier" in group.columns:
                    mods = group["modifier"].dropna().unique()
                    modifier_text = f" Modifiers present: {', '.join(str(m) for m in mods)}." if len(mods) > 0 else " No modifier present."

                evidence = Evidence(
                    evidence_id=make_evidence_id(self.rule_id),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    claim_ids=[str(c) for c in claim_ids],
                    fields_matched=["cpt_code", "comprehensive_cpt", "component_cpt",
                                    "service_from", "modifier"],
                    plain_text=(
                        f"Unbundled: comprehensive CPT {comp_cpt} and component CPT "
                        f"{component_cpt} billed for member {member} by provider "
                        f"{provider} on {svc_date}.{modifier_text}"
                    ),
                    est_overpay=est_overpay,
                    severity=base_severity,
                    fp_notes=[
                        "Distinct anatomical sites may justify separate billing.",
                        "Review clinical documentation for medical necessity.",
                    ],
                )

                alerts.append(Alert(
                    alert_id=Alert.make_id(),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    entity_type="provider",
                    entity_id=str(provider),
                    claim_ids=[str(c) for c in claim_ids],
                    severity=base_severity,
                    est_dollars=est_overpay,
                    evidence=[evidence],
                    fp_notes=[
                        "Distinct anatomical sites may justify separate billing.",
                    ],
                ))

        return alerts
