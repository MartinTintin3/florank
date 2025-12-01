-- schema.sql
-- Run this script to create the required tables for the application.

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    date TEXT,
    state TEXT,
    name TEXT,
    isDual INTEGER,
    lat REAL,
    lon REAL
);

CREATE TABLE IF NOT EXISTS teams (
    id TEXT PRIMARY KEY,
    name TEXT,
    state TEXT,
    crawled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS wrestlers (
    id TEXT PRIMARY KEY,
    name TEXT,
    state TEXT,
    gradYear INTEGER,
    dateOfBirth TEXT,
    teamId TEXT,
    FOREIGN KEY (teamId) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS matches (
    id TEXT PRIMARY KEY,
    topId TEXT,
    bottomId TEXT,
    winnerId TEXT,
    result TEXT,
    winType TEXT,
    eventId TEXT,
    weightClass TEXT,
    date TEXT,
    FOREIGN KEY (topId) REFERENCES wrestlers(id),
    FOREIGN KEY (bottomId) REFERENCES wrestlers(id),
    FOREIGN KEY (winnerId) REFERENCES wrestlers(id),
    FOREIGN KEY (eventId) REFERENCES events(id)
);