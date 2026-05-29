"""
stats.py — Statistical helper functions.

Pure functions only — no database calls, no side effects.
Each function takes plain Python values and returns a formatted string
the agent can read directly.

Three capabilities:
  1. detect_anomalies  — flag unusual values in a time series using z-scores
  2. compare_cohort_rates — two-proportion z-test to check if a rate
     difference between two groups is real or just random variation
  3. investigate_drop — decompose a before/after change across a dimension
     (e.g. region, plan tier) to see where the change came from
"""

from __future__ import annotations

import math
from typing import Sequence


# --- z-score anomaly detection ---

def _z_scores(values: Sequence[float]) -> list[float]:
    """
    Compute a z-score for each value.
    z = (x - mean) / std_dev

    A z-score tells you how many standard deviations a point sits
    above or below the mean. Used internally by detect_anomalies.
    """
    n = len(values)
    if n < 2:
        return [0.0] * n

    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)  # sample variance
    std = math.sqrt(variance) if variance > 0 else 1.0

    return [(x - mean) / std for x in values]


def detect_anomalies(
    dates: Sequence[str],
    values: Sequence[float],
    threshold: float = 2.0,
) -> str:
    """
    Flag values that are more than `threshold` standard deviations from the mean.

    Args:
        dates:     Date labels, one per data point (e.g. ["2025-01", "2025-02"]).
        values:    Numeric values corresponding to each date.
        threshold: Z-score cutoff. 2.0 catches the outer ~5% of a normal distribution.

    Returns a plain-text list of anomalous points, or a message if none found.
    """
    if len(dates) != len(values):
        return "Error: dates and values must be the same length."
    if len(values) < 3:
        return "Not enough data points (need at least 3)."

    scores = _z_scores(list(values))
    anomalies = [
        (dates[i], values[i], scores[i])
        for i in range(len(values))
        if abs(scores[i]) >= threshold
    ]

    if not anomalies:
        return f"No anomalies found (z-score threshold: {threshold})."

    lines = [f"Anomalies detected (z-score threshold: {threshold}):"]
    for date, value, z in anomalies:
        direction = "high" if z > 0 else "low"
        lines.append(f"  {date}: {value:,.2f}  (z={z:.2f}, unusually {direction})")

    return "\n".join(lines)


# --- two-proportion z-test ---

def _normal_cdf(x: float) -> float:
    """
    Standard normal CDF using math.erf.
    Avoids a scipy dependency for a single p-value calculation.
    """
    return (1.0 + math.erf(x / math.sqrt(2))) / 2


def compare_cohort_rates(
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    label_a: str = "Group A",
    label_b: str = "Group B",
) -> str:
    """
    Two-proportion z-test: checks whether the rate difference between two
    groups is statistically significant, or could plausibly be due to chance.

    Example use: is the churn rate for EMEA enterprise (37%) meaningfully
    higher than NAM enterprise (22%)?

    Args:
        successes_a / trials_a: count and total for group A (e.g. churned / total)
        successes_b / trials_b: count and total for group B
        label_a / label_b:      display names for the output

    Returns a plain-text summary with rates, z-score, p-value, and verdict.
    """
    if trials_a == 0 or trials_b == 0:
        return "Error: trial counts must be greater than zero."

    rate_a = successes_a / trials_a
    rate_b = successes_b / trials_b

    # Pooled proportion — used to estimate the shared standard error under H0
    pooled = (successes_a + successes_b) / (trials_a + trials_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / trials_a + 1 / trials_b))

    if se == 0:
        return "Error: standard error is zero (all values are identical)."

    z = (rate_a - rate_b) / se
    p_value = 2 * (1 - _normal_cdf(abs(z)))  # two-tailed

    verdict = "significant" if p_value < 0.05 else "not significant"

    lines = [
        f"{label_a}: {rate_a:.1%}  ({successes_a} / {trials_a})",
        f"{label_b}: {rate_b:.1%}  ({successes_b} / {trials_b})",
        f"Difference: {(rate_a - rate_b):+.1%}",
        f"z-score:    {z:.3f}",
        f"p-value:    {p_value:.4f}",
        f"Result:     {verdict} at alpha=0.05",
    ]
    return "\n".join(lines)


# --- decompose a drop by dimension ---

def investigate_drop(
    before: dict[str, float],
    after: dict[str, float],
    metric_name: str = "metric",
) -> str:
    """
    Given before/after totals keyed by a dimension (e.g. region or plan tier),
    compute the absolute and percentage change per segment and rank them from
    largest drop to largest gain.

    This answers "where did the change come from?" rather than just "how much
    did the total change?"

    Args:
        before:      {dimension_value: metric_total} for the earlier period
        after:       {dimension_value: metric_total} for the later period
        metric_name: used in the output header (e.g. "MRR", "churn count")
    """
    all_keys = sorted(set(before) | set(after))

    if not all_keys:
        return "No data provided."

    rows = []
    for key in all_keys:
        b = before.get(key, 0.0)
        a = after.get(key, 0.0)
        delta = a - b
        pct = ((delta / b) * 100) if b != 0 else float("nan")
        rows.append((key, b, a, delta, pct))

    # Largest drop first
    rows.sort(key=lambda r: r[3])

    total_before = sum(before.values())
    total_after = sum(after.values())
    total_delta = total_after - total_before

    lines = [
        f"{metric_name} change: {total_before:,.0f} -> {total_after:,.0f} "
        f"({total_delta:+,.0f})",
        "",
        f"{'Segment':<20} {'Before':>12} {'After':>12} {'Change':>10} {'%':>8}",
        "-" * 66,
    ]

    for key, b, a, delta, pct in rows:
        pct_str = f"{pct:+.1f}%" if not math.isnan(pct) else "  n/a"
        lines.append(
            f"{str(key):<20} {b:>12,.0f} {a:>12,.0f} {delta:>+10,.0f} {pct_str:>8}"
        )

    return "\n".join(lines)
