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
                state: Optional[str] = None) -> str:
    """Insert a new row into `teams`. Returns the team_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO teams (id, name, state) VALUES (?, ?, ?)",
        (team_id, name, state),
    )
    conn.commit()
    return team_id


def create_wrestler(conn: sqlite3.Connection, *, wrestler_id: str, name: Optional[str] = None,
                    state: Optional[str] = None, grade: Optional[int] = None,
                    dateOfBirth: Optional[str] = None, teamId: Optional[str] = None) -> str:
    """Insert a new row into `wrestlers`. Returns the wrestler_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wrestlers (id, name, state, grade, dateOfBirth, teamId) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (wrestler_id, name, state, grade, dateOfBirth, teamId),
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


def match_exists(conn: sqlite3.Connection, match_id: str) -> bool:
    """Return True if a match with `match_id` exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM matches WHERE id = ? LIMIT 1", (match_id,))
    return cur.fetchone() is not None


def create_match(conn: sqlite3.Connection, *, match_id: str, topId: Optional[str] = None,
                 bottomId: Optional[str] = None, winnerId: Optional[str] = None,
                 result: Optional[str] = None, winType: Optional[str] = None,
                 eventId: Optional[str] = None, weightClass: Optional[str] = None) -> str:
    """Insert a new row into `matches`. Returns the match_id."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO matches (id, topId, bottomId, winnerId, result, winType, eventId, weightClass) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (match_id, topId, bottomId, winnerId, result, winType, eventId, weightClass),
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
                state: Optional[str] = None) -> int:
    """Update fields on the `teams` table for the given team_id."""
    fields = {}
    if name is not None:
        fields["name"] = name
    if state is not None:
        fields["state"] = state

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(team_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE teams SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


def update_wrestler(conn: sqlite3.Connection, wrestler_id: str, *,
                    grade: Optional[int] = None, dateOfBirth: Optional[str] = None,
                    teamId: Optional[str] = None, name: Optional[str] = None,
                    state: Optional[str] = None) -> int:
    """Update fields on the `wrestlers` table for the given wrestler_id.

    Only fields provided (not None) are updated. Returns number of rows updated.
    """
    fields = {}
    if grade is not None:
        fields["grade"] = grade
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
                 eventId: Optional[str] = None, weightClass: Optional[str] = None) -> int:
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

    if not fields:
        return 0

    set_clause, params = _build_set_clause(fields)
    params.append(match_id)
    cur = conn.cursor()
    cur.execute(f"UPDATE matches SET {set_clause} WHERE id = ?", params)
    conn.commit()
    return cur.rowcount


__all__ = [
    "get_connection",
    "create_event",
    "event_exists",
    "update_event",
    "create_team",
    "team_exists",
    "update_team",
    "create_wrestler",
    "wrestler_exists",
    "update_wrestler",
    "create_match",
    "match_exists",
    "update_match",
]
