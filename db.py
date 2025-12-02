"""Database helper module.

Provides get_connection() which returns a sqlite3 connection to data.db
and ensures the database schema is initialized from schema.sql on each
connection. Also includes helper insert, update, and lookup functions for
the `events`, `teams`, `wrestlers`, and `matches` tables.
"""
import os
import sqlite3
from typing import Optional, Tuple

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "data.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def _init_db(conn: sqlite3.Connection) -> None:
    """Initialize database schema from `schema.sql`.

    This runs every time get_connection() is called so the tables exist.
    """
    if not os.path.exists(SCHEMA_PATH):
        # Nothing to do if schema file is missing — raise a clear error
        raise FileNotFoundError(f"schema.sql not found at {SCHEMA_PATH}")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)

    # Backfill crawled flag for teams table if the column does not exist yet.
    cur = conn.execute("PRAGMA table_info(teams)")
    columns = {row[1] if not isinstance(row, sqlite3.Row) else row["name"] for row in cur.fetchall()}
    if "crawled" not in columns:
        conn.execute("ALTER TABLE teams ADD COLUMN crawled INTEGER DEFAULT 0")
        conn.commit()


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3.Connection to `data.db`, initializing schema.

    The schema from `schema.sql` is executed on every call to ensure
    tables exist. The connection uses Row factory for convenient access.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _build_set_clause(fields: dict) -> Tuple[str, list]:
    """Helper to build SET clause and parameters for an UPDATE statement.

    Returns tuple (set_clause, params)
    """
    parts = []
    params = []
    for k, v in fields.items():
        parts.append(f"{k} = ?")
        params.append(v)
    return ", ".join(parts), params


def _bool_to_int(value: Optional[bool]) -> Optional[int]:
    """Convert optional boolean to SQLite-friendly int (1/0)."""
    if value is None:
        return None
    return 1 if value else 0


def create_event(conn: sqlite3.Connection, *, event_id: str, date: Optional[str] = None,
                 state: Optional[str] = None, name: Optional[str] = None,
                 isDual: Optional[bool] = None, lat: Optional[float] = None,
                 lon: Optional[float] = None) -> str:
    """Insert a new row into `events`. Returns the event_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (id, date, state, name, isDual, lat, lon) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (event_id, date, state, name, _bool_to_int(isDual), lat, lon),
    )
    conn.commit()
    return event_id


def create_team(conn: sqlite3.Connection, *, team_id: str, name: Optional[str] = None,
                state: Optional[str] = None, crawled: Optional[bool] = None) -> str:
    """Insert a new row into `teams`. Returns the team_id."""
    cur = conn.cursor()
    crawled_value = _bool_to_int(crawled) if crawled is not None else 0
    cur.execute(
        "INSERT INTO teams (id, name, state, crawled) VALUES (?, ?, ?, ?)",
        (team_id, name, state, crawled_value),
    )
    conn.commit()
    return team_id


def create_wrestler(conn: sqlite3.Connection, *, wrestler_id: str, name: Optional[str] = None,
                    state: Optional[str] = None, gradYear: Optional[int] = None,
                    dateOfBirth: Optional[str] = None, teamId: Optional[str] = None) -> str:
    """Insert a new row into `wrestlers`. Returns the wrestler_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wrestlers (id, name, state, gradYear, dateOfBirth, teamId) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (wrestler_id, name, state, gradYear, dateOfBirth, teamId),
    )
    conn.commit()
    return wrestler_id


def wrestler_exists(conn: sqlite3.Connection, wrestler_id: str) -> bool:
    """Return True if a wrestler with `wrestler_id` exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM wrestlers WHERE id = ? LIMIT 1", (wrestler_id,))
    return cur.fetchone() is not None


def event_exists(conn: sqlite3.Connection, event_id: str) -> bool:
    """Return True if an event with `event_id` exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM events WHERE id = ? LIMIT 1", (event_id,))
    return cur.fetchone() is not None


def team_exists(conn: sqlite3.Connection, team_id: str) -> bool:
    """Return True if a team with `team_id` exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM teams WHERE id = ? LIMIT 1", (team_id,))
    return cur.fetchone() is not None


def is_team_crawled(conn: sqlite3.Connection, team_id: str) -> bool:
    """Return True if a team exists and has already been crawled."""
    cur = conn.cursor()
    cur.execute("SELECT crawled FROM teams WHERE id = ?", (team_id,))
    row = cur.fetchone()
    if row is None:
        return False
    value = row[0] if not isinstance(row, sqlite3.Row) else row["crawled"]
    return bool(value)


def set_team_crawled(conn: sqlite3.Connection, team_id: str, crawled: bool = True) -> int:
    """Mark the given team as crawled (or not)."""
    return update_team(conn, team_id, crawled=crawled)


def match_exists(conn: sqlite3.Connection, match_id: str) -> bool:
    """Return True if a match with `match_id` exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM matches WHERE id = ? LIMIT 1", (match_id,))
    return cur.fetchone() is not None


