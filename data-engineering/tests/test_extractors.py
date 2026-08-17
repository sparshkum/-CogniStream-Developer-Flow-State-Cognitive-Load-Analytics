from cognistream.extractors import activitywatch_extractor, github_extractor, jira_extractor, slack_extractor
from cognistream.processing import clean


def test_extractors_produce_events_for_every_developer():
    days = 5
    gh = github_extractor.extract_recent(days=days)
    sl = slack_extractor.extract_recent(days=days)
    ji = jira_extractor.extract_recent(days=days)
    aw = activitywatch_extractor.extract_recent(days=days)

    assert set(gh.keys()) == set(sl.keys()) == set(ji.keys()) == set(aw.keys())
    assert len(gh) == days

    last_date = sorted(gh.keys())[-1]
    assert len(aw[last_date]) > 0, "ActivityWatch should emit IDE heartbeats every workday"


def test_github_payload_shapes_are_parseable_by_clean():
    payload = github_extractor.extract_for_date(sorted(github_extractor.extract_recent(days=3).keys())[-1], days=3)
    rows = clean.parse_github(payload)
    for row in rows:
        assert row["source"] == "github"
        assert row["event_type"] in {"commit", "pr_review_requested"}
        assert row["developer"]


def test_slack_payload_shapes_are_parseable_by_clean():
    day = sorted(slack_extractor.extract_recent(days=3).keys())[-1]
    payload = slack_extractor.extract_for_date(day, days=3)
    rows = clean.parse_slack(payload)
    assert len(rows) == len(payload)
    for row in rows:
        assert row["event_type"] in {"message_received", "mention_received"}


def test_jira_payload_shapes_are_parseable_by_clean():
    day = sorted(jira_extractor.extract_recent(days=3).keys())[-1]
    payload = jira_extractor.extract_for_date(day, days=3)
    rows = clean.parse_jira(payload)
    for row in rows:
        assert row["event_type"] in {"ticket_transitioned", "ticket_commented"}


def test_activitywatch_payload_shapes_are_parseable_by_clean():
    day = sorted(activitywatch_extractor.extract_recent(days=3).keys())[-1]
    payload = activitywatch_extractor.extract_for_date(day, days=3)
    rows = clean.parse_activitywatch(payload)
    assert len(rows) == len(payload)
    for row in rows:
        assert row["event_type"] == "ide_active"
        assert row["duration_seconds"] > 0
