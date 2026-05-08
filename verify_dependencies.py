#!/usr/bin/env python3
"""Verify runtime prerequisites for the send-qq-email skill."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "scripts" / "send_qq_email.py"


def main() -> int:
    py_compile.compile(str(SCRIPT), doraise=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "email.yaml"
        output_dir = Path(temp_dir) / "out"
        config_path.write_text(
            "\n".join(
                [
                    "smtp:",
                    "  username: sender@qq.com",
                    "  password: fake-authorization-code",
                    "  to_address: receiver@example.com",
                    "  from_name: Codex",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--config",
                str(config_path),
                "--test",
                "--dry-run",
                "--output-dir",
                str(output_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            return result.returncode

        payload = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
        if payload.get("status") != "dry_run":
            print(f"Unexpected smoke-test status: {payload}", file=sys.stderr)
            return 1
        if not (output_dir / "message.eml").exists():
            print("Dry-run did not write message.eml", file=sys.stderr)
            return 1

    print("send-qq-email dependencies verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
