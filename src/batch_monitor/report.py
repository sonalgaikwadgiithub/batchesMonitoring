"""Builds the stakeholder email subject and body."""

from __future__ import annotations

from datetime import datetime
from html import escape

from .config import AppConfig
from .db import BatchStatusResult

_STYLE = """
body { font-family: Segoe UI, Arial, sans-serif; font-size: 13px; color: #202124; }
table { border-collapse: collapse; margin-top: 8px; }
th, td { border: 1px solid #d0d7de; padding: 5px 9px; text-align: left; }
th { background: #f2f4f7; }
tr.failed td { background: #fdecea; }
.banner-bad { background: #b3261e; color: #fff; padding: 8px 12px; font-weight: 600; }
.banner-ok { background: #1e7d32; color: #fff; padding: 8px 12px; font-weight: 600; }
.meta { color: #5f6368; font-size: 12px; margin-top: 14px; }
"""


def build_subject(config: AppConfig, result: BatchStatusResult) -> str:
    prefix = f"[{config.environment_label}] Batch Status"
    if result.is_healthy:
        return f"{prefix} - OK ({len(result.rows)} row(s))"
    return f"{prefix} - ACTION REQUIRED: {len(result.failed_rows)} failure(s)"


def _table(columns: list[str], rows: list[dict[str, object]], failed_ids: set[int]) -> str:
    header = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
    body_rows = []
    for row in rows:
        css = ' class="failed"' if id(row) in failed_ids else ""
        cells = "".join(
            f"<td>{escape('' if row.get(column) is None else str(row.get(column)))}</td>"
            for column in columns
        )
        body_rows.append(f"<tr{css}>{cells}</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def build_html_body(config: AppConfig, result: BatchStatusResult) -> str:
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    if result.is_healthy:
        banner = (
            '<div class="banner-ok">All batches look healthy. '
            "No failure detected.</div>"
        )
    else:
        banner = (
            f'<div class="banner-bad">{len(result.failed_rows)} batch row(s) reported '
            "a failure. Please investigate.</div>"
        )

    shown = result.rows[: config.max_rows_in_email]
    truncated = len(result.rows) - len(shown)
    failed_ids = {id(row) for row in result.failed_rows}

    sections = [banner]
    if result.failed_rows:
        sections.append("<h3>Failing rows</h3>")
        sections.append(
            _table(
                result.columns,
                result.failed_rows[: config.max_rows_in_email],
                failed_ids,
            )
        )
    sections.append("<h3>Full result set</h3>")
    sections.append(_table(result.columns, shown, failed_ids))
    if truncated > 0:
        sections.append(f"<p><i>{truncated} further row(s) omitted.</i></p>")

    sections.append(
        f'<div class="meta">Environment: {escape(config.environment_label)}<br>'
        f"Query source: {escape(config.query.source)}<br>"
        f"Generated: {escape(generated_at)}<br>"
        "Sent automatically by the batch status monitor.</div>"
    )

    return (
        f"<html><head><style>{_STYLE}</style></head><body>"
        f"{''.join(sections)}</body></html>"
    )


def build_text_body(config: AppConfig, result: BatchStatusResult) -> str:
    lines = [build_subject(config, result), ""]
    if result.failed_rows:
        lines.append(f"Failing rows ({len(result.failed_rows)}):")
        for row in result.failed_rows[: config.max_rows_in_email]:
            lines.append("  " + " | ".join(f"{key}={row[key]}" for key in result.columns))
        lines.append("")
    lines.append(f"Total rows returned: {len(result.rows)}")
    lines.append(f"Environment: {config.environment_label}")
    lines.append(f"Query source: {config.query.source}")
    return "\n".join(lines)
