# SMTP Config Reference

Keep real credentials outside the repository. QQ Mail SMTP uses an authorization code as `SMTP_PASSWORD`; do not use or store the normal mailbox login password.

## Manual QQ Mail Setup

QQ Mail does not allow an agent to safely automate the login, phone verification, QR verification, or authorization-code generation steps. When credentials are missing, guide the user through these manual steps before retrying the script.

Setup link:

- QQ Mail web login: <https://mail.qq.com/>

Path after login:

1. Open `Settings`.
2. Open `Account`.
3. Find `POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV service`.
4. Enable `POP3/SMTP` or `IMAP/SMTP`.
5. Complete the security verification shown by QQ Mail.
6. Copy the generated authorization code.

After the user has the authorization code, put it in `SMTP_PASSWORD`. Put the QQ mailbox address in `SMTP_USERNAME`. Never put the normal QQ login password in SMTP config.

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

`.env` example for projects that load environment variables before running this script:

```dotenv
SMTP_USERNAME=your-account@qq.com
SMTP_PASSWORD=your-qq-mail-authorization-code
SMTP_TO=receiver@example.com
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USE_STARTTLS=true
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
