"""Command-line interface for the log-quality workflow."""

import argparse
import json
from pathlib import Path

from .io import read_xes, write_xes
from .metrics import profile_log
from .noise import inject_noise
from .repair import repair_log


def _write_json(path: str | None, value: dict) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True)
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bpi17-quality",
        description="Profile, corrupt, and repair common BPI17 event-log noise.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    corrupt = commands.add_parser(
        "corrupt", help="inject deterministic synthetic noise"
    )
    corrupt.add_argument("--input", required=True, help="source XES file")
    corrupt.add_argument("--output", required=True, help="destination XES file")
    corrupt.add_argument("--label-rate", type=float, default=0.01)
    corrupt.add_argument("--timestamp-rate", type=float, default=0.01)
    corrupt.add_argument("--seed", type=int, default=42)

    repair = commands.add_parser("repair", help="repair timestamps and event labels")
    repair.add_argument("--input", required=True, help="noisy XES file")
    repair.add_argument("--output", required=True, help="destination XES file")
    repair.add_argument("--report", help="optional JSON report path")

    profile = commands.add_parser("profile", help="print an event-log quality profile")
    profile.add_argument("--input", required=True, help="source XES file")
    profile.add_argument("--report", help="optional JSON report path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    frame = read_xes(args.input)

    if args.command == "corrupt":
        noised, counts = inject_noise(
            frame,
            label_rate=args.label_rate,
            timestamp_rate=args.timestamp_rate,
            seed=args.seed,
        )
        write_xes(noised, args.output)
        _write_json(None, {"input": args.input, "output": args.output, **counts})
        return

    if args.command == "repair":
        repaired, counts = repair_log(frame)
        write_xes(repaired, args.output)
        report = {
            "input": args.input,
            "output": args.output,
            "before": profile_log(frame),
            "after": profile_log(repaired),
            **counts,
        }
        _write_json(args.report, report)
        return

    report = {"input": args.input, "profile": profile_log(frame)}
    _write_json(args.report, report)


if __name__ == "__main__":
    main()

