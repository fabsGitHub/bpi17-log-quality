# Methodology and limits

This portfolio rework focuses on two data-quality patterns documented as the
author's contribution in the original university project: timestamp anomalies
and activity labels polluted with a numeric event-ID suffix.

## Noise generation

The `corrupt` command uses a seeded NumPy generator, so the selected rows and
generated variants are reproducible for the same input and options. It injects
three timestamp variants (unparseable text, slash-delimited dates, and
day/month-swapped dates where the calendar values permit it) and appends a
numeric identifier to selected activity labels. It does not modify the source
file.

## Repairs

Activity-label repair removes only a trailing `: <digits>` suffix. Timestamp
repair normalizes slash separators, parses timestamps in UTC, considers
day/month swaps only for ambiguous dates, and accepts a swap only when it
reduces backwards transitions in the input order for that case. Remaining
missing timestamps are interpolated by row position between available values
within a case. A case with no valid timestamp remains missing.

## Limitations

These are transparent heuristics for the synthetic corruption patterns in this
project, not general-purpose data repair guarantees. Event order is taken from
the input file. Real logs may be out of order, contain legitimate concurrent
events, use locale-specific date formats, or violate the interpolation
assumption. Review the generated JSON profile and domain context before using a
repaired log for analysis. No benchmark results are claimed in this repository.

