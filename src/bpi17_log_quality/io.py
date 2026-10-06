"""XES input and output helpers."""

from pathlib import Path

import pandas as pd
import pm4py

REQUIRED_COLUMNS = {"case:concept:name", "concept:name", "time:timestamp"}


def read_xes(path: str | Path) -> pd.DataFrame:
    """Read an XES event log and validate the columns used by this project."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Event log not found: {source}")

    frame = pm4py.read_xes(str(source), return_dataframe=True)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"XES log is missing required columns: {names}")
    return frame


def write_xes(frame: pd.DataFrame, path: str | Path) -> None:
    """Write an event-log DataFrame as XES, creating its parent directory."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pm4py.write_xes(frame, str(destination))

