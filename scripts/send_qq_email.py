#!/usr/bin/env python3
"""Send UTF-8 email through QQ SMTP with structured JSON results."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import smtplib
import ssl
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_DIR = ".send-qq-email"
DEFAULT_CONFIG_FILE = "email.yaml"
DEFAULT_SMTP_HOST = "smtp.qq.com"
DEFAULT_SMTP_PORT = 587
DEFAULT_TIMEOUT_SECONDS = 20.0
QQ_MAIL_SETUP_URL = "https://mail.qq.com/"


class EmailConfigError(Exception):
    """Raised when SMTP configuration is missing or invalid."""


@dataclass(slots=True)
class EmailConfig:
    host: str
    port: int
    username: str
    password: str
    from_address: str
    to_address: str
    from_name: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    use_starttls: bool = True


@dataclass(slots=True)
class EmailPayload:
    subject: str
    text_body: str
    recipient: str
    html_body: str = ""
    attachments: list[Path] | None = None
    metadata: dict[str, str] | None = None


@dataclass(slots=True)
class EmailResult:
    status: str
    recipient: str
    sent_at: str
    error_type: str = ""
    error_summary: str = ""
    message_id: str = ""
    eml_path: str = ""
    dry_run: bool = False


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config = load_config(args)
        payload = build_payload(args, config)
        result = send_or_dry_run(config, payload, args)
    except EmailConfigError as exc:
        result = EmailResult(
            status="failed",
            recipient=args.to or os.environ.get("SMTP_TO", ""),
            sent_at=utc_now(),
            error_type="config_missing",
            error_summary=str(exc),
        )
        write_result(args, result)
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return 2

    write_result(args, result)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    if result.status in {"sent", "dry_run"}:
        return 0
    return 3


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send email through QQ SMTP.")
    parser.add_argument("--config", help="Path to private JSON/YAML config file.")
    parser.add_argument("--to", help="Recipient address. Overrides SMTP_TO/config.")
    parser.add_argument("--subject", help="Email subject.")
    parser.add_argument("--text", help="Plain text body.")
    parser.add_argument("--text-file", help="Path to UTF-8 plain text body file.")
    parser.add_argument("--html", help="HTML body.")
    parser.add_argument("--html-file", help="Path to UTF-8 HTML body file.")
    parser.add_argument("--attach", action="append", default=[], help="Path to a file attachment. Can be used more than once.")
    parser.add_argument("--test", action="store_true", help="Use a built-in SMTP test message.")
    parser.add_argument("--dry-run", action="store_true", help="Build artifacts without connecting to SMTP.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Task-owned output directory, normally .tmp/runs/<run-id>/send-qq-email.",
    )
    parser.add_argument("--eml-output", help="Explicit .eml output path.")
    parser.add_argument("--result-output", help="Explicit result JSON output path.")
    return parser.parse_args(argv)


def load_config(args: argparse.Namespace) -> EmailConfig:
    file_values = load_config_file(resolve_config_path(args.config))
    values = merge_config(file_values, os.environ)

    host = values.get("SMTP_HOST", DEFAULT_SMTP_HOST).strip() or DEFAULT_SMTP_HOST
    port_text = values.get("SMTP_PORT", str(DEFAULT_SMTP_PORT)).strip() or str(DEFAULT_SMTP_PORT)
    username = values.get("SMTP_USERNAME", "").strip()
    password = values.get("SMTP_PASSWORD", "")
    from_address = values.get("SMTP_FROM", username).strip()
    to_address = (args.to or values.get("SMTP_TO", "")).strip()
    from_name = values.get("SMTP_FROM_NAME", "").strip()
    timeout_text = values.get("SMTP_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)).strip()
    starttls_text = values.get("SMTP_USE_STARTTLS", "true").strip().lower()

    missing = []
    if not username:
        missing.append("SMTP_USERNAME")
    if not password:
        missing.append("SMTP_PASSWORD")
    if not to_address:
        missing.append("SMTP_TO or --to")
    if missing:
        raise EmailConfigError(format_missing_config_guidance(missing))

    try:
        port = int(port_text)
    except ValueError as exc:
        raise EmailConfigError(f"SMTP_PORT is not an integer: {port_text}") from exc
    try:
        timeout_seconds = float(timeout_text)
    except ValueError as exc:
        raise EmailConfigError(f"SMTP_TIMEOUT_SECONDS is not a number: {timeout_text}") from exc

    return EmailConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        to_address=to_address,
        from_name=from_name,
        timeout_seconds=timeout_seconds,
        use_starttls=starttls_text not in {"0", "false", "no"},
    )


def resolve_config_path(config_arg: str | None) -> Path:
    if config_arg:
        return Path(config_arg).expanduser()
    env_path = os.environ.get("SEND_QQ_EMAIL_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / DEFAULT_CONFIG_DIR / DEFAULT_CONFIG_FILE


def load_config_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        return normalize_smtp_payload(payload.get("smtp", payload))
    return normalize_smtp_payload(parse_simple_smtp_yaml(text))


def parse_simple_smtp_yaml(text: str) -> dict[str, Any]:
    """Parse the simple top-level smtp YAML shape used by this skill."""
    in_smtp = False
    values: dict[str, Any] = {}
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.strip() == "smtp:":
            in_smtp = True
            continue
        if not in_smtp:
            continue
        if not raw_line.startswith((" ", "\t")):
            break
        key, sep, value = raw_line.strip().partition(":")
        if not sep:
            continue
        values[key.strip()] = value.strip().strip("\"'")
    return values


def normalize_smtp_payload(payload: dict[str, Any]) -> dict[str, str]:
    mapping = {
        "host": "SMTP_HOST",
        "port": "SMTP_PORT",
        "username": "SMTP_USERNAME",
        "password": "SMTP_PASSWORD",
        "from_address": "SMTP_FROM",
        "from": "SMTP_FROM",
        "to_address": "SMTP_TO",
        "to": "SMTP_TO",
        "from_name": "SMTP_FROM_NAME",
        "timeout_seconds": "SMTP_TIMEOUT_SECONDS",
        "use_starttls": "SMTP_USE_STARTTLS",
    }
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        env_key = mapping.get(str(key), str(key))
        if value is not None:
            normalized[env_key] = str(value)
    return normalized


def merge_config(file_values: dict[str, str], env: os._Environ[str]) -> dict[str, str]:
    values = dict(file_values)
    keys = {
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SMTP_TO",
        "SMTP_FROM_NAME",
        "SMTP_TIMEOUT_SECONDS",
        "SMTP_USE_STARTTLS",
    }
    for key in keys:
        if env.get(key):
            values[key] = env[key]
    return values


def format_missing_config_guidance(missing: list[str]) -> str:
    missing_text = ", ".join(missing)
    return "\n".join(
        [
            f"Missing SMTP configuration: {missing_text}",
            "",
            "Manual QQ Mail setup is required before sending:",
            f"1. Open QQ Mail: {QQ_MAIL_SETUP_URL}",
            "2. Go to Settings > Account > POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV service.",
            "3. Enable POP3/SMTP or IMAP/SMTP, finish QQ Mail phone/QR verification, and copy the generated authorization code.",
            "4. Put your QQ mailbox address in SMTP_USERNAME.",
            "5. Put the generated authorization code in SMTP_PASSWORD; do not use your normal QQ password.",
            "6. Put the recipient in SMTP_TO, or pass --to recipient@example.com.",
            "",
            "Private config file example (~/.send-qq-email/email.yaml):",
            "smtp:",
            "  username: your-account@qq.com",
            "  password: paste-qq-mail-authorization-code-here",
            "  to_address: receiver@example.com",
            "",
            ".env keys, if your project loads a .env file:",
            "SMTP_USERNAME=your-account@qq.com",
            "SMTP_PASSWORD=paste-qq-mail-authorization-code-here",
            "SMTP_TO=receiver@example.com",
        ]
    )


def build_payload(args: argparse.Namespace, config: EmailConfig) -> EmailPayload:
    if args.test:
        subject = args.subject or "Send QQ Email SMTP test"
        text_body = args.text or "If you received this message, QQ SMTP delivery is working."
        html_body = args.html or "<p>If you received this message, QQ SMTP delivery is working.</p>"
    else:
        subject = args.subject
        text_body = args.text or read_optional_text(args.text_file)
        html_body = args.html or read_optional_text(args.html_file)

    if not subject:
        raise EmailConfigError("Missing message subject. Pass --subject or --test.")
    if not text_body and not html_body:
        raise EmailConfigError("Missing message body. Pass --text, --text-file, --html, --html-file, or --test.")
    if not text_body:
        text_body = "This email contains an HTML body. Please view it in an HTML-capable mail client."

    return EmailPayload(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        attachments=resolve_attachments(args.attach),
        recipient=config.to_address,
        metadata={"Source": "send-qq-email-skill"},
    )


def read_optional_text(path_text: str | None) -> str:
    if not path_text:
        return ""
    return Path(path_text).read_text(encoding="utf-8")


def resolve_attachments(path_texts: list[str]) -> list[Path]:
    attachments = []
    for path_text in path_texts:
        path = Path(path_text)
        if not path.is_file():
            raise EmailConfigError(f"Attachment does not exist or is not a file: {path}")
        attachments.append(path)
    return attachments


def send_or_dry_run(config: EmailConfig, payload: EmailPayload, args: argparse.Namespace) -> EmailResult:
    message = build_message(config, payload)
    eml_path = write_eml(args, message)

    if args.dry_run:
        return EmailResult(
            status="dry_run",
            recipient=payload.recipient,
            sent_at=utc_now(),
            message_id=str(message["Message-ID"] or ""),
            eml_path=eml_path,
            dry_run=True,
        )

    try:
        with smtplib.SMTP(config.host, config.port, timeout=config.timeout_seconds) as client:
            client.ehlo()
            if config.use_starttls:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            client.login(config.username, config.password)
            client.send_message(message)
    except smtplib.SMTPAuthenticationError:
        return failure(payload.recipient, "authentication_failed", "SMTP authentication failed. Check QQ authorization code.", eml_path)
    except smtplib.SMTPRecipientsRefused as exc:
        refused = ", ".join(exc.recipients.keys()) or payload.recipient
        return failure(payload.recipient, "send_failed", f"SMTP refused recipient: {refused}", eml_path)
    except (TimeoutError, OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as exc:
        return failure(payload.recipient, "connection_failed", f"SMTP connection failed: {exc}", eml_path)
    except smtplib.SMTPException as exc:
        return failure(payload.recipient, "send_failed", f"SMTP send failed: {exc}", eml_path)

    return EmailResult(
        status="sent",
        recipient=payload.recipient,
        sent_at=utc_now(),
        message_id=str(message["Message-ID"] or ""),
        eml_path=eml_path,
    )


def build_message(config: EmailConfig, payload: EmailPayload) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = payload.subject
    message["From"] = formataddr((config.from_name, config.from_address))
    message["To"] = payload.recipient
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid()
    for key, value in (payload.metadata or {}).items():
        safe_key = "".join(ch for ch in key if ch.isalnum() or ch == "-")
        if safe_key:
            message[f"X-Mozhi-{safe_key}"] = value
    message.set_content(payload.text_body, subtype="plain", charset="utf-8")
    if payload.html_body:
        message.add_alternative(payload.html_body, subtype="html", charset="utf-8")
    for attachment in payload.attachments or []:
        content_type, _ = mimetypes.guess_type(attachment.name)
        maintype, subtype = (content_type or "application/octet-stream").split("/", 1)
        message.add_attachment(
            attachment.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment.name,
        )
    return message


def write_eml(args: argparse.Namespace, message: EmailMessage) -> str:
    path = Path(args.eml_output) if args.eml_output else Path(args.output_dir) / "message.eml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(message.as_bytes())
    return str(path)


def write_result(args: argparse.Namespace, result: EmailResult) -> None:
    path = Path(args.result_output) if args.result_output else Path(args.output_dir) / "result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failure(recipient: str, error_type: str, summary: str, eml_path: str) -> EmailResult:
    return EmailResult(
        status="failed",
        recipient=recipient,
        sent_at=utc_now(),
        error_type=error_type,
        error_summary=summary,
        eml_path=eml_path,
    )


def utc_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    sys.exit(main())
