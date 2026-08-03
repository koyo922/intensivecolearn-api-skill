# Intensive CoLearn API Skill

[![Validate](https://github.com/koyo922/intensivecolearn-api-skill/actions/workflows/validate.yml/badge.svg)](https://github.com/koyo922/intensivecolearn-api-skill/actions/workflows/validate.yml)
[![skills.sh](https://skills.sh/b/koyo922/intensivecolearn-api-skill)](https://skills.sh/koyo922/intensivecolearn-api-skill)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An unofficial, cross-agent Skill for the [Intensive CoLearn](https://intensivecolearn.ing/) Agent API. It gives compatible agents a safe, documented client for programs, applications, check-ins, events, profiles, collections, tags, and organizer or administrator workflows.

The bundled Python client covers all 28 operations in the official [OpenAPI document](https://intensivecolearn.ing/api/v1/openapi.json), uses only the Python standard library, redacts credentials in dry runs, and requires explicit user intent before mutations.

## Install

Install interactively into any detected compatible agent:

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api
```

Install globally without prompts:

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api --global --yes
```

The Agent Skills format works with Codex, Claude Code, Antigravity, Cursor, GitHub Copilot, and other clients supported by the [`skills` CLI](https://github.com/vercel-labs/skills).

## Configure

Create an Access Key at [Intensive CoLearn settings](https://intensivecolearn.ing/settings/access-keys), then expose it to your agent process:

```bash
export INTENSIVE_COLEARN_APIKEY="your-access-key"
```

Keep the key in a local environment or secret manager. Never commit it to a repository, paste it into a request body, or put it in a URL.

## Use

Ask your agent in normal language, for example:

```text
List the Intensive CoLearn programs that are currently accepting applications.
Show my application status for the selected program.
Check whether I am eligible to check in today, then draft the check-in for review.
List upcoming events for this program.
```

The Skill resolves resource IDs before acting, checks program lifecycle and application approval before check-in, and uses idempotency keys for mutations.

You can also test the bundled client directly from this repository:

```bash
python3 skills/intensivecolearn-api/scripts/icl_api.py --list-operations
python3 skills/intensivecolearn-api/scripts/icl_api.py get-me --status-only
python3 skills/intensivecolearn-api/scripts/icl_api.py list-programs --query page=1
```

## Capabilities

- Browse programs and inspect program details.
- Read and update the current profile.
- Apply, withdraw, and inspect application status.
- Create, update, and list personal check-ins.
- Create and manage owned programs and events.
- Review applications for programs you organize.
- Manage review queues, collections, and tags when the account has an administrator role.

## Safety

- Authentication is read only from `INTENSIVE_COLEARN_APIKEY`.
- `--dry-run` redacts the authorization header.
- `--status-only` performs health checks without printing private response data.
- Mutating actions require explicit user intent and receive an idempotency key.
- Personal and organizer responses should be treated as private.

## 中文说明

这是一个非官方、跨 Agent 的 Intensive CoLearn API Skill，覆盖官方 OpenAPI 中的全部 28 个接口。安装后可以让 Codex、Claude Code、Antigravity 等 Agent 查询共学项目、报名状态、打卡、活动和个人资料，也支持发起人及管理员工作流。

安装只需要公开 GitHub 仓库和一条命令：

```bash
npx skills add koyo922/intensivecolearn-api-skill --skill intensivecolearn-api
```

Access Key 只通过本地环境变量 `INTENSIVE_COLEARN_APIKEY` 读取，不会写入 Skill、URL 或请求正文。涉及报名、打卡、修改、审核或删除时，Skill 会要求明确的用户意图。

## Project status

This project is community-maintained and is not affiliated with or endorsed by Intensive CoLearn. API behavior is defined by the upstream service and may change. See [LICENSE](LICENSE).
