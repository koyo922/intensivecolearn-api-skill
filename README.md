# Intensive CoLearn API Skill（残酷共学 Agent Skill）

[![Validate](https://github.com/koyo922/intensivecolearn-api-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/koyo922/intensivecolearn-api-skill/actions/workflows/validate.yml)
[![Install from skills.sh](https://img.shields.io/badge/skills.sh-Install-111111)](https://skills.sh/koyo922/intensivecolearn-api-skill/intensivecolearn-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

这是一个非官方、跨 Agent 的 [Intensive CoLearn（残酷共学）](https://intensivecolearn.ing/) Skill。安装后，Codex、Claude Code、Antigravity、Cursor、GitHub Copilot 等兼容 Agent 可以帮助你查询共学项目、报名和打卡，也能浏览官网评选的优秀学习笔记及公开 GitHub 笔记，从其他学习者的实践中提炼方法。

> **重要来源说明：**报名、打卡等操作使用官方 Agent API；“优秀学习笔记”和公开笔记读取来自 ICL 公开网页及公开 GitHub 仓库，**不是官方 Agent API 接口**。公共笔记能力只读、不需要 ICL Access Key，并且不会绕过“学员私享”权限。

## 最简单的使用方式：把这个 README 交给你的 Agent

如果要查询个人状态、报名或打卡，你只需要先创建一个 ICL Access Key，剩下的安装、配置指导和验证工作可以交给本地 Agent。只浏览公开优秀笔记时不需要 Key。

### 1. 创建 Access Key

1. 登录 [Intensive CoLearn](https://intensivecolearn.ing/)。
2. 打开 [Access Keys 设置页](https://intensivecolearn.ing/settings/access-keys)。
3. 创建并妥善保存 Access Key。

不要把 Access Key 直接粘贴到 Agent 对话、Issue、截图或代码仓库中；请通过本地环境变量或 Secret Manager 提供给 Agent 进程。

### 2. 把 README 链接发给 Agent

将下面这段话发给你的本地 Agent：

```text
请阅读并按照这个 README 帮我安装 Intensive CoLearn API Skill：
https://github.com/koyo922/intensivecolearn-api-skill

请完成以下工作：
1. 安装 intensivecolearn-api Skill，并适配我当前使用的 Agent。
2. 引导我登录 https://intensivecolearn.ing/settings/access-keys 创建 Access Key。
3. 引导我把 Key 安全地配置到本地环境变量 INTENSIVE_COLEARN_APIKEY；不要在聊天、日志、命令输出或仓库中打印 Key。
4. 安装后运行 get-me --status-only，只返回连接是否成功和 HTTP 状态码。
5. 验证公共笔记能力：列出一个公开共学项目的优秀学习笔记，并读取其中一篇；明确说明该能力来自公开网页或 GitHub，不是官方 Agent API。
6. 如果验证成功，告诉我现在可以让你查询项目、学习优秀笔记、查看报名状态或执行打卡等操作。
```

Agent 可以阅读本仓库中的 `SKILL.md` 和 API 参考文档，自行完成后续步骤。涉及报名、打卡、修改、审核或删除等写操作时，Agent 应先向你确认目标和内容。

## 重点能力：学习他人的优秀笔记

你可以直接把 ICL 项目链接交给 Agent：

```text
列出这个残酷共学项目的优秀学习笔记，选择最值得学习的三篇，
比较它们的研究方法、证据质量和可复用框架，并附上原文链接。
```

Skill 会优先读取项目页中的“每日优秀学习笔记”和“结营优秀学习笔记”。如果项目明确公开到 GitHub，还可以浏览仓库中的其他公开 Markdown 笔记。对于“学员私享”的项目，Skill 只读取官网已经公开展示的优秀笔记；若发起人尚未启用评选，则如实返回不可用，不尝试绕过权限。

这个能力使用公开网页和公开 GitHub 数据，不属于官方 Agent API。网页结构未来可能变化，因此脚本在无法确认解析结果时会报告兼容性错误，不会把解析失败误报为“没有优秀笔记”。

手动调用示例：

```bash
python3 skills/intensivecolearn-api/scripts/icl_public_notes.py inspect-program PROGRAM_ID
python3 skills/intensivecolearn-api/scripts/icl_public_notes.py list-highlights PROGRAM_ID
python3 skills/intensivecolearn-api/scripts/icl_public_notes.py get-highlight PROGRAM_ID HIGHLIGHT_ID
python3 skills/intensivecolearn-api/scripts/icl_public_notes.py list-public-notes OWNER/REPO --limit 30
python3 skills/intensivecolearn-api/scripts/icl_public_notes.py get-public-note OWNER/REPO notes/AUTHOR.md
```

## Access Key 配置原则

Skill 只从环境变量 `INTENSIVE_COLEARN_APIKEY` 读取凭据。

在 macOS/Linux 的 zsh 环境中，可以把下面一行加入本机 `~/.zshrc`，然后重新打开终端或执行 `source ~/.zshrc`：

```bash
export INTENSIVE_COLEARN_APIKEY="你的 Access Key"
```

请注意：

- 不要把真实 Key 写入 README、Skill 文件或 Git 仓库。
- 不要直接在 Agent 对话中发送 Key；让 Agent 引导你在本机完成环境变量配置。
- 不要把 Key 放进 URL、API 请求正文、截图或 Agent 回复。
- 不要要求 Agent 回显 Key。只需让它检查变量是否存在并执行 `--status-only` 验证。
- 团队或云端环境应优先使用对应平台的 Secret Manager，而不是共享 shell 配置文件。

## 手动安装

通常把 README 交给 Agent 即可。如果需要手动安装，可以运行：

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api
```

全局安装且跳过交互确认：

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api --global --yes
```

本项目采用开放的 [Agent Skills](https://agentskills.io/) 格式，并通过 [`skills` CLI](https://github.com/vercel-labs/skills) 分发。

## 可以让 Agent 做什么

- 浏览共学项目并读取项目详情。
- 查看官网评选的每日及结营优秀学习笔记，读取原文并总结、比较学习方法。
- 浏览明确公开到 GitHub 的共学笔记。
- 查询当前用户资料和报名状态。
- 报名或退出共学项目。
- 在满足项目开始时间和报名审核条件后创建、更新和查询打卡。
- 查询、创建或取消项目活动。
- 管理自己发起的共学项目并审核报名。
- 在账号具备管理员权限时管理审核队列、合集和标签。

你可以直接这样对 Agent 说：

```text
帮我看看现在有哪些正在报名的残酷共学项目。
找出这个项目的优秀学习笔记，比较前三名为什么值得学习。
从这个公开共学仓库里找几篇高质量笔记，提炼一份学习框架。
查询我在这个项目里的报名状态。
先检查今天是否可以打卡，然后帮我起草一份打卡内容供我确认。
列出这个共学项目接下来的活动。
```

## 技术信息与安全边界

- Python 客户端覆盖官方 [OpenAPI 文档](https://intensivecolearn.ing/api/v1/openapi.json)中的全部 28 个接口。
- 独立的公共笔记客户端读取公开 ICL 项目页和公开 GitHub 仓库；它不是官方 Agent API，也不需要 ICL Access Key。
- 客户端只使用 Python 标准库，没有第三方运行时依赖。
- `--dry-run` 会隐藏 Authorization Header。
- `--status-only` 可验证连接而不打印个人资料。
- 写操作使用幂等键，并要求 Agent 先获得明确用户意图。
- 打卡前会检查项目是否已经开始，以及报名状态是否为 `approved`。

也可以从仓库源码直接运行客户端：

```bash
python3 skills/intensivecolearn-api/scripts/icl_api.py --list-operations
python3 skills/intensivecolearn-api/scripts/icl_api.py get-me --status-only
python3 skills/intensivecolearn-api/scripts/icl_api.py list-programs --query page=1
```

---

## English

This is an unofficial, cross-agent Skill for [Intensive CoLearn](https://intensivecolearn.ing/). It covers all 28 operations in the official Agent API and can also read selected excellent notes from public ICL program pages and Markdown notes from public project repositories.

Public-note discovery is read-only, requires no ICL Access Key, and is **not an official Agent API feature**. It does not bypass private-cohort access.

The easiest setup is to send this repository URL to your local agent and ask it to install the Skill, guide you through creating an Access Key at [ICL Access Keys settings](https://intensivecolearn.ing/settings/access-keys), configure `INTENSIVE_COLEARN_APIKEY` securely, and verify the connection with `get-me --status-only`.

Manual installation:

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api
```

Never paste the Access Key into public chats, logs, screenshots, URLs, request bodies, or repositories. Mutating operations require explicit user intent.

## Project status

This project is community-maintained and is not affiliated with or endorsed by Intensive CoLearn. API behavior is defined by the upstream service and may change. See [LICENSE](LICENSE).
