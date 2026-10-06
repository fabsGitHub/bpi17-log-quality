"""Small, explainable event-log quality summaries."""

import pandas as pd


def profile_log(
    frame: pd.DataFrame,
    timestamp_column: str = "time:timestamp",
    activity_column: str = "concept:name",
    case_column: str = "case:concept:name",
) -> dict[str, int]:
    """Return row counts, parse issues, and trace-order anomalies."""
    required = {timestamp_column, activity_column, case_column}
    missing = required.difference(frame.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Missing columns required for profiling: {names}")

    parsed = pd.to_datetime(
        frame[timestamp_column], errors="coerce", utc=True, format="mixed"
    )
    ordered = pd.DataFrame(
        {
            "case": frame[case_column].reset_index(drop=True),
            "time": parsed.reset_index(drop=True),
        }
    )
    deltas = ordered.groupby("case", dropna=False, sort=False)["time"].diff()
    labels = frame[activity_column]
    duplicate_count = int(
        frame.duplicated([case_column, activity_column, timestamp_column]).sum()
    )
    return {
        "events": int(len(frame)),
        "cases": int(frame[case_column].nunique(dropna=True)),
        "activities": int(labels.nunique(dropna=True)),
        "missing_case_ids": int(frame[case_column].isna().sum()),
        "missing_activity_labels": int(labels.isna().sum()),
        "unparseable_timestamps": int(
            (frame[timestamp_column].notna() & parsed.isna()).sum()
        ),
        "missing_timestamps": int(frame[timestamp_column].isna().sum()),
        "out_of_order_transitions": int((deltas < pd.Timedelta(0)).sum()),
        "duplicate_case_activity_timestamp_rows": duplicate_count,
    }

