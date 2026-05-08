---
name: send-qq-email
description: Send UTF-8 plain text or HTML email through QQ Mail SMTP. Use when Codex needs to configure, dry-run, test, or perform SMTP email delivery with QQ authorization-code credentials, including sending test messages, producing .eml snapshots, validating SMTP environment variables, or reusing a small standalone email sender in an agent workflow.
---

# Send QQ Email

## Overview

Use this skill to send or test email through QQ Mail SMTP without bringing in a larger application stack. Prefer the bundled `scripts/send_qq_email.py` script for deterministic behavior: it reads SMTP settings from environment variables or a private config file, builds a UTF-8 MIME message, optionally writes an `.eml` snapshot, and returns a structured JSON result.

## Workflow

1. Confirm the user's intent and recipient before a real send when the request is ambiguous. Use `--dry-run` for setup checks, previews, and validation tasks.
2. Load SMTP settings from environment variables or a private config file. See `references/smtp-config.md` when you need exact field names or examples.
3. Build the message content from `--test`, inline `--text` / `--html`, or file inputs.
4. Run the script from this skill directory.
5. Report the result status, recipient, output paths, and any stable error type. Do not print or commit SMTP passwords or QQ authorization codes.

## Commands

Dry-run a test message and write artifacts only:

```powershell
py scripts/send_qq_email.py --test --dry-run --output-dir artifacts/email/send-qq-email-latest
```

Send a test message using configured SMTP credentials:

```powershell
py scripts/send_qq_email.py --test --output-dir artifacts/email/send-qq-email-latest
```

Send custom content:

```powershell
py scripts/send_qq_email.py --subject "Daily report" --text-file report.txt --html-file report.html --to receiver@example.com
```

Use an explicit private config file:

```powershell
py scripts/send_qq_email.py --config "$env:USERPROFILE\.send-qq-email\email.yaml" --test
```

## Script Behavior

- Defaults to `smtp.qq.com`, port `587`, and STARTTLS when host, port, or STARTTLS are not specified.
- Requires `SMTP_USERNAME`, `SMTP_PASSWORD`, and a recipient. `SMTP_FROM` defaults to `SMTP_USERNAME`; `SMTP_TO` can be overridden by `--to`.
- Treat `SMTP_PASSWORD` as the QQ Mail authorization code, not the normal login password.
- Writes `message.eml` and `result.json` under `--output-dir` unless `--eml-output` or `--result-output` are set.
- Returns exit code `0` for `sent` or `dry_run`, `2` for configuration errors, and `3` for SMTP send failures.
- Supports simple YAML or JSON private config files with a top-level `smtp` object.

## Validation

Run the dependency and smoke checks from the skill root:

```powershell
py verify_dependencies.py
```

This compiles the sender script and performs a dry-run smoke test. It never sends a real email.
