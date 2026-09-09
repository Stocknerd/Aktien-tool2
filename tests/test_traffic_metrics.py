from src.traffic_metrics import aggregate_metric_totals


def test_aggregate_metric_totals_does_not_invent_totals_from_dimension_rows():
    rows = [
        {"sessions": 11, "totalUsers": 10, "engagementRate": 0.5},
        {"sessions": 4, "totalUsers": 4, "engagementRate": 0.25},
    ]

    totals = aggregate_metric_totals(
        rows,
        ["sessions", "totalUsers", "engagementRate"],
        {},
    )

    assert totals == {}


def test_aggregate_metric_totals_preserves_provider_totals():
    rows = [{"sessions": 11}]

    totals = aggregate_metric_totals(rows, ["sessions"], {"sessions": 99})

    assert totals == {"sessions": 99}


def test_aggregate_metric_totals_uses_single_dimensionless_row_for_rates():
    rows = [{"sessions": 11, "engagementRate": 0.625}]

    totals = aggregate_metric_totals(rows, ["sessions", "engagementRate"], {})

    assert totals == {"sessions": 11, "engagementRate": 0.625}
