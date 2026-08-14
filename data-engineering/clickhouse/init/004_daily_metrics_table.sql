-- Pre-aggregated per-developer/day rollup produced by
-- cognistream.processing.flow_state.compute_daily_metrics(). Backs the
-- dashboard's summary cards without re-aggregating flow_blocks on every
-- request; ReplacingMergeTree lets a re-run of the same day's pipeline
-- overwrite that day's row instead of duplicating it.
CREATE TABLE IF NOT EXISTS cognistream.daily_metrics
(
    developer                     LowCardinality(String),
    team                          LowCardinality(String),
    date                          Date,
    total_coding_minutes          Float64,
    flow_minutes                  Float64,
    interrupted_minutes           Float64,
    context_switch_tax_pct        Float64,
    num_flow_blocks               UInt32,
    longest_flow_block_minutes    Float64,
    num_interruptions_breaking_flow UInt32,
    total_interruption_events     UInt32,
    total_commits                 UInt32,
    updated_at                    DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
PARTITION BY toYYYYMM(date)
ORDER BY (team, developer, date);
