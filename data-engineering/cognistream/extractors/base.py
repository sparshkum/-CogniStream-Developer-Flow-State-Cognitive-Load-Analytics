"""Shared helpers for writing raw extractor output to the landing zone.

Every extractor writes one JSON file per (source, run_date) under
`raw_data_dir/<source>/<run_date>.json`, mirroring how a real Airflow DAG
would land raw API responses in object storage before the cleaning step
picks them up. Keeping extractors dumb (fetch -> write raw JSON) and pushing
all normalization into `processing/clean.py` matches how a real pipeline
separates "extract" from "transform".
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from cognistream.config import PIPELINE


def raw_output_path(source: str, run_date: str) -> str:
    directory = os.path.join(PIPELINE.raw_data_dir, source)
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{run_date}.json")


def write_raw_payload(source: str, run_date: str, payload: list[dict]) -> str:
    path = raw_output_path(source, run_date)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    return path


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utcnow_run_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
