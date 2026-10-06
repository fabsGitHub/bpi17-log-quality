# BPI17 Log Quality

[![CI](https://github.com/fabsGitHub/bpi17-log-quality/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/fabsGitHub/bpi17-log-quality/actions/workflows/ci.yml)

A reproducible Python workflow for injecting and repairing two common event-log
quality issues: timestamp anomalies and activity labels polluted with numeric
event IDs. The project is based on contributions to the BPI Challenge 2017
university project and is intentionally scoped to the author's documented
work.

## What it does

- Creates deterministic synthetic timestamp and label noise from an XES log.
- Repairs parseable date-format variants, conservative day/month inversions,
  missing timestamps within a case, and trailing numeric label suffixes.
- Profiles a log before and after repair with event, case, activity, timestamp,
  ordering, and duplicate-row counts.
- Keeps source data and generated event logs out of Git.

## Project layout

```text
data/                     Dataset instructions; local logs are ignored
docs/                     Methodology and limitations
src/bpi17_log_quality/    XES I/O, noise generation, repair, metrics, and CLI
tests/                    Dataset-independent unit tests
.github/workflows/ci.yml  Automated quality checks
```

## Requirements

- Python 3.10 or newer
- The BPI Challenge 2017 XES log, obtained from its official
  [4TU.ResearchData record](https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b)

The dataset is not included. See [`data/README.md`](data/README.md) for its
citation and local setup. Keep the source log unchanged and follow the dataset
record's terms of use.

## Install

```bash
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Validate changes

Install the optional development tools and run the same checks used by CI:

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest -q
python -m compileall -q src tests
bpi17-quality --help
```

GitHub Actions runs these checks on Python 3.10 and 3.12 for pull requests and
updates to `main`. The tests use small synthetic event rows; they do not
download or require the BPI Challenge dataset.

## Run the workflow

Place the XES file at `data/raw/BPI_Challenge_2017.xes`, then run:

```bash
# Inspect the source log
bpi17-quality profile --input data/raw/BPI_Challenge_2017.xes

# Make deterministic synthetic variants
bpi17-quality corrupt \\
  --input data/raw/BPI_Challenge_2017.xes \\
  --output data/processed/noisy.xes \\
  --label-rate 0.01 \\
  --timestamp-rate 0.01 \\
  --seed 42

# Repair the generated log and save an aggregate before/after report
bpi17-quality repair \\
  --input data/processed/noisy.xes \\
  --output data/processed/repaired.xes \\
  --report reports/repair-summary.json
```

The report contains aggregate metrics and changed-value counts; it does not
export case-level records. Commands accept explicit paths, so the log does not
need to be copied into a fixed project location.

## Method and limitations

The timestamp repair uses input order within each case as a heuristic signal. It
only accepts a day/month swap when it reduces backwards transitions. Missing
values are interpolated by row position between known timestamps. Those choices
fit the synthetic patterns this project demonstrates, but they are not safe
assumptions for every real process log. Review
[`docs/methodology.md`](docs/methodology.md) before applying the repairs to
another dataset.

No discovery, conformance-checking, or performance-analysis results are claimed
here. The public version focuses on reproducible data-quality preparation.

## Project origin and dataset attribution

This is a focused rework of timestamp and activity-label contributions from a
university team project. Other team members' modules, notebooks, reports, and
the original commit history are not included. See [`NOTICE.md`](NOTICE.md) for
the scope and attribution note and [`CITATION.cff`](CITATION.cff) for a
software citation.

The BPI Challenge 2017 event log is a separate 4TU.ResearchData dataset. Its
full citation and source are listed in [`data/README.md`](data/README.md); no
event data is redistributed by this repository.
