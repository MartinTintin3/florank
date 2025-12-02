import api_types
import json
from datetime import datetime, timezone, timedelta
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