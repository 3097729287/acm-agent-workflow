PRAGMA foreign_keys = ON;

CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  nickname TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE ac_events (
  user_id TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  problem_key TEXT NOT NULL,
  event_id TEXT NOT NULL,
  accepted_at TEXT NOT NULL,
  accepted_day TEXT NOT NULL,
  difficulty REAL,
  received_at TEXT NOT NULL,
  PRIMARY KEY(user_id, problem_key),
  UNIQUE(user_id, event_id)
);
CREATE INDEX ac_events_day_user ON ac_events(accepted_day, user_id);

CREATE TABLE request_limits (
  bucket TEXT PRIMARY KEY,
  count INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX request_limits_expiry ON request_limits(expires_at);
