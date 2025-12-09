import api_types
import json
import calendar
from datetime import datetime, timezone, timedelta
from typing import Iterable, Iterator, Tuple

import db

def next_link(data: api_types.GenericResponse, current_url: str) -> str | None:
	if "links" in data and "next" in data["links"]:
		next_url = data["links"]["next"]
		if next_url is not current_url:
			return next_url
	return None

def get_school_year(date: datetime) -> int:
	if date.month > 8:
		return date.year
	else:
		return date.year - 1

def calc_cur_grade(past_grade: int, past_date: str, cur_date: datetime) -> int | None:
	past_school_year = 0

	d = datetime.strptime(past_date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
		
	past_school_year = get_school_year(d)
	cur_school_year = get_school_year(cur_date)
	return past_grade + cur_school_year - past_school_year

def calc_grad_year(grade: int, as_of: datetime) -> int:
	school_year = get_school_year(as_of)
	years_left = 12 - grade
	return school_year + years_left + 1

def get_divisions() -> list[int]:
	with open("./alignments/miaa.json", "r", encoding="utf-8") as f:
		data = json.load(f)

	divisions = []

	for d in data.get("divisions", []):
		divisions.append(d.get("division"))
	
	return divisions

def get_sections(division: int | None = None) -> list[str]:
	with open("./alignments/miaa.json", "r", encoding="utf-8") as f:
		data = json.load(f)

	sections = []

	for d in data.get("divisions", []):
		if division is not None and d.get("division") != division:
			continue

		for s in d.get("sections", []):
			sections.append(s.get("name")) # type: ignore
	
	return sections

def get_team_ids(division: int | None = None, section: str | None = None) -> list[str]:
	with open("./alignments/miaa.json", "r", encoding="utf-8") as f:
		data = json.load(f)

	teams = []

	for d in data.get("divisions", []):
		if division is not None and d.get("division") != division:
			continue

		for s in d.get("sections", []):
			if section is not None and s.get("name") != section: # type: ignore
				continue

			teams.extend(s.get("teams", [])) # type: ignore
	
	return teams


def get_team_section(team_id: str) -> Tuple[str | None, int | None]:
	"""Return (section, division) for a team id using alignment data."""
	with open("./alignments/miaa.json", "r", encoding="utf-8") as f:
		data = json.load(f)

	for d in data.get("divisions", []):
		division_num = d.get("division")
		for s in d.get("sections", []):
			section_name = s.get("name")  # type: ignore
			if team_id in (s.get("teams", []) or []):  # type: ignore
				return section_name, division_num
	return None, None


def get_team_metadata(team_ids: Iterable[str]) -> dict[str, dict]:
	"""Return mapping of teamId -> {name, section, division}."""
	ids = [t for t in team_ids if t]
	if not ids:
		return {}

	conn = db.get_connection()
	cur = conn.cursor()
	placeholders = ",".join("?" for _ in ids)
	sql = f"SELECT id, name FROM teams WHERE id IN ({placeholders})"
	cur.execute(sql, ids)
	results: dict[str, dict] = {}
	for team_id, name in cur.fetchall():
		section, division = get_team_section(team_id)
		results[team_id] = {"name": name, "section": section, "division": division}
	# Fill section/division for any missing names using alignment data.
	for team_id in ids:
		if team_id in results:
			continue
		section, division = get_team_section(team_id)
		results[team_id] = {"name": team_id, "section": section, "division": division}
	return results

def get_section(team_id: str) -> dict[str, str] | None:
	# return team's section and division
	with open("./alignments/miaa.json", "r", encoding="utf-8") as f:
		data = json.load(f)
	for d in data.get("divisions", []):
		for s in d.get("sections", []):
			if team_id in s.get("teams", []): # type: ignore
				return {
					"division": d.get("division"),
					"section": s.get("name"),
				}
	return None

def get_wrestler_matches(wrestler_id: str) -> list[dict]:
	conn = db.get_connection()
	cur = conn.cursor()

	sql = """
SELECT
  m.id,
  m.eventId,
  COALESCE(m.date, e.date) AS match_date,
  m.weightClass,
  m.topId,
  m.bottomId,
  m.winnerId,
  m.result,
  m.winType,
  e.name AS event_name,
  top_w.name AS top_name,
  bottom_w.name AS bottom_name
FROM matches AS m
LEFT JOIN events AS e ON e.id = m.eventId
LEFT JOIN wrestlers AS top_w ON top_w.id = m.topId
LEFT JOIN wrestlers AS bottom_w ON bottom_w.id = m.bottomId
WHERE m.topId = ? OR m.bottomId = ?
ORDER BY (match_date IS NULL), match_date DESC;
	"""
	cur.execute(sql, (wrestler_id, wrestler_id))
	rows = cur.fetchall()
	matches = []

	for (
		match_id,
		event_id,
		date,
		weight_class,
		top_id,
		bottom_id,
		winner_id,
		result,
		win_type,
		event_name,
		top_name,
		bottom_name,
	) in rows:
		opponent_name = bottom_name if top_id == wrestler_id else top_name
		opponent_id = bottom_id if top_id == wrestler_id else top_id
		matches.append({
			"type": "win" if winner_id == wrestler_id else "loss",
			"id": match_id,
			"date": date,
			"weightClass": weight_class,
			"opponent": {
				"id": opponent_id,
				"name": opponent_name,
			},
			"result": result,
			"winType": win_type,
			"event": {
				"id": event_id,
				"name": event_name,
			},
		})
	return matches


def get_active_wrestlers(min_wins: int = 1) -> list[str]:
	teams = get_team_ids()
	
	if not teams:
		return []

	conn = db.get_connection()
	cur = conn.cursor()

	# Calculate date 1 year ago
	one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
	date_str = one_year_ago.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

	placeholders = ",".join("?" for _ in teams)
	sql = f"""
		SELECT w.id
		FROM wrestlers w
		JOIN matches m ON w.id = m.winnerId
		WHERE w.teamId IN ({placeholders})
		AND (w.gradYear IS NULL OR w.gradYear >= 2026)
		AND m.date >= ?
		GROUP BY w.id
		HAVING COUNT(m.id) >= ?
	"""

	params = list(teams)
	params.append(date_str)
	params.append(min_wins) # type: ignore
	
	cur.execute(sql, params)
	rows = cur.fetchall()
	
	return [row[0] for row in rows]
	

def get_team_lineup(team_id: str, event_id: str) -> dict[str, tuple[str, str]]:
	conn = db.get_connection()
	cur = conn.cursor()

	sql = """
SELECT DISTINCT
  w.id,
  w.name,
  m.weightClass AS weight_class
FROM matches AS m
JOIN wrestlers AS w
  ON (m.topId = w.id OR m.bottomId = w.id)
WHERE m.eventId = ?
  AND w.teamId = ?;
	"""
	cur.execute(sql, (event_id, team_id))
	rows = cur.fetchall()

	lineup: dict[str, tuple[str, str]] = {}
	# sort by weight class
	for wrestler_id, wrestler_name, weight_class in rows:
		lineup[weight_class] = (wrestler_id, wrestler_name)
	
	return dict(sorted(lineup.items()))


def parse_date(date_str: str) -> datetime:
	"""Parse ISO date strings from the DB/API into aware datetimes."""
	value = date_str.replace("Z", "+00:00")
	try:
		result = datetime.fromisoformat(value)
		if result.tzinfo is None:
			return result.replace(tzinfo=timezone.utc)
		return result
	except ValueError:
		# Some dates may omit timezone; assume UTC.
		return datetime.fromisoformat(value.split("+")[0]).replace(tzinfo=timezone.utc)


def load_seasons(path: str = "seasons.json") -> list[dict]:
	"""Load season metadata in chronological order."""
	with open(path, "r", encoding="utf-8") as f:
		data = json.load(f)
	if not isinstance(data, list):
		return []
	return data


def month_periods(start: datetime, end: datetime) -> Iterator[tuple[datetime, datetime]]:
	"""Yield half-open [start, end) monthly periods between two dates."""
	def _add_month(d: datetime) -> datetime:
		year = d.year + (d.month // 12)
		month = 1 if d.month == 12 else d.month + 1
		day = min(d.day, calendar.monthrange(year, month)[1])
		return d.replace(year=year, month=month, day=day)

	current = start
	while current < end:
		next_month = _add_month(current)
		yield current, min(next_month, end)
		current = next_month


def get_matches_between(
	start: datetime,
	end: datetime,
	wrestler_ids: Iterable[str],
	weight_classes: set[str] | None = None,
) -> list[dict]:
	"""Fetch matches between two dates where both wrestlers are in the provided set."""
	ids = list(wrestler_ids)
	if not ids:
		return []

	conn = db.get_connection()
	cur = conn.cursor()

	date_start = start.astimezone(timezone.utc).isoformat()
	date_end = end.astimezone(timezone.utc).isoformat()

	id_placeholders = ",".join("?" for _ in ids)
	weight_clause = ""
	params: list = [date_start, date_end, *ids, *ids]

	if weight_classes:
		weight_clause = f" AND m.weightClass IN ({','.join('?' for _ in weight_classes)})"
		params.extend(weight_classes)  # type: ignore[arg-type]

	sql = f"""
SELECT
  m.id,
  COALESCE(m.date, e.date) AS match_date,
  m.weightClass,
  m.topId,
  m.bottomId,
  m.winnerId,
  m.result,
  m.winType
FROM matches AS m
LEFT JOIN events AS e ON e.id = m.eventId
WHERE match_date IS NOT NULL
  AND match_date >= ?
  AND match_date < ?
  AND m.topId IN ({id_placeholders})
  AND m.bottomId IN ({id_placeholders})
  {weight_clause}
ORDER BY match_date ASC;
	"""
	cur.execute(sql, params)

	matches = []
	for (
		match_id,
		match_date,
		weight_class,
		top_id,
		bottom_id,
		winner_id,
		result,
		win_type,
	) in cur.fetchall():
		matches.append(
			{
				"id": match_id,
				"date": parse_date(match_date),
				"weightClass": weight_class,
				"topId": top_id,
				"bottomId": bottom_id,
				"winnerId": winner_id,
				"result": result,
				"winType": win_type,
			}
		)
	return matches


def get_wrestler_names(wrestler_ids: Iterable[str]) -> dict[str, str]:
	"""Return a mapping of wrestler IDs to their stored names."""
	ids = list(wrestler_ids)
	if not ids:
		return {}

	conn = db.get_connection()
	cur = conn.cursor()

	placeholders = ",".join("?" for _ in ids)
	sql = f"SELECT id, COALESCE(name, id) FROM wrestlers WHERE id IN ({placeholders})"
	cur.execute(sql, ids)

	return {row[0]: row[1] for row in cur.fetchall()}


def get_wrestler_info(wrestler_ids: Iterable[str]) -> dict[str, dict]:
	"""Return a mapping of wrestler IDs to metadata such as name, gradYear, teamId."""
	ids = list(wrestler_ids)
	if not ids:
		return {}

	conn = db.get_connection()
	cur = conn.cursor()

	placeholders = ",".join("?" for _ in ids)
	sql = f"""
SELECT w.id,
       COALESCE(w.name, w.id) AS name,
       w.gradYear,
       w.teamId,
       t.name as teamName
FROM wrestlers w
LEFT JOIN teams t ON t.id = w.teamId
WHERE w.id IN ({placeholders})
"""
	cur.execute(sql, ids)

	info: dict[str, dict] = {}
	for wrestler_id, name, grad_year, team_id, team_name in cur.fetchall():
		section, division = get_team_section(team_id) if team_id else (None, None)
		info[wrestler_id] = {
			"name": name,
			"gradYear": grad_year,
			"teamId": team_id,
			"teamName": team_name,
			"section": section,
			"division": division,
		}
	return info

#return all post season events a wrestler participated in each year
def get_post_participation(wrestler_id: str) -> dict[int, list[dict]]:
	# find all events with the word "MIAA" in the name of the event (no other search criteria)
	conn = db.get_connection()
	cur = conn.cursor()
	sql = """
SELECT DISTINCT
  e.id,
  e.name,
  e.date
FROM events AS e
JOIN matches AS m ON m.eventId = e.id
WHERE (m.topId = ? OR m.bottomId = ?)
  AND e.name LIKE '%MIAA%'
ORDER BY e.date ASC;
	"""
	cur.execute(sql, (wrestler_id, wrestler_id))
	rows = cur.fetchall()
	participation: dict[int, list[dict]] = {}
	for event_id, event_name, event_date in rows:
		date_obj = parse_date(event_date)
		year = get_school_year(date_obj)
		if year not in participation:
			participation[year] = []
		participation[year].append({
			"id": event_id,
			"name": event_name,
			"date": date_obj,
		})

	return participation


def infer_grad_year_from_post(wrestler_id: str) -> int | None:
	"""Infer minimum gradYear from earliest postseason appearance."""
	participation = get_post_participation(wrestler_id)
	if not participation:
		return None
	earliest_school_year = min(participation.keys())
	return earliest_school_year + 4
