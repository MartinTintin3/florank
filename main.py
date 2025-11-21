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
		"events_file",
		type=Path,
		nargs="?",
		default=Path("events/2022.json"),
		help="Path to the JSON file containing events metadata.",
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


def process_events(events: Sequence[Mapping]) -> None:
	if not events:
		console.print("[yellow]No events to process.")
		return

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
				progress.console.print(f"[yellow]Skipping event {event_name} without brackets")
				progress.advance(download_task)
				progress.advance(store_task)
				continue

			if db.event_exists(db.get_connection(), event_id):
				progress.console.print(f"[blue]Event {event_name} already exists in the database, skipping.")
				progress.advance(download_task)
				progress.advance(store_task)
				continue

			progress.update(download_task, description=f"Downloading {event_name}")
			downloader.store_event(str(event_id))
			progress.advance(download_task)

			progress.update(store_task, description=f"Stored {event_name}")
			progress.advance(store_task)

	console.print("[green]Finished downloading and storing all events!", highlight=False)


def main() -> None:
	args = parse_args()
	try:
		events = load_events(args.events_file)
	except FileNotFoundError as exc:
		console.print(f"[red]{exc}")
		return
	process_events(events)


if __name__ == "__main__":
	main()