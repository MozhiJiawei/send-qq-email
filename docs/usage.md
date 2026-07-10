# 使用方式

这个 skill 面向 Agent 原生工作流：你描述要发什么、发给谁、是否只是预览，Agent 负责检查配置、生成邮件快照和执行发送。

## 典型 Prompt

- `请用 QQ 邮箱 SMTP dry-run 一封测试邮件，并把 .eml 快照写到 .tmp/send-qq-email/。`
- `请检查我的 QQ 邮箱 SMTP 环境变量是否齐全，不要真实发送邮件。`
- `请把这段日报内容通过 QQ 邮箱发给我指定的收件人；发送前先确认收件人。`

## 推荐流程

1. 明确这是 dry-run、配置检查，还是真实发送。
2. 真实发送前确认收件人和发送意图。
3. 从环境变量或私有配置文件读取 SMTP 设置。
4. 构造 UTF-8 MIME 邮件。
5. 写入 `.eml` 快照和 `result.json`。
6. dry-run 到此结束；真实发送则继续连接 `smtp.qq.com`。

## 必要配置

| 字段 | 说明 |
| --- | --- |
| `SMTP_USERNAME` | QQ 邮箱地址。 |
| `SMTP_PASSWORD` | QQ 邮箱 SMTP 授权码，不是登录密码。 |
| `SMTP_TO` | 默认收件人，也可用 `--to` 覆盖。 |

更多配置字段见子仓 `references/smtp-config.md`。

## 脚本入口

以下命令都从 workspace 根目录运行。dry-run 仍需从环境变量或私有配置文件读取 `SMTP_USERNAME`、`SMTP_PASSWORD` 和收件人，但不会连接 SMTP。所有产物都写入 `.tmp/send-qq-email/`。

先查看帮助，不读取配置也不发送邮件：

```powershell
python skills/send-qq-email/scripts/send_qq_email.py --help
```

dry-run 测试邮件：

```powershell
python skills/send-qq-email/scripts/send_qq_email.py `
  --test `
  --dry-run `
  --output-dir .tmp/send-qq-email/test
```

dry-run 自定义正文：

```powershell
python skills/send-qq-email/scripts/send_qq_email.py `
  --subject "Daily report" `
  --text "This is a dry-run daily report." `
  --to receiver@example.com `
  --dry-run `
  --output-dir .tmp/send-qq-email/daily-report
```

使用私有配置文件：

```powershell
python skills/send-qq-email/scripts/send_qq_email.py `
  --config "$env:USERPROFILE\.send-qq-email\email.yaml" `
  --test `
  --dry-run `
  --output-dir .tmp/send-qq-email/config-check
```

## 依赖检查

从 workspace 根目录检查 SMTP 配置：

```powershell
python skills/send-qq-email/verify_dependencies.py
```

需要时可显式增加网络连通性检查：

```powershell
python skills/send-qq-email/verify_dependencies.py --check-network
```

默认检查只读取外部 SMTP 配置，确认 `SMTP_USERNAME`、`SMTP_PASSWORD` 和 `SMTP_TO` 是否存在；`--check-network` 还会尝试连接配置的 SMTP 主机和端口。该入口不会编译发送脚本、不会生成邮件，也不会执行 dry-run smoke test。

## 输入与输出

| 项目 | 说明 |
| --- | --- |
| 输入 | 发送模式、收件人、主题、文本或 HTML 正文、可选附件，以及仓库外的 SMTP 配置。 |
| 输出 | `.tmp/send-qq-email/<task>/message.eml` 和 `.tmp/send-qq-email/<task>/result.json`。 |
| 临时目录 | workspace 根目录下的 `.tmp/send-qq-email/`；不要把凭据或邮件临时产物写入 skill 子仓。 |

## 完成标准

- `--help` 能正常显示命令参数，或 dry-run 返回 `status: dry_run`。
- `.eml` 与 `result.json` 写入指定的 `.tmp/send-qq-email/<task>/`。
- 主 Agent 汇报模式、收件人、结果状态和产物路径，但不显示 SMTP 授权码。
- 若为真实发送，发送意图和收件人已经明确；若信息不明确，已经由用户人工确认。

本 skill 默认不需要子 Agent 或 checker；普通调用无需为此额外授权。
