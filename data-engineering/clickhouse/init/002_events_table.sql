-- Raw, cleaned event log from all four developer-tool sources.
-- MergeTree ordered by (team, developer, event_time) so per-developer,
-- per-time-range scans -- the FastAPI layer's bread and butter -- only
-- touch the granules they need instead of scanning the whole table.
CREATE TABLE IF NOT EXISTS cognistream.events
(
    event_id          String,
    developer         LowCardinality(String),
    team              LowCardinality(String),
    source            LowCardinality(String),   -- github | slack | jira | activitywatch
    event_type        LowCardinality(String),   -- commit | pr_review_requested | message_received | ...
    event_time        DateTime64(3, 'UTC'),
    duration_seconds  Float64 DEFAULT 0,
    metadata          String,                   -- JSON-encoded source-specific detail
    event_date        Date MATERIALIZED toDate(event_time),
    ingested_at       DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (team, developer, event_time)
TTL event_date + INTERVAL 2 YEAR;
