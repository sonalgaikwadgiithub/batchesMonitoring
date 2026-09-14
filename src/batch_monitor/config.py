"""Runtime configuration, loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_FAILURE_VALUES = "FAILED,FAILURE,FAIL,ERROR,ABORTED,ABEND,KILLED,CANCELLED"


class ConfigError(RuntimeError):
    pass


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Missing required setting {name!r}. Copy .env.example to .env and fill it in."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class OracleConfig:
    user: str
    password: str
    dsn: str


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    sender: str
    recipients: list[str]
    use_starttls: bool
    username: str
    password: str


@dataclass(frozen=True)
class QueryConfig:
    sql: str
    source: str
    status_column: str
    failure_values: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppConfig:
    oracle: OracleConfig
    smtp: SmtpConfig
    query: QueryConfig
    environment_label: str
    send_when_healthy: bool
    max_rows_in_email: int


def _load_query() -> QueryConfig:
    """SQL comes from a file when BATCH_SQL_FILE is set, otherwise from BATCH_SQL."""
    sql_file = _optional("BATCH_SQL_FILE")
    if sql_file:
        path = Path(sql_file)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.is_file():
            raise ConfigError(f"BATCH_SQL_FILE does not exist: {path}")
        sql = path.read_text(encoding="utf-8")
        source = str(path)
    else:
        sql = _require("BATCH_SQL")
        source = "BATCH_SQL environment variable"

    # Oracle rejects a trailing semicolon when the statement is sent via the driver.
    sql = sql.strip().rstrip(";").strip()
    if not sql:
        raise ConfigError(f"No SQL statement found in {source}.")

    return QueryConfig(
        sql=sql,
        source=source,
        status_column=_optional("BATCH_STATUS_COLUMN").upper(),
        failure_values=[
            value.upper()
            for value in _csv(_optional("BATCH_FAILURE_VALUES", DEFAULT_FAILURE_VALUES))
        ],
    )


def load_config(env_file: str | os.PathLike[str] | None = None) -> AppConfig:
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)

    recipients = _csv(_require("MAIL_TO"))
    if not recipients:
        raise ConfigError("MAIL_TO must contain at least one address.")

    sender = _optional("MAIL_FROM") or recipients[0]

    return AppConfig(
        oracle=OracleConfig(
            user=_require("ORACLE_USER"),
            password=_require("ORACLE_PASSWORD"),
            dsn=_require("ORACLE_DSN"),
        ),
        smtp=SmtpConfig(
            host=_require("SMTP_HOST"),
            port=int(_optional("SMTP_PORT", "25")),
            sender=sender,
            recipients=recipients,
            use_starttls=_flag("SMTP_STARTTLS", False),
            username=_optional("SMTP_USERNAME"),
            password=_optional("SMTP_PASSWORD"),
        ),
        query=_load_query(),
        environment_label=_optional("ENVIRONMENT_LABEL", "PROD"),
        send_when_healthy=_flag("SEND_WHEN_HEALTHY", True),
        max_rows_in_email=int(_optional("MAX_ROWS_IN_EMAIL", "200")),
    )
