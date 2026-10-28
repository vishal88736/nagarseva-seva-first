CREATE TABLE IF NOT EXISTS citizen_issues (
  id TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  request_sha256 TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('submitted','under_review','resolved')),
  reported_at TEXT NOT NULL,
  body TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS citizen_issues_status_date ON citizen_issues(status, reported_at);
CREATE TABLE IF NOT EXISTS citizen_issue_attachments (
  issue_id TEXT PRIMARY KEY REFERENCES citizen_issues(id),
  filename TEXT NOT NULL,
  content_type TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  content BLOB NOT NULL
);
