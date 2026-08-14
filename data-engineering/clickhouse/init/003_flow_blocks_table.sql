-- One row per contiguous coding block produced by
-- cognistream.processing.flow_state.compute_flow_blocks(). A block is
-- "uninterrupted flow" once duration_minutes crosses the 90-minute
-- threshold with zero interruption events inside it.
CREATE TABLE IF NOT EXISTS cognistream.flow_blocks
(
    developer         LowCardinality(String),
    team              LowCardinality(String),
    date              Date,
    block_start       DateTime64(3, 'UTC'),
    block_end         DateTime64(3, 'UTC'),
    duration_minutes  Float64,
    is_flow_block     UInt8,                    -- 1 if duration_minutes >= flow_block_min_minutes
    interrupted_by    Nullable(String),          -- "source:event_type" that ended this block, NULL if natural session end
    ingested_at       DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(date)
ORDER BY (team, developer, block_start)
TTL date + INTERVAL 2 YEAR;
