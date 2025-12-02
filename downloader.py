import requests
from typing import Literal, Callable, Optional
import db
import api_types

from datetime import datetime

import utils

event_bout_params = {
	"include": "event,topWrestler.team,bottomWrestler.team,weightClass,weightClass.division",
	"fields[event]": "startDateTime,state,name,location,isDual",
	"fields[bout]": "topWrestlerId,bottomWrestlerId,winnerWrestlerId,result,winType,weightClassId,startDateTime,goDateTime,endDateTime",
	"fields[wrestler]": "firstName,lastName,state,divisionId,teamId,grade,weightClassId,dateOfBirth,identityPersonId,isWeighInOk",
	"fields[team]": "name,abbreviation,city,state,identityTeamId",
}

team_bout_paarms = {
	"include": "event,topWrestler.team,bottomWrestler.team,weightClass,weightClass.division",
	"fields[event]": "startDateTime,state,name,location,isDual",
	"fields[bout]": "topWrestlerId,bottomWrestlerId,winnerWrestlerId,result,winType,weightClassId,startDateTime,goDateTime,endDateTime,eventId",
	"fields[wrestler]": "firstName,lastName,state,divisionId,teamId,grade,weightClassId,dateOfBirth,identityPersonId,isWeighInOk,eventId",
	"fields[team]": "name,abbreviation,city,state,identityTeamId",
}

def download_all(url: str, callback=None):
	req = requests.get(url)
	req.raise_for_status()
	data = req.json()
	max = data.get("meta", {}).get("total", 0)
	downloaded = len(data.get("data", []))
	if callback:
		callback(data)
	while utils.next_link(data, url) :
		url = utils.next_link(data, url) # type: ignore
		req = requests.get(url)
		req.raise_for_status()
		data = req.json()
		downloaded += len(data.get("data", []))
		if callback:
			callback(data, url, downloaded / max if max > 0 else 0)
			

def fetch_events(year: int | None = None, month: int | None = None, event_type: Literal["tournament", "duals", "all"] = "all"):
	base_url = "https://arena.flowrestling.org/events/past"
	params = []
	
	if year is not None:
		params.append(f"year={year}")
	if month is not None:
		params.append(f"month={month}")
	if event_type:
		params.append(f"eventType={event_type}")
	
	query_string = "&".join(params)
	full_url = f"{base_url}?{query_string}" if query_string else base_url
	
	response = requests.get(full_url)
	response.raise_for_status()
	
	return response.json()  # Assuming the response is in JSON format

def get_event_bouts(event_id: str, partial_callback: Callable[[api_types.BoutsResponse, str, float], None] = lambda x, y, z: None):
	url = f"https://floarena-api.flowrestling.org/bouts/?eventId={event_id}"

	full_url = url + "&" + "&".join([f"{key}={value}" for key, value in event_bout_params.items()])
	
	download_all(full_url, callback=partial_callback)

def get_team_bouts(team_id: str, partial_callback: Callable[[api_types.BoutsResponse, str, float], None] = lambda x, y, z: None):
	url = f"https://floarena-api.flowrestling.org/bouts/?identityTeamId={team_id}"

	full_url = url + "&" + "&".join([f"{key}={value}" for key, value in team_bout_paarms.items()])
	
	download_all(full_url, callback=partial_callback)

