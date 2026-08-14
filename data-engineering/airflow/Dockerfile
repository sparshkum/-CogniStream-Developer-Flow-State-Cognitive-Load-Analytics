FROM apache/airflow:2.10.4-python3.11

USER root
# The `cognistream` package (extractors/processing/storage) lives one level
# up from airflow/ so both the DAGs and the plain-Python local runner share
# the exact same code.
COPY --chown=airflow:root cognistream /opt/cognistream/cognistream
COPY --chown=airflow:root clickhouse /opt/cognistream/clickhouse
COPY --chown=airflow:root pyproject.toml /opt/cognistream/pyproject.toml

USER airflow
COPY --chown=airflow:root airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir -e /opt/cognistream

ENV PYTHONPATH="/opt/cognistream:${PYTHONPATH}" \
    COGNISTREAM_RAW_DIR="/opt/airflow/data/raw" \
    COGNISTREAM_CLEAN_DIR="/opt/airflow/data/clean" \
    CLICKHOUSE_HOST="clickhouse" \
    CLICKHOUSE_PORT="8123"
