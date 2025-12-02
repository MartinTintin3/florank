"""Export matches for a wrestler to CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable

import utils

DEFAULT_WRESTLER_ID = "064ad7f4-8d16-4dd2-94b1-1dd1c45c3832"
COLUMN_NAMES = [
	"type",
	"opponent",
	"result",
	"event",
	"date",
	"weightClass",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Export wrestler matches to CSV")
	parser.add_argument(
		"wrestler_id",
		nargs="?",
		default=DEFAULT_WRESTLER_ID,
		help="Wrestler ID to export",
	)
	parser.add_argument(
		"--output",
		type=Path,
		help="Destination CSV file (defaults to wrestler_matches_<id>.csv)",
	)
	return parser.parse_args()


def format_result(result: str | None, win_type: str | None) -> str:
	parts = [part for part in (result, win_type) if part]
	return " - ".join(parts)


def rows_for_csv(matches: Iterable[dict]) -> list[dict[str, str]]:
	rows: list[dict[str, str]] = []
	for match in matches:
		rows.append(
			{
				"type": match.get("type", ""),
				"opponent": match.get("opponentName") or "Unknown",
				"result": format_result(match.get("result"), match.get("winType")),
				"event": match.get("eventName") or "",
				"date": match.get("date") or "",
				"weightClass": match.get("weightClass") or "",
			}
		)
	return rows


def export_matches(wrestler_id: str, output_path: Path) -> Path:
	matches = utils.get_wrestler_matches(wrestler_id)
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", newline="", encoding="utf-8") as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=COLUMN_NAMES)
		writer.writeheader()
		writer.writerows(rows_for_csv(matches))
	return output_path


def main() -> None:
	args = parse_args()
	output = args.output or Path(f"wrestler_matches_{args.wrestler_id}.csv")
	path = export_matches(args.wrestler_id, output)
	print(f"Exported matches for {args.wrestler_id} to {path}")


if __name__ == "__main__":
	main()