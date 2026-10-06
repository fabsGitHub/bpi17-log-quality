"""Unit tests for deterministic, dataset-independent log-quality behavior."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal

from bpi17_log_quality.metrics import profile_log
from bpi17_log_quality.noise import inject_noise
from bpi17_log_quality.repair import repair_activity_labels, repair_timestamps


def test_repair_activity_labels_removes_only_numeric_suffixes_without_mutating_input():
    frame = pd.DataFrame(
        {
            "concept:name": pd.Series(
                [
                    "Approve application: 17",
                    "Call applicant",
                    pd.NA,
                    "Review: urgent: 203",
                ],
                dtype="string",
            )
        }
    )
    original = frame.copy(deep=True)

    repaired, changed = repair_activity_labels(frame)

    assert changed == 2
    assert_series_equal(
        repaired["concept:name"],
        pd.Series(
            ["Approve application", "Call applicant", pd.NA, "Review: urgent"],
            dtype="string",
            name="concept:name",
        ),
    )
    assert_frame_equal(frame, original)


def test_repair_timestamps_corrects_inversion_interpolates_and_preserves_empty_cases():
    frame = pd.DataFrame(
        {
            "case:concept:name": [
                "case-a",
                "case-a",
                "case-a",
                "case-a",
                "case-b",
                "case-b",
            ],
            "time:timestamp": [
                "2020-03-15",
                "2020-02-04",
                "not-a-timestamp",
                "2020-04-03",
                "not-a-timestamp",
                None,
            ],
        }
    )
    original = frame.copy(deep=True)

    repaired, changed = repair_timestamps(frame)

    expected = pd.Series(
        pd.to_datetime(
            [
                "2020-03-15",
                "2020-04-02",
                "2020-04-02 12:00:00",
                "2020-04-03",
                None,
                None,
            ],
            utc=True,
        ),
        name="time:timestamp",
    )
    assert changed == 2
    assert_series_equal(repaired["time:timestamp"], expected)
    assert repaired["time:timestamp"].iloc[4:].isna().all()
    assert_frame_equal(frame, original)


def test_noise_injection_is_seeded_reports_counts_and_leaves_input_unchanged():
    frame = pd.DataFrame(
        {
            "concept:name": [f"Activity {index}" for index in range(6)],
            "EventID": [f"task_{index:06d}" for index in range(6)],
            "time:timestamp": pd.date_range(
                "2024-01-01", periods=6, freq="h", tz="UTC"
            ).astype(str),
        }
    )
    original = frame.copy(deep=True)

    first, counts = inject_noise(
        frame, label_rate=0.5, timestamp_rate=0.5, seed=7
    )
    second, repeated_counts = inject_noise(
        frame, label_rate=0.5, timestamp_rate=0.5, seed=7
    )

    assert_frame_equal(first, second)
    assert counts == {
        "activity_labels_changed": 3,
        "timestamps_changed": 3,
    }
    assert repeated_counts == counts
    assert first["concept:name"].str.endswith(
        tuple(f": {index:06d}" for index in range(6))
    ).sum() == 3
    assert_frame_equal(frame, original)


def test_noise_injection_rejects_rates_outside_zero_to_one():
    frame = pd.DataFrame({"concept:name": ["A"], "time:timestamp": ["2024-01-01"]})

    with pytest.raises(ValueError, match="between 0 and 1"):
        inject_noise(frame, label_rate=1.1)


def test_profile_reports_missing_invalid_and_out_of_order_values():
    frame = pd.DataFrame(
        {
            "case:concept:name": ["case-a", "case-a", "case-b", "case-b"],
            "concept:name": ["A", "A", "B", None],
            "time:timestamp": [
                "2024-01-01",
                "2023-12-31",
                "not-a-timestamp",
                None,
            ],
        }
    )

    assert profile_log(frame) == {
        "events": 4,
        "cases": 2,
        "activities": 2,
        "missing_case_ids": 0,
        "missing_activity_labels": 1,
        "unparseable_timestamps": 1,
        "missing_timestamps": 1,
        "out_of_order_transitions": 1,
        "duplicate_case_activity_timestamp_rows": 0,
    }