def store_event_bout_data(data: api_types.BoutsResponse, url: str = "", progress: float = 0.0):
	conn = db.get_connection()
	
	lookup = {}

	# find type event in included
	event = next((item for item in data.get("included", []) if item.get("type") == "event"), None)
	if event is None:
		return

	for included in data.get("included", []):
		lookup[included["id"]] = included
		attrs = included["attributes"]
		if included["type"] == "team" and attrs.get("identityTeamId"):
			if not db.team_exists(conn, attrs["identityTeamId"]):
				db.create_team(
					conn,
					team_id=attrs["identityTeamId"],
					name=attrs.get("name"),
					state=attrs.get("state"),
				)
		if included["type"] == "event" and not db.event_exists(conn, included["id"]):
			attrs = included["attributes"]
			db.create_event(
				conn,
				event_id=included["id"],
				name=attrs.get("name"),
				date=attrs.get("startDateTime"),
				state=attrs.get("state"),
				isDual=attrs.get("isDual"),
				lat=attrs.get("location", {}).get("latitude", None),
				lon=attrs.get("location", {}).get("longitude", None),
			)
	
	for included in data.get("included", []):
		attrs = included.get("attributes", {})
		if included["type"] == "wrestler":
			person_id = attrs.get("identityPersonId", f"unknown_{included['id']}")
			if not person_id:
				continue
			team = lookup.get(attrs.get("teamId"), {}) if attrs.get("teamId") else None
			team_id = team.get("attributes", {}).get("identityTeamId") if team else None
			event_attrs = event.get("attributes", {})
			grade = None
			if attrs.get("grade"):
				grade = attrs["grade"].get("attributes", {}).get("numericValue")
			cur_grade = None
			if grade is not None and grade >= 8 and event_attrs.get("startDateTime"):
				cur_grade = utils.calc_cur_grade(
					past_grade=grade,
					past_date=event_attrs["startDateTime"],
					cur_date=datetime.now(),
				)
			grad_year = utils.calc_grad_year(grade=cur_grade, as_of=datetime.now()) if cur_grade is not None else None

			if not db.wrestler_exists(conn, person_id):
				db.create_wrestler(
					conn,
					wrestler_id=person_id,
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
					gradYear=grad_year,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
				)
			else:
				db.update_wrestler(
					conn,
					wrestler_id=person_id,
					gradYear=grad_year,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
				)

	for bout in data["data"]:
		attrs = bout["attributes"]

		if attrs["winType"] in ["BYE", "FOR"]:
			continue
	
		if attrs.get("winnerWrestlerId") is None:
			continue  # skip matches without a winner

		top_wrestler = lookup.get(attrs.get("topWrestlerId")) if attrs.get("topWrestlerId") else None
		bottom_wrestler = lookup.get(attrs.get("bottomWrestlerId")) if attrs.get("bottomWrestlerId") else None
		winner_wrestler = lookup.get(attrs.get("winnerWrestlerId")) if attrs.get("winnerWrestlerId") else None
		weightClass = lookup.get(attrs.get("weightClassId"), {}) if attrs.get("weightClassId") else None
		division_id = weightClass.get("attributes", {}).get("divisionId") if weightClass else None
		division = lookup.get(division_id) if division_id else None
		if not division.get("attributes", {}).get("isVarsity", True) if division else True:
			continue  # skip non-varsity matches
		if top_wrestler is None:
			continue  # skip invalid wrestlers
		if bottom_wrestler is None:
			continue  # skip invalid wrestlers

		date = attrs.get("startDateTime") or attrs.get("goDateTime") or attrs.get("endDateTime")
		if date is None:
			date = event.get("attributes", {}).get("startDateTime")

		if not db.match_exists(conn, bout["id"]):
			db.create_match(
				conn,
				match_id=bout["id"],
				topId=top_wrestler["attributes"].get("identityPersonId", f"unknown_{attrs.get('topWrestlerId')}") if top_wrestler else None,
				bottomId=bottom_wrestler["attributes"].get("identityPersonId", f"unknown_{attrs.get('bottomWrestlerId')}") if bottom_wrestler else None,
				winnerId=winner_wrestler["attributes"].get("identityPersonId", f"unknown_{attrs.get('winnerWrestlerId')}") if winner_wrestler else None,
				result=attrs.get("result"),
				winType=attrs.get("winType"),
				eventId=event["id"],
				weightClass=lookup.get(attrs.get("weightClassId"), {}).get("attributes", {}).get("name"),
				date=date,
			)
	
	if not utils.next_link(data, url) and not db.event_exists(conn, event["id"]):
		attrs = event["attributes"]
		db.create_event(
			conn,
			event_id=event["id"],
			name=attrs.get("name"),
			date=attrs.get("startDateTime"),
			state=attrs.get("state"),
			isDual=attrs.get("isDual"),
			lat=attrs.get("location", {}).get("latitude", None),
			lon=attrs.get("location", {}).get("longitude", None),
		)

def store_event(event_id: str, progress_callback: Optional[Callable[[float], None]] = None):
	"""Fetch and persist a single event, informing caller about download progress."""

	def _partial_callback(data: api_types.BoutsResponse, url: str = "", fraction: float = 0.0):
		store_event_bout_data(data, url, fraction)
		if progress_callback is not None:
			# Clamp to [0, 1] since upstream may slightly overshoot due to rounding.
			progress_callback(max(0.0, min(1.0, fraction)))

	get_event_bouts(event_id, partial_callback=_partial_callback)
	if progress_callback is not None:
		progress_callback(1.0)

