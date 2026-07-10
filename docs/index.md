# QQ 邮件发送

`send-qq-email` 是一个轻量 SMTP skill，用来通过 QQ 邮箱发送 UTF-8 文本 / HTML 邮件，或在不真实发送的情况下生成 `.eml` 快照和结构化结果。

## 逻辑视图

这个 skill 由决策层、配置层、执行层和交付层组成：

| 层次 | 核心概念与边界 |
| --- | --- |
| 决策层 | 主 Agent 理解用户 prompt，区分配置检查、预览与真实发送；真实发送意图或收件人不明确时，先请求人工确认。 |
| 配置层 | SMTP 配置来自显式 `--config`、`SEND_QQ_EMAIL_CONFIG`、默认私有配置文件或环境变量。授权码只从仓库外读取。 |
| 执行层 | `scripts/send_qq_email.py` 负责校验发送参数、构造 MIME 邮件、写入快照，并按参数执行 dry-run 或连接 SMTP；它不负责决定是否应当真实发送。 |
| 依赖检查 | `verify_dependencies.py` 只检查 SMTP 用户名、授权码和默认收件人是否已配置；仅在显式传入 `--check-network` 时额外检查 SMTP 地址的 TCP 连通性。它不编译脚本，也不执行 dry-run smoke test。 |
| 交付层 | `.tmp/send-qq-email/<task>/message.eml` 保存邮件快照，`result.json` 保存结构化结果。 |

主要输入是发送模式、收件人、主题、文本或 HTML 正文、可选附件与私有 SMTP 配置；主要输出是 `.eml` 快照和结果 JSON。脚本不会代替用户完成 QQ 登录、安全验证或授权码生成，也不应把凭据写进交付物。

## 运行视图

从用户请求到交付物的主路径如下：

```text
用户 prompt
  -> 主 Agent 判断配置检查 / dry-run / 真实发送
  -> [真实发送信息不明确] 人工确认发送意图和收件人
  -> 从仓库外读取 SMTP 配置
  -> 发送脚本校验配置与邮件输入
  -> 构造 MIME 邮件并写入 message.eml
  -> [dry-run] 不连接 SMTP，写入 dry_run 结果
  -> [真实发送] 连接 QQ SMTP，写入 sent 或 failed 结果
  -> 主 Agent 汇报 result.json 中的状态、收件人和产物路径
```

配置检查可在发送流程之前独立运行。默认检查不访问网络；只有用户或主 Agent 明确需要验证网络前置条件时，才运行 `verify_dependencies.py --check-network`。网络可达只说明能够建立 TCP 连接，不验证账号能否登录或邮件能否投递。

## 开发视图

| 目录或文件 | 分层职责 |
| --- | --- |
| `SKILL.md` | Agent 入口和工作流约束，包括真实发送确认与凭据保护规则。 |
| `docs/` | 面向文档站的能力展示、使用方式、依赖说明和架构概览。 |
| `references/smtp-config.md` | SMTP 字段、QQ 邮箱人工设置步骤和私有配置格式参考。 |
| `verify_dependencies.py` | 外部配置与可选网络连通性检查入口。 |
| `scripts/send_qq_email.py` | 邮件构造、快照写入、dry-run、SMTP 发送和结构化结果实现。 |

文档负责说明行为，发送脚本负责实现行为；`verify_dependencies.py` 只判断外部前置条件，不替代发送脚本的参数校验，也不承担仓库代码健康检查。

## 多 Agent 职责边界

该 skill 默认由一个主 Agent 完成，不要求启动子 Agent、checker 或 reviewer。

| 角色 | 职责 | 禁止事项与交接边界 |
| --- | --- | --- |
| 主 Agent | 理解请求、选择配置检查或发送模式、收集人工确认、调用脚本并汇报产物。 | 不自动生成授权码，不输出凭据；没有明确授权时不把任务升级为真实发送。 |
| 用户 | 提供仓库外的 SMTP 配置，并在真实发送信息不明确时确认发送意图和收件人。 | 不应把授权码写入仓库、prompt 交付物或公开日志。 |
| 发送脚本 | 接收已经确定的参数和配置，生成邮件及结构化结果。 | 不做业务决策，不与用户交互，不自行选择收件人。 |
| 可选子 Agent / checker | 本 skill 没有默认职责或必需交接物；只有上层任务另有明确要求时才参与外围内容复核。 | 不接触 SMTP 授权码，不执行真实发送，不改变主 Agent 的确认责任。 |

## 配置来源

脚本按以下方式读取 SMTP 配置：

1. 显式 `--config` 文件。
2. `SEND_QQ_EMAIL_CONFIG` 指向的私有配置文件。
3. 默认私有配置：`~/.send-qq-email/email.yaml`。
4. 环境变量覆盖配置文件字段。

真实凭据不应写入仓库。QQ 邮箱 SMTP 使用授权码作为 `SMTP_PASSWORD`，不是 QQ 登录密码。

## 设计边界

- 配置检查、预览和验证默认使用 dry-run。
- 真实发送前，如果收件人或意图不明确，Agent 应先确认。
- 脚本可以写 `.eml` 和 `result.json`，但不记录 SMTP 密码或授权码。
- 输出目录在主工作区中应放到 `.tmp/send-qq-email/` 下。

## 输出契约

脚本会在输出目录写入：

```text
.tmp/send-qq-email/<task>/
|-- message.eml
`-- result.json
```

`result.json` 用固定字段表达发送状态，包括 `status`、`recipient`、`sent_at`、`error_type`、`error_summary`、`message_id`、`eml_path` 和 `dry_run`。

真实发送失败时也会保留 `.eml`，方便复核邮件内容是否正确。
