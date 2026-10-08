"""
R02 — Upcoding Detection.

Detects abnormal E/M coding at provider level relative to peer behavior:
  - MAD z-score > threshold on Level 4/5 share
  - Level 4/5 share >= multiplier × peer median
  - Minimum claim volume required

Claim-level supporting evidence:
  - Level 5 with low dx_complexity
  - Service duration below peer p25
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from vigilx.features.claim_features import extract_em_level
from vigilx.features.peer_features import compute_mad_zscore, compute_peer_duration_stats
from vigilx.features.provider_features import compute_provider_em_distribution
from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id
from vigilx.rules.base import BaseRule


class UpcodingRule(BaseRule):
    """R02 — Upcoding Detection."""

    rule_id = "R02"

    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """Run upcoding detection across all claims."""
        if not self.enabled:
            return []

        claims = data.get("claims")
        if claims is None or claims.empty:
            return []

        cfg = self.cfg
        min_claims = cfg.get("min_em_claims", 50)
        mad_z_threshold = cfg.get("mad_z_threshold", 3.0)
        share_multiplier = cfg.get("share_multiplier", 2.0)
        claim_cfg = cfg.get("claim_level", {})
        low_complexity_max = claim_cfg.get("low_complexity_max", 1)
        duration_pct = claim_cfg.get("duration_percentile", 25)

        providers = data.get("providers", pd.DataFrame())

        # Step 1: Extract E/M levels
        df = extract_em_level(claims)
        em_claims = df[df["em_level"].notna()].copy()
        if em_claims.empty:
            return []

        # Step 2: Compute provider-level E/M distributions
        prov_em = compute_provider_em_distribution(em_claims)
        if prov_em.empty:
            return []

        # Step 3: Add peer group if available
        if not providers.empty and "peer_group" in providers.columns:
            prov_em = prov_em.merge(
                providers[["provider_id", "peer_group"]].rename(
                    columns={"provider_id": "billing_provider_id"}
                ),
                on="billing_provider_id",
                how="left",
            )
        if "peer_group" not in prov_em.columns:
            prov_em["peer_group"] = "all"

        prov_em["peer_group"] = prov_em["peer_group"].fillna("all")

        # Step 4: Compute peer-relative stats
        prov_em = self._add_peer_stats(prov_em)

        # Step 5: Filter to suspicious providers
        suspicious = prov_em[
            (prov_em["total_em_claims"] >= min_claims)
            & (prov_em["peer_zscore"] > mad_z_threshold)
            & (prov_em["level_45_share"] >= share_multiplier * prov_em["peer_median"])
        ].copy()

        if suspicious.empty:
            return []

        # Step 6: Compute duration stats for claim-level evidence
        duration_stats = compute_peer_duration_stats(em_claims)

        # Step 7: Build alerts
        alerts: list[Alert] = []
        for _, prov in suspicious.iterrows():
            prov_id = str(prov["billing_provider_id"])
            prov_claims = em_claims[em_claims["billing_provider_id"] == prov["billing_provider_id"]]

            alert = self._build_provider_alert(
                prov, prov_id, prov_claims, duration_stats,
                low_complexity_max, duration_pct,
            )
            alerts.append(alert)

        return alerts

    # ── internal helpers ─────────────────────────────────────────

    def _add_peer_stats(self, prov_em: pd.DataFrame) -> pd.DataFrame:
        """Add peer median, p95, and MAD z-score for level_45_share."""
        peer_agg = prov_em.groupby("peer_group")["level_45_share"].agg(
            peer_median="median",
            peer_p95=lambda x: x.quantile(0.95),
        ).reset_index()

        prov_em = prov_em.merge(peer_agg, on="peer_group", how="left")

        # Compute MAD z-score within each peer group
        z_scores = []
        for _, group in prov_em.groupby("peer_group"):
            z = compute_mad_zscore(group["level_45_share"], center=group["peer_median"].iloc[0])
            z_scores.append(z)

        prov_em["peer_zscore"] = pd.concat(z_scores).reindex(prov_em.index)
        return prov_em

    def _build_provider_alert(
        self,
        prov: pd.Series,
        prov_id: str,
        prov_claims: pd.DataFrame,
        duration_stats: pd.DataFrame,
        low_complexity_max: int,
        duration_pct: int,
    ) -> Alert:
        """Build a complete alert for a suspicious provider."""
        l45_pct = prov["level_45_share"] * 100
        peer_med_pct = prov["peer_median"] * 100
        z_score = prov["peer_zscore"]

        # Estimate overpayment: difference between actual high-level amounts
        # and expected lower-level amounts
        est_dollars = self._estimate_overpayment(prov_claims)

        # Provider-level evidence
        prov_evidence = Evidence(
            evidence_id=make_evidence_id(self.rule_id),
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            claim_ids=sorted(prov_claims["claim_id"].tolist()),
            fields_matched=["em_level", "level_45_share", "peer_median", "peer_zscore"],
            plain_text=(
                f"Provider {prov_id} has {l45_pct:.0f}% Level-4/5 E/M visits "
                f"versus peer median {peer_med_pct:.0f}% "
                f"(MAD z-score={z_score:.1f})."
            ),
            est_overpay=est_dollars,
            severity=Severity.HIGH,
            fp_notes=[
                "High-acuity patient mix may explain elevated E/M levels.",
                "Specialty differences may account for higher coding patterns.",
            ],
        )

        evidence_items = [prov_evidence]

        # Claim-level supporting evidence
        claim_evidence = self._build_claim_evidence(
            prov_claims, duration_stats, low_complexity_max, duration_pct,
        )
        evidence_items.extend(claim_evidence)

        all_claim_ids = sorted(prov_claims["claim_id"].tolist())

        return Alert(
            alert_id=Alert.make_id(),
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            entity_type="provider",
            entity_id=prov_id,
            claim_ids=all_claim_ids,
            severity=Severity.HIGH,
            est_dollars=est_dollars,
            evidence=evidence_items,
            fp_notes=[
                "High-acuity patient panel may explain elevated E/M levels.",
                "Chronic/high-risk patient populations may justify higher coding.",
            ],
        )

    def _build_claim_evidence(
        self,
        prov_claims: pd.DataFrame,
        duration_stats: pd.DataFrame,
        low_complexity_max: int,
        duration_pct: int,
    ) -> list[Evidence]:
        """Build claim-level supporting evidence for low-complexity Level-5 claims."""
        evidence: list[Evidence] = []

        # Level 5 with low complexity
        level5 = prov_claims[prov_claims["em_level"] == 5].copy()
        if level5.empty:
            return evidence

        if "dx_complexity" in level5.columns:
            low_cx = level5[level5["dx_complexity"] <= low_complexity_max].copy()
        else:
            low_cx = pd.DataFrame()

        if low_cx.empty:
            return evidence

        # Add duration stats if available
        if "service_minutes" in low_cx.columns and not duration_stats.empty and "duration_p25" in duration_stats.columns:
            low_cx = low_cx.merge(
                duration_stats[["cpt_code", "duration_p25"]],
                on="cpt_code",
                how="left",
            )

        # Limit to top 10 examples for readability
        for _, row in low_cx.head(10).iterrows():
            fields = ["em_level", "dx_complexity"]
            text_parts = [
                f"Claim {row['claim_id']} billed Level 5 "
                f"for dx_complexity={int(row.get('dx_complexity', 0))}"
            ]

            if (
                "service_minutes" in row.index
                and pd.notna(row.get("service_minutes"))
                and "duration_p25" in row.index
                and pd.notna(row.get("duration_p25"))
                and row["service_minutes"] < row["duration_p25"]
            ):
                fields.append("service_minutes")
                text_parts.append(
                    f"with service duration {row['service_minutes']:.0f} min "
                    f"below peer p25"
                )

            evidence.append(Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=fields,
                plain_text=" ".join(text_parts) + ".",
                severity=Severity.MEDIUM,
            ))

        return evidence

    def _estimate_overpayment(self, prov_claims: pd.DataFrame) -> float:
        """
        Estimate overpayment from upcoding.

        Uses the difference between actual high-level allowed amounts
        and expected lower-level allowed amounts. Only estimates when
        actual amount data is available.
        """
        amount_col = next(
            (c for c in ["allowed_amount", "paid_amount", "billed_amount"]
             if c in prov_claims.columns),
            None,
        )
        if amount_col is None:
            return 0.0

        # For Level 4/5 claims, estimate overpay as ~40% of amount
        # (typical difference between Level 3 and Level 4/5 reimbursement)
        high_level = prov_claims[prov_claims["em_level"].isin([4, 5])]
        if high_level.empty:
            return 0.0

        total_high = high_level[amount_col].sum()
        # Conservative: estimate 35% is overpayment (difference from expected level)
        return round(float(total_high * 0.35), 2)
