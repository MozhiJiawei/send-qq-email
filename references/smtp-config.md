# SMTP Config Reference

Keep real credentials outside the repository. QQ Mail SMTP uses an authorization code as `SMTP_PASSWORD`; do not use or store the normal mailbox login password.

## Environment Variables

Required:

- `SMTP_USERNAME`: QQ mailbox account, usually `name@qq.com`
- `SMTP_PASSWORD`: QQ Mail authorization code
- `SMTP_TO`: default recipient, unless the command passes `--to`

Optional:

- `SMTP_HOST`: defaults to `smtp.qq.com`
- `SMTP_PORT`: defaults to `587`
- `SMTP_FROM`: defaults to `SMTP_USERNAME`
- `SMTP_FROM_NAME`: display name in the From header
- `SMTP_TIMEOUT_SECONDS`: defaults to `20`
- `SMTP_USE_STARTTLS`: defaults to `true`; set `false` only for a provider that does not use STARTTLS
- `SEND_QQ_EMAIL_CONFIG`: explicit private config path

PowerShell example:

```powershell
$env:SMTP_USERNAME = "your-account@qq.com"
$env:SMTP_PASSWORD = "your-qq-mail-authorization-code"
$env:SMTP_TO = "receiver@example.com"
```

## Private YAML Config

Default path:

```text
~/.send-qq-email/email.yaml
```

Example:

```yaml
smtp:
  host: smtp.qq.com
  port: 587
  username: your-account@qq.com
  password: your-qq-mail-authorization-code
  from_address: your-account@qq.com
  from_name: Codex
  to_address: receiver@example.com
  timeout_seconds: 20
  use_starttls: true
```

Environment variables override values from this file.
