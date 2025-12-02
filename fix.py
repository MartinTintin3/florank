"""Utility script to backfill match dates using their events."""

try:
	from rich.console import Console  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
	Console = None  # type: ignore

import db


def _print(message: str, style: str | None = None) -> None:
	if Console is not None:
		Console().print(message if style is None else f"[{style}]{message}")
	else:
		print(message)


def backfill_matches() -> int:
	conn = db.get_connection()
	return db.backfill_match_dates(conn)


def main() -> None:
	try:
		updated = backfill_matches()
		if updated:
			_print(f"Updated {updated} matches with missing dates.", "green")
		else:
			_print("No matches required backfilling.", "yellow")
	except Exception as exc:  # pragma: no cover - simple CLI script
		_print(f"Failed to backfill matches: {exc}", "red")
		raise


if __name__ == "__main__":
	main()
