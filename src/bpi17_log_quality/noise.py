"""Deterministic injectors for timestamp and activity-label noise."""

import numpy as np
import pandas as pd


def _sample_positions(valid_positions: np.ndarray, rate: float, rng) -> np.ndarray:
    if not 0 <= rate <= 1:
        raise ValueError("Noise rates must be between 0 and 1.")
    if not len(valid_positions) or rate == 0:
        return np.array([], dtype=int)
    count = min(len(valid_positions), max(1, round(len(valid_positions) * rate)))
    return np.sort(rng.choice(valid_positions, size=count, replace=False))


def inject_label_id_noise(
    frame: pd.DataFrame,
    rate: float = 0.01,
    seed: int = 42,
    activity_column: str = "concept:name",
    event_id_column: str = "EventID",
) -> tuple[pd.DataFrame, int]:
    """Append a reproducible event-ID suffix to a sample of activity labels."""
    if activity_column not in frame:
        raise ValueError(f"Missing activity column: {activity_column}")

    result = frame.copy()
    labels = result[activity_column]
    positions = np.flatnonzero(labels.notna().to_numpy())
    selected = _sample_positions(positions, rate, np.random.default_rng(seed))
    if not len(selected):
        return result, 0

    event_ids = result[event_id_column] if event_id_column in result else None
    for position in selected:
        label = str(labels.iloc[position])
        if event_ids is not None and pd.notna(event_ids.iloc[position]):
            suffix = str(event_ids.iloc[position]).rsplit("_", maxsplit=1)[-1]
        else:
            suffix = str(position + 1)
        result.iat[position, result.columns.get_loc(activity_column)] = f"{label}: {suffix}"
    return result, len(selected)


def inject_timestamp_noise(
    frame: pd.DataFrame,
    rate: float = 0.01,
    seed: int = 43,
    timestamp_column: str = "time:timestamp",
) -> tuple[pd.DataFrame, int]:
    """Inject parse failures and date-format variants into a sample of timestamps."""
    if timestamp_column not in frame:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")

    result = frame.copy()
    parsed = pd.to_datetime(
        result[timestamp_column], errors="coerce", utc=True, format="mixed"
    )
    positions = np.flatnonzero(parsed.notna().to_numpy())
    rng = np.random.default_rng(seed)
    selected = _sample_positions(positions, rate, rng)
    if not len(selected):
        return result, 0

    for position in selected:
        timestamp = parsed.iloc[position]
        pattern = int(rng.integers(0, 3))
        if pattern == 0:
            value = "not-a-timestamp"
        elif pattern == 1:
            value = timestamp.strftime("%Y/%m/%d %H:%M:%S%z")
        elif timestamp.day <= 12:
            value = timestamp.strftime("%Y-%d-%m %H:%M:%S%z")
        else:
            value = "not-a-timestamp"
        result.iat[position, result.columns.get_loc(timestamp_column)] = value
    return result, len(selected)


def inject_noise(
    frame: pd.DataFrame,
    *,
    label_rate: float = 0.01,
    timestamp_rate: float = 0.01,
    seed: int = 42,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Apply both supported noise patterns and return their changed-row counts."""
    noised, label_count = inject_label_id_noise(frame, label_rate, seed)
    noised, timestamp_count = inject_timestamp_noise(
        noised, timestamp_rate, seed + 1
    )
    return noised, {
        "activity_labels_changed": label_count,
        "timestamps_changed": timestamp_count,
    }

