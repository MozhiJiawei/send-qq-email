# 依赖说明

使用这个 skill 前，请先让 Agent 跑依赖检查。依赖状态以子仓根目录的 `verify_dependencies.py` 输出为准；文档只说明它会检查什么。

## 让 Agent 先做什么

你可以直接这样说：

```text
我要使用 send-qq-email，请先检查邮件发送依赖；如果 QQ 邮箱 SMTP 凭据或网络前置条件没有准备好，请提示我补齐。
```

## 检查命令

在 workspace 根目录运行：

```powershell
python skills/send-qq-email/verify_dependencies.py
```

## 它会检查什么

| 类型 | 说明 |
| --- | --- |
| 必需：SMTP 配置 | 检查 `SMTP_USERNAME`、`SMTP_PASSWORD` 和 `SMTP_TO` 是否存在；配置可来自环境变量、`SEND_QQ_EMAIL_CONFIG` 指向的文件或默认私有配置文件。 |
| 可选：SMTP 网络 | 仅在传入 `--check-network` 时，尝试连接配置的 SMTP 主机和端口；默认值是 `smtp.qq.com:587`。 |

它不会扫描仓库文件、编译发送脚本、生成 `.eml`、执行 dry-run smoke test，也不会验证 SMTP 登录或邮件投递。网络检查只反映 TCP 连接是否可建立。

## 判断标准

默认依赖检查通过，表示三个必需 SMTP 配置项已提供；只有使用 `--check-network` 并通过时，才同时表示目标 SMTP 地址在检查时可建立 TCP 连接。真实发送前，还需要让 Agent 确认 SMTP 用户名、授权码、收件人和发送意图。
