import utils
import db

conn = db.get_connection()	
cur = conn.cursor()

teams = utils.get_team_ids()

q_placeholders = ",".join(["?"] * len(teams))
placeholders = ", ".join("?" * len(teams))
sql = f"""
	SELECT
		w.name  AS wrestler_name,
		w.id    AS wrestler_id,
		t.name  AS team_name
	FROM wrestlers AS w
	JOIN teams AS t
		ON t.id = w.teamId
	WHERE w.grade IS NULL
		AND w.teamId IN ({placeholders})
"""
cur.execute(sql, teams)
rows = cur.fetchall()

for wrestler_name, wrestler_id, team_name in []: #rows:
	won = 0

	# Fetch all matches where this wrestler participated
	match_sql = """
		SELECT date, winnerId FROM matches
		WHERE topId = ? OR bottomId = ?
		ORDER BY date
	"""
	cur.execute(match_sql, (wrestler_id, wrestler_id))
	matches = cur.fetchall()

	if not len(matches):
		continue

	for (match_date, winner_id) in matches:
		if winner_id != wrestler_id:
			continue

		won += 1
	
	if won:
		print(f"{wrestler_name} ({wrestler_id}) - {team_name}: {won} wins")

conn.close()


print(utils.get_team_lineup("3834b461-34c2-46af-8527-c018714b092c", "08b275f3-f925-4b0d-b3b6-15a295f0a6c1"))