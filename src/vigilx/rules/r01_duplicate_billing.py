"""
R01 — Duplicate Billing Detection.

Detects exact and near-duplicate claims:
  A. Exact: same member, provider, CPT, service date, amount
  B. Near:  same member, provider, CPT, date ±1 day, same amount

Excludes corrected/voided claims and legitimate modifiers (LT, RT, 50, 76, 77).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id
from vigilx.rules.base import BaseRule


class DuplicateBillingRule(BaseRule):
    """R01 — Duplicate Billing."""

    rule_id = "R01"

    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """Run duplicate billing detection across all claims."""
        if not self.enabled:
            return []

        claims = data.get("claims")
        if claims is None or claims.empty:
            return []

        cfg = self.cfg
        day_window = cfg.get("near_dup_day_window", 1)
        legit_mods = set(cfg.get("legitimate_modifiers", ["LT", "RT", "50", "76", "77"]))
        void_statuses = set(s.lower() for s in cfg.get("void_statuses", []))
        corrected_statuses = set(s.lower() for s in cfg.get("corrected_statuses", []))
        sev_exact = Severity(cfg.get("severity_exact", "HIGH"))
        sev_near = Severity(cfg.get("severity_near", "MEDIUM"))

        df = self._prepare(claims, void_statuses, corrected_statuses, legit_mods)
        if df.empty:
            return []

        alerts: list[Alert] = []
        alerts.extend(self._detect_exact(df, sev_exact))
        alerts.extend(self._detect_near(df, sev_near, day_window))
        return alerts

    # ── internal helpers ─────────────────────────────────────────

    def _prepare(
        self,
        claims: pd.DataFrame,
        void_statuses: set[str],
        corrected_statuses: set[str],
        legit_mods: set[str],
    ) -> pd.DataFrame:
        """
        Prepare claims for duplicate detection.

        Marks claims that should be excluded (voided, corrected, legitimate
        modifiers) but does NOT drop them — their presence is itself a signal.
        """
        df = claims.copy()

        # Ensure service_from is datetime
        if not pd.api.types.is_datetime64_any_dtype(df["service_from"]):
            df["service_from"] = pd.to_datetime(df["service_from"], errors="coerce")

        # Flag exclusion reasons (kept for evidence, not for dropping)
        df["_is_void"] = False
        if "claim_status" in df.columns:
            df["_is_void"] = df["claim_status"].str.lower().isin(void_statuses)

        df["_is_corrected"] = False
        if "claim_status" in df.columns:
            df["_is_corrected"] = df["claim_status"].str.lower().isin(corrected_statuses)

        df["_has_legit_mod"] = False
        if "modifier" in df.columns:
            df["_has_legit_mod"] = df["modifier"].apply(
                lambda m: bool(set(str(m).split(",")) & legit_mods) if pd.notna(m) else False
            )

        # Combined exclusion flag
        df["_excluded"] = df["_is_void"] | df["_is_corrected"] | df["_has_legit_mod"]

        return df

    def _detect_exact(self, df: pd.DataFrame, severity: Severity) -> list[Alert]:
        """Detect exact duplicate claims."""
        match_cols = ["member_id", "billing_provider_id", "cpt_code", "service_from", "billed_amount"]
        available = [c for c in match_cols if c in df.columns]
        if len(available) < len(match_cols):
            # Fall back to whatever columns exist
            amount_col = next(
                (c for c in ["billed_amount", "allowed_amount", "paid_amount"] if c in df.columns),
                None,
            )
            available = [c for c in ["member_id", "billing_provider_id", "cpt_code", "service_from"] if c in df.columns]
            if amount_col:
                available.append(amount_col)

        # Only look at non-excluded claims for flagging
        active = df[~df["_excluded"]].copy()
        if active.empty:
            return []

        # Find groups of exact matches
        dupes = active[active.duplicated(subset=available, keep=False)]
        if dupes.empty:
            return []

        alerts: list[Alert] = []
        seen_pairs: set[tuple[str, str]] = set()

        for _, group in dupes.groupby(available):
            claim_ids = sorted(group["claim_id"].tolist())
            if len(claim_ids) < 2:
                continue

            # Create one alert per unique pair to avoid double-counting
            for i in range(len(claim_ids)):
                for j in range(i + 1, len(claim_ids)):
                    pair_key = (claim_ids[i], claim_ids[j])
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    row = group.iloc[0]
                    amount_col = next(
                        (c for c in ["billed_amount", "allowed_amount", "paid_amount"] if c in group.columns),
                        None,
                    )
                    amount = float(row[amount_col]) if amount_col and pd.notna(row[amount_col]) else 0.0

                    evidence = Evidence(
                        evidence_id=make_evidence_id(self.rule_id),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        claim_ids=[claim_ids[i], claim_ids[j]],
                        fields_matched=available,
                        plain_text=(
                            f"Exact duplicate: claims {claim_ids[i]} and {claim_ids[j]} "
                            f"share member={row['member_id']}, provider={row['billing_provider_id']}, "
                            f"CPT={row['cpt_code']}, date={row['service_from']}, "
                            f"amount=${amount:,.2f}."
                        ),
                        est_overpay=amount,  # One of the two is the overpayment
                        severity=severity,
                    )

                    alerts.append(Alert(
                        alert_id=Alert.make_id(),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        entity_type="provider",
                        entity_id=str(row["billing_provider_id"]),
                        claim_ids=[claim_ids[i], claim_ids[j]],
                        severity=severity,
                        est_dollars=amount,
                        evidence=[evidence],
                    ))

        return alerts

    def _detect_near(self, df: pd.DataFrame, severity: Severity, day_window: int) -> list[Alert]:
        """Detect near-duplicate claims (date within ±day_window)."""
        active = df[~df["_excluded"]].copy()
        if active.empty:
            return []

        # Group by member, provider, CPT — then check date proximity
        group_cols = [c for c in ["member_id", "billing_provider_id", "cpt_code"] if c in active.columns]
        amount_col = next(
            (c for c in ["billed_amount", "allowed_amount", "paid_amount"] if c in active.columns),
            None,
        )

        alerts: list[Alert] = []
        seen_pairs: set[tuple[str, str]] = set()
        # Also track pairs already flagged as exact duplicates by checking same-day
        exact_keys = set()

        for _, group in active.groupby(group_cols):
            if len(group) < 2:
                continue

            rows = group.sort_values("service_from").reset_index(drop=True)
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    r1, r2 = rows.iloc[i], rows.iloc[j]
                    cid1, cid2 = str(r1["claim_id"]), str(r2["claim_id"])

                    pair_key = (min(cid1, cid2), max(cid1, cid2))
                    if pair_key in seen_pairs:
                        continue

                    date_diff = abs((r2["service_from"] - r1["service_from"]).days)

                    # Skip exact duplicates (date_diff == 0) — already caught
                    if date_diff == 0:
                        continue

                    if date_diff > day_window:
                        continue

                    # Amount must match for near-duplicate
                    if amount_col:
                        a1 = r1[amount_col] if pd.notna(r1[amount_col]) else None
                        a2 = r2[amount_col] if pd.notna(r2[amount_col]) else None
                        if a1 != a2:
                            continue
                        amount = float(a1) if a1 is not None else 0.0
                    else:
                        amount = 0.0

                    seen_pairs.add(pair_key)

                    evidence = Evidence(
                        evidence_id=make_evidence_id(self.rule_id),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        claim_ids=[cid1, cid2],
                        fields_matched=group_cols + ["billed_amount"],
                        plain_text=(
                            f"Near duplicate: claims {cid1} and {cid2} "
                            f"share member={r1['member_id']}, provider={r1['billing_provider_id']}, "
                            f"CPT={r1['cpt_code']}, amount=${amount:,.2f}, "
                            f"dates {date_diff} day(s) apart."
                        ),
                        est_overpay=amount,
                        severity=severity,
                        fp_notes=["Date difference may indicate a legitimate follow-up visit."],
                    )

                    alerts.append(Alert(
                        alert_id=Alert.make_id(),
                        rule_id=self.rule_id,
                        rule_version=self.rule_version,
                        entity_type="provider",
                        entity_id=str(r1["billing_provider_id"]),
                        claim_ids=[cid1, cid2],
                        severity=severity,
                        est_dollars=amount,
                        evidence=[evidence],
                        fp_notes=["Date difference may indicate a legitimate follow-up visit."],
                    ))

        return alerts
