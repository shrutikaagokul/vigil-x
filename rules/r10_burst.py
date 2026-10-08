"""
R10 — Burst / Spike

Detects when a provider's weekly paid dollars exceed 3x their own
trailing 12-week median AND the weekly amount exceeds $5,000.

This is a temporal behavior rule: it uses provider-specific history,
NOT a global threshold.

False-positive considerations: new provider ramp-up, seasonality,
legitimate contract changes, insufficient history.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from contracts.alert import Alert, Evidence, Severity
from config.loader import get_rule_config
from temporal.features import build_provider_weekly_panel, add_trailing_median

RULE_ID = "R10"


def detect_burst(
    claims: pd.DataFrame,
    config: Optional[Dict] = None,
) -> List[Alert]:
    """
    Run R10: detect weekly payment spikes.

    Args:
        claims: Claims DataFrame with [provider_id, service_date, paid_amount, claim_id]
        config: R10 config dict

    Returns:
        List[Alert]
    """
    if config is None:
        config = get_rule_config("R10")

    if not config.get("enabled", True):
        return []

    version = config.get("version", "1.0.0")
    multiplier = config.get("spike_multiplier", 3.0)
    dollar_floor = config.get("dollar_floor", 5000)
    trailing_weeks = config.get("trailing_weeks", 12)
    min_history = config.get("min_history_weeks", 4)
    severity = config.get("severity", Severity.MEDIUM.value)

    # Step 1: Build weekly panel
    panel = build_provider_weekly_panel(claims)
    if panel.empty:
        return []

    # Step 2: Add trailing median
    panel = add_trailing_median(panel, trailing_weeks=trailing_weeks)

    # Step 3: Compute ratio
    panel["ratio"] = np.where(
        panel["trailing_median"] > 0,
        panel["weekly_dollars"] / panel["trailing_median"],
        np.nan,
    )

    # Step 4: Flag spikes
    flagged = panel[
        (panel["weekly_dollars"] > dollar_floor)
        & (panel["ratio"] > multiplier)
        & (panel["history_weeks"] >= min_history)
    ].copy()

    # Step 5: Build alerts
    alerts = []
    for _, row in flagged.iterrows():
        pid = row["provider_id"]
        week = row["week_start"]
        current = row["weekly_dollars"]
        median = row["trailing_median"]
        ratio = row["ratio"]
        hist_wks = int(row["history_weeks"])

        # Reduce severity for borderline cases
        eff_severity = severity
        if ratio < multiplier * 1.5:
            eff_severity = Severity.LOW.value

        ev = Evidence(
            evidence_id=Evidence.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            claim_ids=[],  # Could be enriched with weekly claim IDs
            fields_matched=[
                "weekly_dollars", "trailing_median", "ratio",
                "dollar_floor", "week_start", "history_weeks",
            ],
            plain_text=(
                f"Provider {pid} paid ${current:,.2f} in week starting "
                f"{pd.Timestamp(week).strftime('%Y-%m-%d')}, which is {ratio:.1f}x "
                f"the trailing {trailing_weeks}-week median of ${median:,.2f}. "
                f"Dollar floor: ${dollar_floor:,}. History: {hist_wks} weeks."
            ),
            est_overpay=max(0, current - median),
            severity=eff_severity,
            fp_notes=(
                "Check for legitimate contract changes, new patient panel expansion, "
                "or seasonal patterns."
            ),
        )

        alerts.append(Alert(
            alert_id=Alert.generate_id(RULE_ID),
            rule_id=RULE_ID,
            rule_version=version,
            entity_type="provider",
            entity_id=pid,
            claim_ids=[],
            severity=eff_severity,
            est_dollars=max(0, current - median),
            evidence=[ev],
            metadata={
                "weekly_dollars": round(current, 2),
                "trailing_median": round(median, 2),
                "ratio": round(ratio, 2),
                "dollar_floor": dollar_floor,
                "week_start": str(pd.Timestamp(week).date()),
                "history_weeks": hist_wks,
            },
        ))

    return alerts
