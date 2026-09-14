"""Oracle access and failure classification."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import oracledb

from .config import OracleConfig, QueryConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchStatusResult:
    columns: list[str]
    rows: list[dict[str, object]]
    failed_rows: list[dict[str, object]]

    @property
    def is_healthy(self) -> bool:
        return not self.failed_rows


def _cell_indicates_failure(value: object, failure_values: list[str]) -> bool:
    if value is None:
        return False
    text = str(value).strip().upper()
    if not text:
        return False
    return any(marker in text for marker in failure_values)


def _row_indicates_failure(
    row: dict[str, object], query: QueryConfig
) -> bool:
    if query.status_column:
        if query.status_column not in row:
            raise KeyError(
                f"BATCH_STATUS_COLUMN={query.status_column!r} is not in the result "
                f"columns: {sorted(row)}"
            )
        return _cell_indicates_failure(row[query.status_column], query.failure_values)

    # No status column configured: any cell carrying a failure marker flags the row.
    return any(
        _cell_indicates_failure(value, query.failure_values) for value in row.values()
    )


def fetch_batch_status(
    oracle: OracleConfig, query: QueryConfig
) -> BatchStatusResult:
    log.info("Connecting to Oracle DSN %s as %s", oracle.dsn, oracle.user)
    with oracledb.connect(
        user=oracle.user, password=oracle.password, dsn=oracle.dsn
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query.sql)
            columns = [description[0] for description in cursor.description]
            rows = [dict(zip(columns, values)) for values in cursor.fetchall()]

    log.info("Query returned %d row(s) from %s", len(rows), query.source)
    failed_rows = [row for row in rows if _row_indicates_failure(row, query)]
    if failed_rows:
        log.warning("%d row(s) classified as failures", len(failed_rows))

    return BatchStatusResult(columns=columns, rows=rows, failed_rows=failed_rows)
