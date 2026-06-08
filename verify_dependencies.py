#!/usr/bin/env python3
"""Verify external dependencies and auth for send-qq-email.

This script checks only user/environment prerequisites: QQ Mail SMTP
credentials, recipient configuration, and optional SMTP network reachability.
Repository files, script compilation, dry-run artifacts, and smoke tests are
internal health checks and are intentionally outside this dependency check.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = Path.home() / ".send-qq-email" / "email.yaml"
DEFAULT_SMTP_HOST = "smtp.qq.com"
DEFAULT_SMTP_PORT = 587


def parse_simple_smtp_yaml(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    in_smtp = False
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
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
        if sep:
            values[key.strip()] = value.strip().strip("\"'")
    return {
        "SMTP_USERNAME": values.get("username", ""),
        "SMTP_PASSWORD": values.get("password", ""),
        "SMTP_TO": values.get("to_address", values.get("to", "")),
        "SMTP_HOST": values.get("host", ""),
        "SMTP_PORT": values.get("port", ""),
    }


def load_external_config() -> dict[str, str]:
    config_path = Path(os.environ.get("SEND_QQ_EMAIL_CONFIG", "")).expanduser() if os.environ.get("SEND_QQ_EMAIL_CONFIG") else DEFAULT_CONFIG_PATH
    file_values = parse_simple_smtp_yaml(config_path)
    values = {**file_values}
    for key in ("SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_TO", "SMTP_HOST", "SMTP_PORT"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def check_smtp_network(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=10):
            return True
    except OSError:
        return False


def main() -> int:
    check_network = "--check-network" in sys.argv
    values = load_external_config()
    required = {
        "SMTP_USERNAME": bool(values.get("SMTP_USERNAME")),
        "SMTP_PASSWORD": bool(values.get("SMTP_PASSWORD")),
        "SMTP_TO": bool(values.get("SMTP_TO")),
    }
    host = values.get("SMTP_HOST") or DEFAULT_SMTP_HOST
    try:
        port = int(values.get("SMTP_PORT") or DEFAULT_SMTP_PORT)
    except ValueError:
        port = DEFAULT_SMTP_PORT
        required["SMTP_PORT is integer"] = False

    ok = all(required.values())
    results = {
        "ok": ok,
        "required": [{"name": key, "ok": value} for key, value in required.items()],
        "optional": [{"name": "SMTP host", "value": host}, {"name": "SMTP port", "value": port}],
        "warnings": [],
    }

    if check_network:
        network_ok = check_smtp_network(host, port)
        results["required"].append({"name": f"{host}:{port} reachable", "ok": network_ok})
        results["ok"] = results["ok"] and network_ok

    if not results["ok"]:
        results["warnings"].append("Real sends need QQ Mail SMTP username, authorization code, recipient, and reachable SMTP network.")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
