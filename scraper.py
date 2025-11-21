import json
import downloader
import rich

# get year from cmd line args
import sys
year = None
if len(sys.argv) > 1:
	year = int(sys.argv[1])

with open("seasons.json", "r") as f:
	seasons = json.load(f)

	years = [year] if year else set([season["start_year"] for season in seasons] + [season["end_year"] for season in seasons])

	for year in years:
		print(f"Fetching events for year {year}...")
		data = downloader.fetch_events(year=year, event_type="all")

		# dump
		with open(f"events_{year}.json", "w") as ef:
			json.dump(data["response"], ef, indent=4)