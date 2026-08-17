"""Mock developer-API extractors: GitHub, Slack, Jira, ActivityWatch (VSCode).

Each extractor mimics the real API's response shape so `processing/clean.py`
has genuine normalization work to do. All four extractors read from a single
shared behavioral simulation (`mock_world.py`) so that a Slack ping, a Jira
ping-pong, and an ActivityWatch idle gap for the same developer on the same
day are mutually consistent -- exactly like they would be in production,
where all four systems are observing the same human.
"""
