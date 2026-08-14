"""Thin wrapper around `clickhouse_connect` plus schema bootstrapping.

Bootstrapping the schema from the `clickhouse/init/*.sql` files here (instead
of only relying on ClickHouse's docker-entrypoint-initdb.d convention) lets
the exact same code stand up the schema in CI, in a fresh dev ClickHouse
instance, or inside the Docker container.
"""
from __future__ import annotations

import glob
import os

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from cognistream.config import CLICKHOUSE

_INIT_SQL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "clickhouse", "init")


def get_client() -> Client:
    return clickhouse_connect.get_client(
        host=CLICKHOUSE.host,
        port=CLICKHOUSE.port,
        username=CLICKHOUSE.username,
        password=CLICKHOUSE.password,
        secure=CLICKHOUSE.secure,
    )


def bootstrap_schema(client: Client | None = None) -> None:
    """Run every .sql file in clickhouse/init/, in filename order. Idempotent:
    every statement uses CREATE ... IF NOT EXISTS.
    """
    client = client or get_client()
    for path in sorted(glob.glob(os.path.join(_INIT_SQL_DIR, "*.sql"))):
        with open(path, "r", encoding="utf-8") as fh:
            statement = fh.read().strip()
        if statement:
            client.command(statement)
