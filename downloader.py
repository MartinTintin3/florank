import requests
from typing import Literal, Callable
import db
import api_types

import utils

event_bout_params = {
	"include": "event,topWrestler.team,bottomWrestler.team,weightClass,weightClass.division",
	"fields[event]": "startDateTime,state,name,location,isDual",
	"fields[bout]": "topWrestlerId,bottomWrestlerId,winnerWrestlerId,result,winType,weightClassId",
	"fields[wrestler]": "firstName,lastName,state,divisionId,teamId,grade,weightClassId,dateOfBirth,identityPersonId,isWeighInOk",
	"fields[team]": "name,abbreviation,city,state,identityTeamId",
}

def download_all(url: str, callback=None):
	req = requests.get(url)
	req.raise_for_status()
	data = req.json()
	if callback:
		callback(data)
	while utils.next_link(data, url) :
		url = utils.next_link(data, url) # type: ignore
		req = requests.get(url)
		req.raise_for_status()
		data = req.json()
		if callback:
			callback(data, url)
			

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

def get_event_bouts(event_id: str, partial_callback: Callable[[api_types.BoutsResponse, str], None] = lambda x, y: None):
	url = f"https://floarena-api.flowrestling.org/bouts/?eventId={event_id}"

	full_url = url + "&" + "&".join([f"{key}={value}" for key, value in event_bout_params.items()])
	
	download_all(full_url, callback=partial_callback)

def store_event_bout_data(data: api_types.BoutsResponse, url: str = ""):
	conn = db.get_connection()
	
	lookup = {}

		# find type event in included
	event = list(filter(lambda x: x["type"] == "event", data.get("included", [])))[0]

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
	
	for included in data.get("included", []):
		attrs = included["attributes"]
		if included["type"] == "wrestler":
			team = lookup.get(attrs["teamId"])
			team_id = team["attributes"]["identityTeamId"] if team else None
			grade = attrs.get("grade").get("attributes", {}).get("numericValue") if attrs.get("grade") else None
			if not db.wrestler_exists(conn, attrs["identityPersonId"]) and attrs.get("identityPersonId"):
				db.create_wrestler(
					conn,
					wrestler_id=attrs.get("identityPersonId"),
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
					grade=grade,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
				)
			else:
				db.update_wrestler(
					conn,
					wrestler_id=attrs["identityPersonId"],
					grade=grade,
					dateOfBirth=attrs.get("dateOfBirth"),
					teamId=team_id,
					name=f"{attrs.get('firstName', '')} {attrs.get('lastName', '')}".strip(),
					state=attrs.get("state"),
				)

	for bout in data["data"]:
		attrs = bout["attributes"]

		if attrs["winType"] in ["BYE", "FOR"]:
			continue

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

def store_event(event_id: str):
	get_event_bouts(event_id, partial_callback=store_event_bout_data)