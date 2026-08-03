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
3. If required SMTP configuration is missing, stop and give the user the QQ Mail setup link, the manual authorization-code steps, and the exact place to paste the code. Do not ask them to "configure SMTP" generically.
4. Build the message content from `--test`, inline `--text` / `--html`, or file inputs.
5. Run the script from this skill directory.
6. Report the result status, recipient, output paths, and any stable error type. Do not print or commit SMTP passwords or QQ authorization codes.

## Missing Configuration Guidance

When `SMTP_USERNAME`, `SMTP_PASSWORD`, or the recipient is missing, tell the user:

- Open QQ Mail: <https://mail.qq.com/>
- In QQ Mail web settings, go to `Settings` / `Account` / `POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV service`.
- Enable `POP3/SMTP` or `IMAP/SMTP`, complete the phone or QR verification, then copy the generated authorization code.
- Paste the mailbox address into `SMTP_USERNAME`.
- Paste the authorization code into `SMTP_PASSWORD`; do not use the normal QQ password.
- Put the recipient in `SMTP_TO`, or pass `--to recipient@example.com` on the command line.

Show one concrete fill-in location. Prefer the private config file for this standalone skill:

```yaml
# ~/.send-qq-email/email.yaml
smtp:
  username: your-account@qq.com
  password: paste-qq-mail-authorization-code-here
  to_address: receiver@example.com
```

If the surrounding project already uses `.env`, show the equivalent keys:

```dotenv
SMTP_USERNAME=your-account@qq.com
SMTP_PASSWORD=paste-qq-mail-authorization-code-here
SMTP_TO=receiver@example.com
```

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

