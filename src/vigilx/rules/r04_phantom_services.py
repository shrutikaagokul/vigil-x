"""
R04 — Phantom Services Detection.

Detects suspicious claims with no plausible real-world service:
  1. Service after member death
  2. Service after member termination
  3. Service during another facility inpatient stay
  4. Service on facility non-operating day
  5. Service before facility open date / after close date
  6. Ambulance claim with no related ER/facility claim within 1 day
  7. Ghost member heuristic (weak signal — never standalone)
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from vigilx.features.member_features import flag_ghost_members
from vigilx.models.alert import Alert, Evidence, Severity, make_evidence_id
from vigilx.rules.base import BaseRule


class PhantomServicesRule(BaseRule):
    """R04 — Phantom Services Detection."""

    rule_id = "R04"

    def detect(self, data: dict[str, Any]) -> list[Alert]:
        """Run all phantom service checks."""
        if not self.enabled:
            return []

        claims = data.get("claims")
        if claims is None or claims.empty:
            return []

        cfg = self.cfg
        members = data.get("members", pd.DataFrame())
        facilities = data.get("facilities", pd.DataFrame())
        inpatient_stays = data.get("inpatient_stays", pd.DataFrame())

        alerts: list[Alert] = []

        # Ensure datetime
        df = claims.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["service_from"]):
            df["service_from"] = pd.to_datetime(df["service_from"], errors="coerce")

        # 1 & 2: Post-death and post-termination
        if not members.empty:
            alerts.extend(self._detect_post_death(df, members, cfg))
            alerts.extend(self._detect_post_termination(df, members, cfg))

        # 3: Inpatient overlap
        if not inpatient_stays.empty:
            alerts.extend(self._detect_inpatient_overlap(df, inpatient_stays, cfg))

        # 4 & 5: Facility-based checks
        if not facilities.empty:
            alerts.extend(self._detect_closed_facility(df, facilities, cfg))
            alerts.extend(self._detect_non_operating_day(df, facilities, cfg))

        # 6: Orphan ambulance
        alerts.extend(self._detect_orphan_ambulance(df, cfg))

        # 7: Ghost members (weak signal only)
        ghost_cfg = cfg.get("ghost_member", {})
        alerts.extend(self._detect_ghost_members(
            df,
            lookback_months=ghost_cfg.get("lookback_months", 12),
            min_claims=ghost_cfg.get("min_same_provider_claims", 5),
            severity=Severity(cfg.get("severity_ghost_member", "LOW")),
        ))

        return alerts

    # ── 1. Post-death ────────────────────────────────────────────

    def _detect_post_death(
        self, claims: pd.DataFrame, members: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect claims with service date after member death date."""
        if "death_date" not in members.columns:
            return []

        severity = Severity(cfg.get("severity_deceased", "CRITICAL"))

        deceased = members[members["death_date"].notna()].copy()
        if deceased.empty:
            return []

        if not pd.api.types.is_datetime64_any_dtype(deceased["death_date"]):
            deceased["death_date"] = pd.to_datetime(deceased["death_date"], errors="coerce")

        merged = claims.merge(
            deceased[["member_id", "death_date"]],
            on="member_id",
            how="inner",
        )
        post_death = merged[merged["service_from"] > merged["death_date"]]
        if post_death.empty:
            return []

        alerts: list[Alert] = []
        for _, row in post_death.iterrows():
            days_after = (row["service_from"] - row["death_date"]).days
            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=["service_from", "death_date"],
                plain_text=(
                    f"Service on {row['service_from'].date()} is {days_after} day(s) "
                    f"after member {row['member_id']} death on {row['death_date'].date()}."
                ),
                severity=severity,
                fp_notes=["Verify death date accuracy — retroactive corrections are possible."],
            )
            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="provider",
                entity_id=str(row.get("billing_provider_id", "unknown")),
                claim_ids=[str(row["claim_id"])],
                severity=severity,
                est_dollars=float(row.get("billed_amount", row.get("allowed_amount", 0)) or 0),
                evidence=[evidence],
            ))
        return alerts

    # ── 2. Post-termination ──────────────────────────────────────

    def _detect_post_termination(
        self, claims: pd.DataFrame, members: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect claims after member eligibility termination."""
        term_col = next((c for c in ["enrollment_end", "termination_date"] if c in members.columns), None)
        if term_col is None:
            return []

        severity = Severity(cfg.get("severity_terminated", "CRITICAL"))

        termed = members[members[term_col].notna()].copy()
        if termed.empty:
            return []

        if not pd.api.types.is_datetime64_any_dtype(termed[term_col]):
            termed[term_col] = pd.to_datetime(termed[term_col], errors="coerce")

        merged = claims.merge(
            termed[["member_id", term_col]],
            on="member_id",
            how="inner",
        )
        post_term = merged[merged["service_from"] > merged[term_col]]
        if post_term.empty:
            return []

        alerts: list[Alert] = []
        for _, row in post_term.iterrows():
            days_after = (row["service_from"] - row[term_col]).days
            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=["service_from", term_col],
                plain_text=(
                    f"Service on {row['service_from'].date()} is {days_after} day(s) "
                    f"after member {row['member_id']} coverage termination / enrollment ended "
                    f"on {row[term_col].date()}."
                ),
                severity=severity,
                fp_notes=[
                    "Retroactive eligibility reinstatement may apply.",
                    "COBRA or continuation coverage may explain post-termination services.",
                ],
            )
            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="provider",
                entity_id=str(row.get("billing_provider_id", "unknown")),
                claim_ids=[str(row["claim_id"])],
                severity=severity,
                est_dollars=float(row.get("billed_amount", row.get("allowed_amount", 0)) or 0),
                evidence=[evidence],
            ))
        return alerts

    # ── 3. Inpatient overlap ─────────────────────────────────────

    def _detect_inpatient_overlap(
        self, claims: pd.DataFrame, inpatient_stays: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect outpatient claims during another facility's inpatient stay."""
        severity = Severity(cfg.get("severity_inpatient_overlap", "HIGH"))

        stays = inpatient_stays.copy()
        admit_col = next((c for c in ["admission_date", "admit_date"] if c in stays.columns), None)
        discharge_col = next((c for c in ["discharge_date", "disch_date"] if c in stays.columns), None)

        if not admit_col or not discharge_col:
            return []

        for col in [admit_col, discharge_col]:
            if not pd.api.types.is_datetime64_any_dtype(stays[col]):
                stays[col] = pd.to_datetime(stays[col], errors="coerce")

        stays_subset = stays[["member_id", "facility_id", admit_col, discharge_col]].rename(
            columns={
                "facility_id": "inpatient_facility_id",
                admit_col: "admission_date",
                discharge_col: "discharge_date",
            }
        )

        # Merge claims with inpatient stays on member
        merged = claims.merge(stays_subset, on="member_id", how="inner")

        # Service during inpatient stay
        overlap = merged[
            (merged["service_from"] >= merged["admission_date"])
            & (merged["service_from"] <= merged["discharge_date"])
        ]

        # Exclude claims billed by or at the inpatient facility itself
        if "facility_id" in overlap.columns:
            overlap = overlap[
                overlap["facility_id"].astype(str) != overlap["inpatient_facility_id"].astype(str)
            ]
        elif "billing_provider_id" in overlap.columns:
            overlap = overlap[
                overlap["billing_provider_id"].astype(str) != overlap["inpatient_facility_id"].astype(str)
            ]

        if overlap.empty:
            return []

        alerts: list[Alert] = []
        for _, row in overlap.iterrows():
            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=["service_from", "admission_date", "discharge_date", "inpatient_facility_id"],
                plain_text=(
                    f"Service on {row['service_from'].date()} for member {row['member_id']} "
                    f"overlaps inpatient stay at facility {row['inpatient_facility_id']} "
                    f"({row['admission_date'].date()} to {row['discharge_date'].date()})."
                ),
                severity=severity,
            )
            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="provider",
                entity_id=str(row.get("billing_provider_id", "unknown")),
                claim_ids=[str(row["claim_id"])],
                severity=severity,
                est_dollars=float(row.get("billed_amount", row.get("allowed_amount", 0)) or 0),
                evidence=[evidence],
            ))
        return alerts

    # ── 4 & 5. Closed / non-operating facility ──────────────────

    def _detect_closed_facility(
        self, claims: pd.DataFrame, facilities: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect claims at facilities that were closed on the service date."""
        severity = Severity(cfg.get("severity_closed_facility", "HIGH"))

        fac = facilities.copy()
        for col in ["open_date", "close_date"]:
            if col in fac.columns and not pd.api.types.is_datetime64_any_dtype(fac[col]):
                fac[col] = pd.to_datetime(fac[col], errors="coerce")

        # Need a join key between claims and facilities
        join_col = "facility_id" if "facility_id" in claims.columns else "billing_provider_id"
        fac_id_col = "facility_id" if "facility_id" in fac.columns else "provider_id"

        if fac_id_col not in fac.columns:
            return []

        date_cols = [c for c in ["open_date", "close_date"] if c in fac.columns]
        if not date_cols:
            return []

        merged = claims.merge(
            fac[[fac_id_col] + date_cols].rename(
                columns={fac_id_col: join_col}
            ),
            on=join_col,
            how="inner",
        )

        closed_before = pd.DataFrame()
        not_yet_open = pd.DataFrame()

        if "close_date" in merged.columns:
            closed_before = merged[
                merged["close_date"].notna()
                & (merged["service_from"] > merged["close_date"])
            ]
        if "open_date" in merged.columns:
            not_yet_open = merged[
                merged["open_date"].notna()
                & (merged["service_from"] < merged["open_date"])
            ]

        suspect = pd.concat([closed_before, not_yet_open]).drop_duplicates(subset=["claim_id"])
        if suspect.empty:
            return []

        alerts: list[Alert] = []
        for _, row in suspect.iterrows():
            reason = "after facility closure" if pd.notna(row.get("close_date")) and \
                row["service_from"] > row["close_date"] else "before facility opening"

            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=["service_from", "open_date", "close_date"],
                plain_text=(
                    f"Service on {row['service_from'].date()} at facility {row.get(join_col)} "
                    f"occurred {reason}."
                ),
                severity=severity,
            )
            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="facility",
                entity_id=str(row.get(join_col, "unknown")),
                claim_ids=[str(row["claim_id"])],
                severity=severity,
                est_dollars=float(row.get("billed_amount", row.get("allowed_amount", 0)) or 0),
                evidence=[evidence],
            ))
        return alerts

    def _detect_non_operating_day(
        self, claims: pd.DataFrame, facilities: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect claims on days when the facility does not operate."""
        severity = Severity(cfg.get("severity_non_operating_day", "HIGH"))

        if "operating_days" not in facilities.columns:
            return []

        fac = facilities.copy()
        join_col = "facility_id" if "facility_id" in claims.columns else "billing_provider_id"
        fac_id_col = "facility_id" if "facility_id" in fac.columns else "provider_id"

        if fac_id_col not in fac.columns:
            return []

        merged = claims.merge(
            fac[[fac_id_col, "operating_days"]].rename(columns={fac_id_col: join_col}),
            on=join_col,
            how="inner",
        )

        # operating_days is expected to be a string like "Mon,Tue,Wed,Thu,Fri"
        day_map = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
        merged["_day_name"] = merged["service_from"].dt.dayofweek.map(day_map)
        merged["_is_operating"] = merged.apply(
            lambda r: str(r["_day_name"]) in str(r["operating_days"]) if pd.notna(r["operating_days"]) else True,
            axis=1,
        )

        non_op = merged[~merged["_is_operating"]]
        if non_op.empty:
            return []

        alerts: list[Alert] = []
        for _, row in non_op.iterrows():
            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=[str(row["claim_id"])],
                fields_matched=["service_from", "operating_days"],
                plain_text=(
                    f"Service on {row['service_from'].date()} ({row['_day_name']}) at "
                    f"facility {row.get(join_col)}, which operates on: {row['operating_days']}."
                ),
                severity=severity,
            )
            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="facility",
                entity_id=str(row.get(join_col, "unknown")),
                claim_ids=[str(row["claim_id"])],
                severity=severity,
                est_dollars=float(row.get("billed_amount", row.get("allowed_amount", 0)) or 0),
                evidence=[evidence],
            ))
        return alerts

    # ── 6. Orphan ambulance ──────────────────────────────────────

    def _detect_orphan_ambulance(
        self, claims: pd.DataFrame, cfg: dict,
    ) -> list[Alert]:
        """Detect ambulance claims without a related ER/facility claim within 1 day."""
        severity = Severity(cfg.get("severity_orphan_ambulance", "MEDIUM"))
        window_days = cfg.get("ambulance_related_window_days", 1)

        # Identify ambulance claims by CPT prefix (A0xxx) or place_of_service
        if "cpt_code" not in claims.columns:
            return []

        ambulance = claims[claims["cpt_code"].str.startswith("A0", na=False)].copy()
        if ambulance.empty:
            return []

        non_ambulance = claims[~claims["cpt_code"].str.startswith("A0", na=False)]

        alerts: list[Alert] = []
        for _, amb_row in ambulance.iterrows():
            member = amb_row["member_id"]
            amb_date = amb_row["service_from"]

            # Find related claims within window
            member_claims = non_ambulance[non_ambulance["member_id"] == member]
            if member_claims.empty:
                related = pd.DataFrame()
            else:
                related = member_claims[
                    (member_claims["service_from"] >= amb_date - pd.Timedelta(days=window_days))
                    & (member_claims["service_from"] <= amb_date + pd.Timedelta(days=window_days))
                ]

            if related.empty:
                evidence = Evidence(
                    evidence_id=make_evidence_id(self.rule_id),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    claim_ids=[str(amb_row["claim_id"])],
                    fields_matched=["cpt_code", "service_from", "member_id"],
                    plain_text=(
                        f"Ambulance claim {amb_row['claim_id']} (CPT {amb_row['cpt_code']}) "
                        f"for member {member} on {amb_date.date()} has no related "
                        f"ER/facility claim within {window_days} day(s)."
                    ),
                    severity=severity,
                    fp_notes=["Patient may have been transported to an out-of-network facility."],
                )
                alerts.append(Alert(
                    alert_id=Alert.make_id(),
                    rule_id=self.rule_id,
                    rule_version=self.rule_version,
                    entity_type="provider",
                    entity_id=str(amb_row.get("billing_provider_id", "unknown")),
                    claim_ids=[str(amb_row["claim_id"])],
                    severity=severity,
                    est_dollars=float(
                        amb_row.get("billed_amount", amb_row.get("allowed_amount", 0)) or 0
                    ),
                    evidence=[evidence],
                    fp_notes=["Patient may have been transported to an out-of-network facility."],
                ))

        return alerts

    # ── 7. Ghost members ─────────────────────────────────────────

    def _detect_ghost_members(
        self,
        claims: pd.DataFrame,
        lookback_months: int,
        min_claims: int,
        severity: Severity,
    ) -> list[Alert]:
        """
        Flag potential ghost members (weak heuristic signal).

        IMPORTANT: Ghost member alerts are always LOW severity and
        must NEVER create a case by themselves.
        """
        ghosts = flag_ghost_members(claims, lookback_months, min_claims)
        ghost_rows = ghosts[ghosts["is_ghost"]]

        if ghost_rows.empty:
            return []

        alerts: list[Alert] = []
        for _, row in ghost_rows.iterrows():
            member = row["member_id"]
            provider = row["billing_provider_id"]
            count = row["claim_count"]

            member_claims = claims[
                (claims["member_id"] == member)
                & (claims["billing_provider_id"] == provider)
            ]
            claim_ids = sorted(member_claims["claim_id"].astype(str).tolist())

            evidence = Evidence(
                evidence_id=make_evidence_id(self.rule_id),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                claim_ids=claim_ids,
                fields_matched=["member_id", "billing_provider_id", "claim_count",
                                "historical_utilization"],
                plain_text=(
                    f"Member {member} has {count} claims with provider {provider} "
                    f"but no claims in the previous {lookback_months} months. "
                    f"Possible ghost member."
                ),
                severity=severity,
                fp_notes=[
                    "New member enrollment may explain lack of history.",
                    "This is a weak heuristic signal — must NOT create a case alone.",
                ],
            )

            alerts.append(Alert(
                alert_id=Alert.make_id(),
                rule_id=self.rule_id,
                rule_version=self.rule_version,
                entity_type="member",
                entity_id=str(member),
                claim_ids=claim_ids,
                severity=severity,
                est_dollars=0.0,  # Ghost signal alone has no dollar estimate
                evidence=[evidence],
                fp_notes=[
                    "Weak heuristic — must not create a case by itself.",
                    "New enrollment may explain lack of history.",
                ],
            ))

        return alerts
