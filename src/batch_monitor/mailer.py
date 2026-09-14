"""SMTP delivery."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from .config import SmtpConfig

log = logging.getLogger(__name__)


def send_email(
    smtp: SmtpConfig, subject: str, text_body: str, html_body: str
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp.sender
    message["To"] = ", ".join(smtp.recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    log.info("Sending mail via %s:%s to %s", smtp.host, smtp.port, smtp.recipients)
    with smtplib.SMTP(smtp.host, smtp.port, timeout=60) as server:
        server.ehlo()
        if smtp.use_starttls:
            server.starttls()
            server.ehlo()
        if smtp.username:
            server.login(smtp.username, smtp.password)
        server.send_message(message)
    log.info("Mail sent")
