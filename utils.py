import api_types
import json
from datetime import datetime, timezone

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

	