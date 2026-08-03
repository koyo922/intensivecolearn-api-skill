---
name: intensivecolearn-api
description: Use the Intensive CoLearn (ICL) Agent API to inspect and manage programs, applications, check-ins, events, profiles, collections, tags, and administrator review workflows. Trigger when a task mentions intensivecolearn.ing, ICL Access Keys,残酷共学 API,共学报名/打卡/发起, or the INTENSIVE_COLEARN_APIKEY environment variable.
---

# Intensive CoLearn API

Use the official ICL Agent API at `https://intensivecolearn.ing/api/v1`. Read [references/api.md](references/api.md) when selecting an endpoint or constructing a request.

## Authentication

- Read the opaque Access Key only from `INTENSIVE_COLEARN_APIKEY`.
- If the variable is defined in `~/.zshrc` without `export`, run `source ~/.zshrc && export INTENSIVE_COLEARN_APIKEY` in the invoking shell; do not copy the value into a file.
- Send it as `Authorization: Bearer $INTENSIVE_COLEARN_APIKEY`.
- Never print, log, persist, commit, or include the key in URLs, request bodies, screenshots, or reports.
- Treat responses from `/me`, applications, and organizer/admin endpoints as potentially private. Return only the fields needed for the task.

## Use the bundled client

Run `scripts/icl_api.py` with Python 3. It uses only the standard library and maps named operations to the official API paths:

```bash
python3 scripts/icl_api.py list-programs --query query=AI --query page=1
python3 scripts/icl_api.py get-program --param programId=PROGRAM_ID
python3 scripts/icl_api.py list-own-checkins --query programId=PROGRAM_ID
python3 scripts/icl_api.py create-own-checkin --data '{"programId":"PROGRAM_ID","content":"今日学习记录"}'
```

Use `--data-file FILE` for larger JSON bodies, `--idempotency-key KEY` when a caller needs a stable retry key, `--status-only` for a health check without printing response data, and `--dry-run` to inspect the request without sending it. Use `--list-operations` to see every mapped operation.

Mutating operations require explicit user intent. Before applying, reviewing, publishing, editing, deleting, withdrawing, canceling, or creating anything, confirm the target and payload; do not turn a read-only question into a write. The client generates a per-request idempotency key for mutating calls unless one is supplied.

## Workflow

1. Start with a read-only operation such as `list-programs`, `get-program`, `get-me`, or a list operation.
2. Resolve IDs from the response rather than guessing them.
3. Validate required fields and role constraints against [references/api.md](references/api.md).
4. Use the narrowest operation and send JSON only for fields being changed.
5. For retries of a mutation, reuse the same `--idempotency-key`.
6. On `401`, report that the key is missing/invalid/expired without exposing it. On `403`, report that the current website role or resource permission is insufficient. On `409`/`412`, preserve the server conflict details and do not retry blindly.

## Important semantics

- All program lifecycle dates are UTC+8 calendar dates in `YYYY-MM-DD`.
- Program creation requires an explicit `noteAccessMode` and matching acknowledgement. `PRIVATE_COHORT` keeps notes in the website; `PUBLIC_GITHUB` explicitly publishes the repository.
- Check-in content is Markdown-capable and limited to 20,000 characters by the API contract.
- Before creating a check-in, call `get-program` and verify that the program has started and `viewerApplication.status` is `approved`. The service rejects early check-ins with `403 forbidden` and `共学尚未开始，暂时不能打卡。`
- Treat `get-program.data.viewerApplication` as the authoritative application state for a specific program. Items returned by `/me/applications` may omit `programId`, so do not rely on client-side filtering by that optional field.
- Public directory operations and authenticated operations share the same `/api/v1` base, but the OpenAPI contract marks every operation as Bearer-authenticated. Use the Access Key for all calls made through this Skill.
