"""Entry point for downloading and storing event data with progress feedback."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping, Sequence

import db

from rich.console import Console
from rich.progress import (
	BarColumn,
	Progress,
	SpinnerColumn,
	TextColumn,
	TimeElapsedColumn,
	TimeRemainingColumn,
)

import downloader

console = Console()


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Download and store wrestling events")
	parser.add_argument(
		"--mode",
		choices=("events", "teams"),
		default="events",
		help="Select whether to download events (default) or teams.",
	)
	parser.add_argument(
		"events_file",
		type=Path,
		nargs="?",
		default=Path("events/2022.json"),
		help="Path to the JSON file containing events metadata.",
	)
	parser.add_argument(
		"--teams-file",
		type=Path,
		default=Path("alignments/miaa.json"),
		help="Path to the JSON file containing team alignment metadata.",
	)
	return parser.parse_args()


def load_events(path: Path) -> Sequence[Mapping]:
	if not path.exists():
		raise FileNotFoundError(f"Events file not found: {path}")
	with path.open("r", encoding="utf-8") as fh:
		data = json.load(fh)
		if isinstance(data, list):
			return list(reversed(data))
			
		return list(reversed(data.get("data", [])))  # type: ignore[call-arg]


def load_team_ids(path: Path) -> Sequence[str]:
	if not path.exists():
		raise FileNotFoundError(f"Teams file not found: {path}")
	with path.open("r", encoding="utf-8") as fh:
		data = json.load(fh)

	teams: list[str] = []
	seen: set[str] = set()

	for division in data.get("divisions", []):
		for section in division.get("sections", []):
			for team_id in section.get("teams", []):
				if not isinstance(team_id, str):
					continue
				if team_id in seen:
					continue
				seen.add(team_id)
				teams.append(team_id)

	return teams


def process_events(events: Sequence[Mapping]) -> None:
	if not events:
		console.print("[yellow]No events to process.")
		return

	conn = db.get_connection()

	with Progress(
		SpinnerColumn(),
		TextColumn("{task.description}"),
		BarColumn(bar_width=None),
		TextColumn("{task.completed}/{task.total}"),
		TimeElapsedColumn(),
		TimeRemainingColumn(),
		console=console,
	) as progress:
		download_task = progress.add_task("Downloading events", total=len(events))
		store_task = progress.add_task("Storing events", total=len(events))
		event_progress_task = progress.add_task("Event progress", total=100, visible=False)

		for event in events:
			event_id = event.get("guid")
			if not event_id:
				progress.console.print("[red]Skipping event without ID")
				progress.advance(download_task)
				progress.advance(store_task)
				continue
			
			event_name = (
				event.get("name")
				or event.get("attributes", {}).get("name")
				or "Unnamed Event"
			)
			if not event.get("hasBrackets", False):
				#progress.console.print(f"[yellow]Skipping event {event_name} without brackets")
				progress.advance(download_task)
				progress.advance(store_task)
				continue

			if db.event_exists(db.get_connection(), event_id):
				#progress.console.print(f"[blue]Event {event_name} already exists in the database, skipping.")
				progress.advance(download_task)
				progress.advance(store_task)
				continue

			progress.update(download_task, description=f"Downloading {event_name}")
			progress.update(
				event_progress_task,
				description=f"{event_name} pages",
				completed=0,
				total=100,
				visible=True,
			)

			def _update_event_progress(fraction: float) -> None:
				progress.update(
					event_progress_task,
					completed=int(max(0.0, min(1.0, fraction)) * 100),
				)

			try:
				downloader.store_event(str(event_id), progress_callback=_update_event_progress)
			finally:
				progress.update(event_progress_task, completed=100, visible=False)

			progress.advance(download_task)

			progress.update(store_task, description=f"Stored {event_name}")
			progress.advance(store_task)

	console.print("[green]Finished downloading and storing all events!", highlight=False)


def process_teams(team_ids: Sequence[str]) -> None:
	if not team_ids:
		console.print("[yellow]No teams to process.")
		return

	conn = db.get_connection()

	with Progress(
		SpinnerColumn(),
		TextColumn("{task.description}"),
		BarColumn(bar_width=None),
		TextColumn("{task.completed}/{task.total}"),
		TimeElapsedColumn(),
		TimeRemainingColumn(),
		console=console,
	) as progress:
		download_task = progress.add_task("Downloading teams", total=len(team_ids))
		store_task = progress.add_task("Storing teams", total=len(team_ids))
		team_progress_task = progress.add_task("Team progress", total=100, visible=False)

		for team_id in team_ids:
			team_label = team_id
			if db.is_team_crawled(conn, team_id):
				progress.console.print(
					f"[blue]Team {team_label} already crawled, skipping."
				)
				progress.advance(download_task)
				progress.advance(store_task)
				continue

			progress.update(download_task, description=f"Downloading team {team_label}")
			progress.update(
				team_progress_task,
				description=f"{team_label} pages",
				completed=0,
				total=100,
				visible=True,
			)

			def _update_label(new_label: str) -> None:
				nonlocal team_label
				team_label = new_label or team_label
				progress.update(download_task, description=f"Downloading team {team_label}")
				progress.update(team_progress_task, description=f"{team_label} pages")

			def _update_team_progress(fraction: float) -> None:
				progress.update(
					team_progress_task,
					completed=int(max(0.0, min(1.0, fraction)) * 100),
				)

			try:
				downloader.store_team(
					team_id,
					progress_callback=_update_team_progress,
					name_callback=_update_label,
				)
			finally:
				progress.update(team_progress_task, completed=100, visible=False)

			progress.advance(download_task)

			progress.update(store_task, description=f"Stored team {team_label}")
			progress.advance(store_task)

	console.print("[green]Finished downloading and storing all teams!", highlight=False)


def main() -> None:
	args = parse_args()
	try:
		if args.mode == "events":
			process_events(load_events(args.events_file))
		else:
			process_teams(load_team_ids(args.teams_file))
	except FileNotFoundError as exc:
		console.print(f"[red]{exc}")
		return


if __name__ == "__main__":
	main()
