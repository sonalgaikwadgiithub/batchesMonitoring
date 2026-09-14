"""Entry point for the weekly batch status check."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from batch_monitor.config import ConfigError, load_config
from batch_monitor.db import fetch_batch_status
from batch_monitor.mailer import send_email
from batch_monitor.report import build_html_body, build_subject, build_text_body

EXIT_OK = 0
EXIT_FAILURES_FOUND = 1
EXIT_JOB_ERROR = 2

log = logging.getLogger("batch_monitor")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query Oracle for batch status and email stakeholders."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the query and print the report without sending mail.",
    )
    parser.add_argument(
        "--env-file",
        help="Path to an alternative .env file (defaults to ./.env).",
    )
    parser.add_argument(
        "--log-file",
        help="Append logs to this file in addition to the console.",
    )
    return parser.parse_args(argv)


def _setup_logging(log_file: str | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=handlers,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _setup_logging(args.log_file)

    try:
        config = load_config(args.env_file)
    except ConfigError as error:
        log.error("Configuration problem: %s", error)
        return EXIT_JOB_ERROR

    try:
        result = fetch_batch_status(config.oracle, config.query)
    except Exception:
        log.exception("Batch status check failed before any mail was produced")
        return EXIT_JOB_ERROR

    subject = build_subject(config, result)
    text_body = build_text_body(config, result)
    html_body = build_html_body(config, result)

    if result.is_healthy and not config.send_when_healthy:
        log.info("No failures and SEND_WHEN_HEALTHY is off; skipping mail.")
        return EXIT_OK

    if args.dry_run:
        log.info("Dry run - no mail sent. Subject: %s", subject)
        print(text_body)
        return EXIT_OK if result.is_healthy else EXIT_FAILURES_FOUND

    try:
        send_email(config.smtp, subject, text_body, html_body)
    except Exception:
        log.exception("Query succeeded but the report could not be emailed")
        return EXIT_JOB_ERROR

    return EXIT_OK if result.is_healthy else EXIT_FAILURES_FOUND


if __name__ == "__main__":
    raise SystemExit(main())
