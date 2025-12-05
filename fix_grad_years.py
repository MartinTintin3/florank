"""Fill missing gradYear values using earliest postseason participation."""

from __future__ import annotations

import argparse

import db
import utils
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn


console = Console()


def load_top_leaderboard_ids(path: Path, top_n: int) -> set[str]:
	if not path.exists():
		console.print(f"[red]Leaderboard file not found: {path}")
		return set()
	try:
		import json
		with path.open("r", encoding="utf-8") as fh:
			data = json.load(fh)
	except Exception as exc:  # noqa: BLE001
		console.print(f"[red]Failed to read leaderboard: {exc}")
		return set()
	weights = data.get("weights") if isinstance(data, dict) else None
	if not isinstance(weights, dict):
		console.print("[red]Leaderboard JSON missing 'weights' object.")
		return set()
	selected: set[str] = set()
	for entries in weights.values():
		if not isinstance(entries, list):
			continue
		for entry in entries[:top_n]:
			if isinstance(entry, dict) and isinstance(entry.get("id"), str):
				selected.add(entry["id"])
	return selected


def fix_grad_years(dry_run: bool = False, only_ids: set[str] | None = None) -> int:
	conn = db.get_connection()
	cur = conn.cursor()
	cur.execute("SELECT id FROM wrestlers WHERE gradYear IS NULL")
	wrestlers = [row[0] for row in cur.fetchall() if not only_ids or row[0] in only_ids]

	if not wrestlers:
		console.print("[green]No wrestlers with missing gradYear.")
		return 0

	updated = 0
	with Progress(
		SpinnerColumn(),
		TextColumn("{task.description}"),
		BarColumn(bar_width=None),
		TextColumn("{task.completed}/{task.total}"),
		TimeElapsedColumn(),
		TimeRemainingColumn(),
		console=console,
	) as progress:
		task = progress.add_task("Inferring grad years", total=len(wrestlers))
		for wrestler_id in wrestlers:
			grad_year = utils.infer_grad_year_from_post(wrestler_id)
			if grad_year is not None:
				updated += 1
				if not dry_run:
					db.update_wrestler(conn, wrestler_id=wrestler_id, gradYear=grad_year)
			progress.advance(task)

	return updated


def main() -> None:
	parser = argparse.ArgumentParser(description="Backfill missing gradYear using postseason participation.")
	parser.add_argument("--dry-run", action="store_true", help="Show how many would be updated without writing.")
	parser.add_argument("--leaderboard", type=Path, help="Limit updates to wrestlers in this leaderboard JSON.")
	parser.add_argument("--top-n", type=int, default=10, help="Top N per weight to consider from leaderboard.")
	args = parser.parse_args()

	limit_ids: set[str] | None = None
	if args.leaderboard:
		limit_ids = load_top_leaderboard_ids(args.leaderboard, args.top_n)
		if limit_ids:
			console.print(f"[blue]Restricting to {len(limit_ids)} wrestlers from leaderboard top {args.top_n} per weight.")
		else:
			console.print("[yellow]No wrestlers collected from leaderboard; nothing to update.")
			return

	updated = fix_grad_years(dry_run=args.dry_run, only_ids=limit_ids)
	if args.dry_run:
		console.print(f"[yellow][dry-run][/yellow] Would update {updated} wrestlers.")
	else:
		console.print(f"[green]Updated {updated} wrestlers.")


if __name__ == "__main__":
	main()
