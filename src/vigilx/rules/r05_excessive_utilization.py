"""
R05 — Excessive Utilization Detection.

Detects:
  A. Per-member code-group utilization above max_per_30d thresholds
  B. Provider mean visits per member > multiplier × peer median
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from vigilx.features.claim_features import compute_rolling_30d_counts
from vigilx.features.peer_features import compute_peer_stats
from vigilx.features.provider_features import compute_provider_utilization_stats
from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id
from vigilx.rules.base import BaseRule


class ExcessiveUtilizationRule(BaseRule):
    """R05 — Excessive Utilization Detection."""

    rule_id = "R05"

    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """Run excessive utilization detection."""
        if not self.enabled:
            return []

        claims = data.get("claims")
        if claims is None or claims.empty:
            return []

        cfg = self.cfg
        providers_df = data.get("providers", pd.DataFrame())

        alerts: list[Alert] = []

        # Part A: Member-level code-group caps
        alerts.extend(self._detect_member_overcaps(claims, cfg))

        # Part B: Provider-level excessive visits
        alerts.extend(self._detect_provider_excessive(claims, providers_df, cfg))

        return alerts

    # ── Part A: Member code-group overcaps ───────────────────────

    def _detect_member_overcaps(
        self, claims: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect members exceeding code-group utilization caps."""
        caps = cfg.get("utilization_caps", {})
        if not caps:
            return []

        base_severity = Severity(cfg.get("base_severity", "MEDIUM"))

        df = claims.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["service_from"]):
            df["service_from"] = pd.to_datetime(df["service_from"], errors="coerce")

        alerts: list[Alert] = []

        for group_name, group_cfg in caps.items():
            max_per_30d = group_cfg.get("max_per_30d", 999)
            prefixes = group_cfg.get("code_prefixes", [])
            if not prefixes:
                continue

            # Filter to relevant CPT codes
            mask = df["cpt_code"].apply(
                lambda c: any(str(c).startswith(p) for p in prefixes) if pd.notna(c) else False
            )
            group_claims = df[mask].copy()
            if group_claims.empty:
                continue

            # Compute rolling 30-day counts per member
            group_claims = compute_rolling_30d_counts(
                group_claims,
                group_cols=["member_id"],
                date_col="service_from",
                count_col="rolling_30d_count",
            )

            # Find members exceeding the cap
            over_cap = group_claims[group_claims["rolling_30d_count"] > max_per_30d]
            if over_cap.empty:
                continue

            # Group by member to create one alert per member
            for member_id, member_group in over_cap.groupby("member_id"):
                max_count = int(member_group["rolling_30d_count"].max())
                claim_ids = sorted(member_group["claim_id"].astype(str).tolist())

                # Find the peak window
                peak_row = member_group.loc[member_group["rolling_30d_count"].idxmax()]

                evidence = Evidence(
                    evidence_id=make_evidence_id(self.rule_id),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    claim_ids=claim_ids,
                    fields_matched=["cpt_code", "rolling_30d_count", "max_per_30d"],
                    plain_text=(
                        f"Member {member_id}: {max_count} {group_name} services "
                        f"in a 30-day window (cap: {max_per_30d}). "
                        f"Peak date: {peak_row['service_from'].date()}."
                    ),
                    est_overpay=0.0,
                    severity=base_severity,
                    fp_notes=[
                        "Acute episode or post-surgical recovery may justify increased utilization.",
                        f"Diagnosis context should be reviewed for {group_name} necessity.",
                    ],
                )

                # Estimate overpay: excess claims × average claim amount
                amount_col = next(
                    (c for c in ["allowed_amount", "paid_amount", "billed_amount"]
                     if c in member_group.columns),
                    None,
                )
                est_dollars = 0.0
                if amount_col:
                    avg_amount = member_group[amount_col].mean()
                    excess_claims = max_count - max_per_30d
                    est_dollars = round(float(avg_amount * excess_claims), 2)
                    evidence.est_overpay = est_dollars

                alerts.append(Alert(
                    alert_id=Alert.make_id(),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    entity_type="member",
                    entity_id=str(member_id),
                    claim_ids=claim_ids,
                    severity=base_severity,
                    est_dollars=est_dollars,
                    evidence=[evidence],
                    fp_notes=["Acute episode may justify increased utilization."],
                ))

        return alerts

    # ── Part B: Provider excessive visits ────────────────────────

    def _detect_provider_excessive(
        self, claims: pd.DataFrame, providers_df: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect providers with mean visits/member > multiplier × peer median."""
        multiplier = cfg.get("provider_peer_multiplier", 3.0)
        escalated_severity = Severity(cfg.get("escalated_severity", "HIGH"))

        # Compute provider utilization
        prov_stats = compute_provider_utilization_stats(claims)
        if prov_stats.empty:
            return []

        # Add peer group
        if not providers_df.empty and "peer_group" in providers_df.columns:
            prov_id_col = "provider_id" if "provider_id" in providers_df.columns else "billing_provider_id"
            prov_stats = prov_stats.merge(
                providers_df[[prov_id_col, "peer_group"]].rename(
                    columns={prov_id_col: "billing_provider_id"}
                ),
                on="billing_provider_id",
                how="left",
            )

        if "peer_group" not in prov_stats.columns:
            prov_stats["peer_group"] = "all"
        prov_stats["peer_group"] = prov_stats["peer_group"].fillna("all")

        # Compute peer stats
        prov_stats = compute_peer_stats(prov_stats, "visits_per_member", "peer_group")

        # Filter suspicious
        suspicious = prov_stats[
            prov_stats["visits_per_member"] > multiplier * prov_stats["peer_median"]
        ]
        if suspicious.empty:
            return []

        alerts: list[Alert] = []
        for _, prov in suspicious.iterrows():
            prov_id = str(prov["billing_provider_id"])
            prov_claims = claims[claims["billing_provider_id"] == prov["billing_provider_id"]]
            claim_ids = sorted(prov_claims["claim_id"].astype(str).tolist())

            vpm = prov["visits_per_member"]
            peer_med = prov["peer_median"]

            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=claim_ids,
                fields_matched=["visits_per_member", "peer_median", "peer_multiplier"],
                plain_text=(
                    f"Provider {prov_id}: {vpm:.1f} visits/member "
                    f"vs peer median {peer_med:.1f} "
                    f"({vpm / peer_med:.1f}x peer median)."
                ),
                severity=escalated_severity,
                fp_notes=[
                    "High-utilization specialty (e.g., oncology, dialysis) may explain volume.",
                    "Chronic disease management programs may justify frequent visits.",
                ],
            )

            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="provider",
                entity_id=prov_id,
                claim_ids=claim_ids,
                severity=escalated_severity,
                est_dollars=0.0,
                evidence=[evidence],
                fp_notes=[
                    "High-utilization specialty may explain volume.",
                ],
            ))

        return alerts
