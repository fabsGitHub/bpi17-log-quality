"""Conservative repairs for corrupted timestamps and activity labels."""

import re

import numpy as np
import pandas as pd

_EVENT_ID_SUFFIX = re.compile(r":\s*\d+$")


def repair_activity_labels(
    frame: pd.DataFrame, activity_column: str = "concept:name"
) -> tuple[pd.DataFrame, int]:
    """Remove a trailing numeric event-ID suffix while preserving missing labels."""
    if activity_column not in frame:
        raise ValueError(f"Missing activity column: {activity_column}")

    result = frame.copy()
    labels = result[activity_column].astype("string")
    repaired = labels.str.replace(_EVENT_ID_SUFFIX, "", regex=True)
    changed = int((labels.notna() & labels.ne(repaired)).sum())
    result[activity_column] = repaired
    return result, changed


def _timeline_cost(values: pd.Series) -> tuple[int, float]:
    valid = values.dropna()
    if len(valid) < 2:
        return 0, 0.0
    differences = valid.diff().dt.total_seconds().dropna()
    backwards = differences[differences < 0]
    return len(backwards), float(backwards.abs().sum())


def _swap_day_month(value):
    if pd.isna(value) or value.day > 12:
        return None
    try:
        return value.replace(day=value.month, month=value.day)
    except ValueError:
        return None


def repair_timestamps(
    frame: pd.DataFrame,
    timestamp_column: str = "time:timestamp",
    case_column: str = "case:concept:name",
) -> tuple[pd.DataFrame, int]:
    """Parse timestamps, fix clear day/month inversions, and interpolate gaps.

    The input row order is treated as the event order within each case. A
    day/month swap is accepted only when it reduces backwards transitions.
    Missing timestamps are interpolated by row position within their case; cases
    with no valid timestamp remain missing.
    """
    missing = {timestamp_column, case_column}.difference(frame.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"Missing columns required for timestamp repair: {names}")

    result = frame.copy()
    original = pd.to_datetime(
        result[timestamp_column].astype("string").str.replace("/", "-", regex=False),
        errors="coerce",
        utc=True,
        format="mixed",
    ).reset_index(drop=True)
    parsed_values = original.copy()
    case_values = result[case_column].reset_index(drop=True)
    positions = pd.DataFrame({"case": case_values})

    for _, group in positions.groupby("case", dropna=False, sort=False):
        indices = group.index.to_list()
        series = parsed_values.iloc[indices].copy()
        current_cost = _timeline_cost(series)
        for _ in range(len(series)):
            best_position = None
            best_value = None
            best_cost = current_cost
            for local_position, value in enumerate(series):
                candidate = _swap_day_month(value)
                if candidate is None:
                    continue
                trial = series.copy()
                trial.iloc[local_position] = candidate
                trial_cost = _timeline_cost(trial)
                if trial_cost < best_cost:
                    best_position = local_position
                    best_value = candidate
                    best_cost = trial_cost
            if best_position is None:
                break
            series.iloc[best_position] = best_value
            current_cost = best_cost
        parsed_values.iloc[indices] = series

    # Interpolate microseconds rather than nanoseconds to keep values precise
    # when represented as floating point numbers during interpolation.
    integer_values = (parsed_values.astype("int64") // 1_000).astype("float64")
    integer_values = integer_values.where(parsed_values.notna(), np.nan)
    interpolated = integer_values.groupby(
        case_values, dropna=False, sort=False
    ).transform(lambda values: values.interpolate(limit_direction="both"))
    repaired = pd.to_datetime(
        interpolated.round().astype("Int64"), unit="us", utc=True
    )

    sentinel = pd.Timestamp.min.tz_localize("UTC")
    changed = int(
        (
            original.fillna(sentinel).ne(repaired.fillna(sentinel))
        ).sum()
    )
    result[timestamp_column] = pd.Series(repaired.array, index=result.index)
    return result, changed


def repair_log(
    frame: pd.DataFrame,
    timestamp_column: str = "time:timestamp",
    activity_column: str = "concept:name",
    case_column: str = "case:concept:name",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply both repairs and report how many values each changed."""
    result, labels_changed = repair_activity_labels(frame, activity_column)
    result, timestamps_changed = repair_timestamps(
        result, timestamp_column, case_column
    )
    return result, {
        "activity_labels_repaired": labels_changed,
        "timestamps_repaired": timestamps_changed,
    }

