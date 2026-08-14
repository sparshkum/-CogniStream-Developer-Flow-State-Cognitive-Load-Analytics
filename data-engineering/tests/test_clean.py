from cognistream.extractors import activitywatch_extractor, github_extractor, jira_extractor, slack_extractor
from cognistream.processing.clean import clean_events


def test_clean_events_merges_all_four_sources_into_canonical_schema():
    days = 4
    gh = github_extractor.extract_recent(days=days)
    sl = slack_extractor.extract_recent(days=days)
    ji = jira_extractor.extract_recent(days=days)
    aw = activitywatch_extractor.extract_recent(days=days)
    day = sorted(gh.keys())[-1]

    df = clean_events(
        {
            "github": gh.get(day, []),
            "slack": sl.get(day, []),
            "jira": ji.get(day, []),
            "activitywatch": aw.get(day, []),
        }
    )

    assert set(df.columns) == {"event_id", "developer", "team", "source", "event_type", "event_time", "duration_seconds", "metadata"}
    assert set(df["source"].unique().to_list()) <= {"github", "slack", "jira", "activitywatch"}
    assert df["team"].null_count() == 0, "every developer must resolve to a team via the roster"
    assert df["event_time"].is_sorted() or df.sort(["developer", "event_time"]).equals(df)