def create_match(conn: sqlite3.Connection, *, match_id: str, topId: Optional[str] = None,
                 bottomId: Optional[str] = None, winnerId: Optional[str] = None,
                 result: Optional[str] = None, winType: Optional[str] = None,
                 eventId: Optional[str] = None, weightClass: Optional[str] = None, date: Optional[str] = None) -> str:
    """Insert a new row into `matches`. Returns the match_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO matches (id, topId, bottomId, winnerId, result, winType, eventId, weightClass, date) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (match_id, topId, bottomId, winnerId, result, winType, eventId, weightClass, date),
    )
    conn.commit()
    return match_id


def update_event(conn: sqlite3.Connection, event_id: str, *, date: Optional[str] = None,
                 state: Optional[str] = None, name: Optional[str] = None,
                 isDual: Optional[bool] = None, lat: Optional[float] = None,
                 lon: Optional[float] = None) -> int:
    """Update fields on the `events` table for the given event_id.

    Only fields provided (not None) are updated. Returns number of rows updated.
    """
    fields = {}
    if date is not None:
        fields["date"] = date
    if state is not None:
        fields["state"] = state
    if name is not None:
        fields["name"] = name
    if isDual is not None:
        # store boolean as integer 0/1
        fields["isDual"] = _bool_to_int(isDual)
    if lat is not None:
        fields["lat"] = lat
    if lon is not None:
        fields["lon"] = lon

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(event_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE events SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


def update_team(conn: sqlite3.Connection, team_id: str, *, name: Optional[str] = None,
                state: Optional[str] = None, crawled: Optional[bool] = None) -> int:
    """Update fields on the `teams` table for the given team_id."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if state is not None:
        fields["state"] = state
    if crawled is not None:
        fields["crawled"] = _bool_to_int(crawled)

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(team_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE teams SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


def update_wrestler(conn: sqlite3.Connection, wrestler_id: str, *,
                    gradYear: Optional[int] = None, dateOfBirth: Optional[str] = None,
                    teamId: Optional[str] = None, name: Optional[str] = None,
                    state: Optional[str] = None) -> int:
    """Update fields on the `wrestlers` table for the given wrestler_id.

    Only fields provided (not None) are updated. Returns number of rows updated.
    """
    fields = {}
    if gradYear is not None:
        fields["gradYear"] = gradYear
    if dateOfBirth is not None:
        fields["dateOfBirth"] = dateOfBirth
    if teamId is not None:
        fields["teamId"] = teamId
    if name is not None:
        fields["name"] = name
    if state is not None:
        fields["state"] = state

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(wrestler_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE wrestlers SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


def update_match(conn: sqlite3.Connection, match_id: str, *, topId: Optional[str] = None,
                 bottomId: Optional[str] = None, winnerId: Optional[str] = None,
                 result: Optional[str] = None, winType: Optional[str] = None,
                 eventId: Optional[str] = None, weightClass: Optional[str] = None, date: Optional[str] = None) -> int:
    """Update fields on the `matches` table for the given match_id.

    Only provided fields are updated. Returns number of rows updated.
    """
    fields = {}
    if topId is not None:
        fields["topId"] = topId
    if bottomId is not None:
        fields["bottomId"] = bottomId
    if winnerId is not None:
        fields["winnerId"] = winnerId
    if result is not None:
        fields["result"] = result
    if winType is not None:
        fields["winType"] = winType
    if eventId is not None:
        fields["eventId"] = eventId
    if weightClass is not None:
        fields["weightClass"] = weightClass
    if date is not None:
        fields["date"] = date

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(match_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE matches SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


def backfill_match_dates(conn: sqlite3.Connection) -> int:
    """Populate missing match dates using their related event date.

    Returns the number of rows updated.
    """
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE matches
        SET date = (
            SELECT events.date
            FROM events
            WHERE events.id = matches.eventId
        )
        WHERE date IS NULL
          AND eventId IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM events
              WHERE events.id = matches.eventId
                AND events.date IS NOT NULL
          )
        ;
        """
    )
    conn.commit()
    return cur.rowcount


__all__ = [
    "get_connection",
    "create_event",
    "event_exists",
    "update_event",
    "create_team",
    "team_exists",
    "is_team_crawled",
    "set_team_crawled",
    "update_team",
    "create_wrestler",
    "wrestler_exists",
    "update_wrestler",
    "create_match",
    "match_exists",
    "update_match",
    "backfill_match_dates",
]