def store_team_bout_data(data: api_types.BoutsResponse, url: str = "", progress: float = 0.0):
	conn = db.get_connection()
	
	lookup = {}


	for included in data.get("included", []):
		lookup[included["id"]] = included
		attrs = included["attributes"]
		if included["type"] == "team" and attrs.get("identityTeamId"):
			if not db.team_exists(conn, attrs["identityTeamId"]):
				db.create_team(
					conn,
					team_id=attrs["identityTeamId"],
					name=attrs.get("name"),
					state=attrs.get("state"),
				)
		if included["type"] == "event":
			if not db.event_exists(conn, included["id"]):
				attrs = included["attributes"]
				db.create_event(
					conn,
					event_id=included["id"],
					name=attrs.get("name"),
					date=attrs.get("startDateTime"),
					state=attrs.get("state"),
					isDual=attrs.get("isDual"),
					lat=attrs.get("location", {}).get("latitude", None),
					lon=attrs.get("location", {}).get("longitude", None),
				)
	
	for included in data.get("included", []):
		attrs = included["attributes"]
		if included["type"] == "wrestler":
			team = lookup.get(attrs["teamId"], {})
			event = lookup.get(attrs["eventId"], {})
			team_id = team["attributes"]["identityTeamId"] if team else None
			grade = attrs.get("grade").get("attributes", {}).get("numericValue") if attrs.get("grade") else None
			cur_grade = utils.calc_cur_grade(past_grade=grade, past_date=event["attributes"]["startDateTime"], cur_date=datetime.now()) if grade is not None and grade >= 8 else None
			grad_year = utils.calc_grad_year(grade=cur_grade, as_of=datetime.now()) if cur_grade is not None else None

			if not db.wrestler_exists(conn, attrs["identityPersonId"]) and attrs.get("identityPersonId"):
				db.create_wrestler(
					conn,
					wrestler_id=attrs.get("identityPersonId"),
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
					gradYear=grad_year,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
				)
			else:
				db.update_wrestler(
					conn,
					wrestler_id=attrs["identityPersonId"],
					gradYear=grad_year,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
				)

	for bout in data["data"]:
		attrs = bout["attributes"]

		if attrs["winType"] in ["BYE", "FOR"]:
			continue
	
		if attrs.get("winnerWrestlerId") is None:
			continue  # skip matches without a winner

		event = lookup.get(attrs["eventId"], {})

		top_wrestler = lookup.get(attrs["topWrestlerId"]) if attrs["topWrestlerId"] else None
		bottom_wrestler = lookup.get(attrs["bottomWrestlerId"]) if attrs["bottomWrestlerId"] else None
		winner_wrestler = lookup.get(attrs.get("winnerWrestlerId")) if attrs.get("winnerWrestlerId") else None
		weightClass = lookup.get(attrs["weightClassId"], {}) if attrs["weightClassId"] else None
		division = lookup.get(lookup.get(attrs["weightClassId"], {}).get("attributes", {}).get("divisionId", None), {}) if weightClass else None
		if not division.get("attributes", {}).get("isVarsity", True) if division else True:
			continue  # skip non-varsity matches
		if top_wrestler is None or top_wrestler.get("attributes", {}).get("identityPersonId") is None:
			continue  # skip invalid wrestlers
		if bottom_wrestler is None or bottom_wrestler.get("attributes", {}).get("identityPersonId") is None:
			continue  # skip invalid wrestlers

		date = attrs.get("startDateTime")
		if date is None:
			date = attrs.get("goDateTime")
		if date is None:
			date = attrs.get("endDateTime")
		if date is None:
			date = event.get("attributes", {}).get("startDateTime")
		if not db.match_exists(conn, bout["id"]):
			db.create_match(
				conn,
				match_id=bout["id"],
				topId=top_wrestler["attributes"]["identityPersonId"] if top_wrestler else None,
				bottomId=bottom_wrestler["attributes"]["identityPersonId"] if bottom_wrestler else None,
				winnerId=winner_wrestler["attributes"]["identityPersonId"] if winner_wrestler else None,
				result=attrs.get("result"),
				winType=attrs.get("winType"),
				eventId=event["id"],
				weightClass=lookup.get(attrs["weightClassId"], {}).get("attributes", {}).get("name", None),
				date=date
			)


def store_team(
	team_id: str,
	progress_callback: Optional[Callable[[float], None]] = None,
	name_callback: Optional[Callable[[str], None]] = None,
):
	"""Fetch and persist a single team, informing caller about download progress and metadata."""

	name_reported = False

	def _partial_callback(data: api_types.BoutsResponse, url: str = "", fraction: float = 0.0):
		nonlocal name_reported
		if name_callback is not None and not name_reported:
			team = next(
				(
					included
					for included in data.get("included", [])
					if included.get("type") == "team"
					and included.get("attributes", {}).get("identityTeamId") == team_id
				),
				None,
			)
			if team:
				team_name = team.get("attributes", {}).get("name")
				if team_name:
					name_reported = True
					name_callback(team_name)

		store_team_bout_data(data, url, fraction)
		if progress_callback is not None:
			# Clamp to [0, 1] since upstream may slightly overshoot due to rounding.
			progress_callback(max(0.0, min(1.0, fraction)))

	get_team_bouts(team_id, partial_callback=_partial_callback)
	conn = db.get_connection()
	if not db.team_exists(conn, team_id):
		db.create_team(conn, team_id=team_id)
	db.set_team_crawled(conn, team_id, True)
	if progress_callback is not None:
		progress_callback(1.0)