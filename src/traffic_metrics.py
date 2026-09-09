from __future__ import annotations

from collections.abc import Mapping, Sequence


def aggregate_metric_totals(
    rows: Sequence[Mapping[str, object]],
    metric_names: Sequence[str],
    provider_totals: Mapping[str, object] | None,
) -> dict[str, object]:
    """Return trustworthy GA4 totals when the API omits its totals block.

    Provider totals always win. A dimensionless GA4 response contains one
    already-aggregated row, so averages and ratios are safe there. Multiple
    dimension rows are never summed: distinct users and truncated reports make
    such reconstructed values unsafe even for apparently additive metrics.
    """
    totals = dict(provider_totals or {})
    if len(rows) == 1:
        row = rows[0]
        for name in metric_names:
            if name not in totals and name in row:
                totals[name] = row[name]
        return totals

    return totals
