# ICL Agent API Reference

Source of truth: [official OpenAPI document](https://intensivecolearn.ing/api/v1/openapi.json), version `1.2.0`, server `https://intensivecolearn.ing/api/v1`.

The API returns an envelope shaped like `{"apiVersion":"v1","data":...}` for object/list responses. All operations use `Authorization: Bearer <Access Key>`. Mutating operations that declare `Idempotency-Key` require a value matching `^[A-Za-z0-9._:-]+$`, 8-128 characters.

## Public notes outside the Agent API

As verified on 2026-08-04, OpenAPI `1.2.0` has no operation for other learners' notes, selected excellent notes, or note rankings. Do not invent an API endpoint for them.

The public website may expose two excellent-note sections on a program page: daily selections and final selections. It embeds the selected note content in the public page. Programs using `PUBLIC_GITHUB` may also expose their repository, commonly with learner Markdown files under `notes/`.

Use `scripts/icl_public_notes.py` for these sources. It is deliberately separate from `icl_api.py`, requires no ICL Access Key, performs only GET requests, and marks output with `officialAgentApi: false`. Website parsing is best-effort because it is not a versioned API contract. Public GitHub notes are broader than official selections and must not be described as award-winning unless the ICL page selected them.

## Public and personal resources

| Client operation | HTTP path | Purpose |
|---|---|---|
| `list-programs` | `GET /programs` | List website-visible programs. Query: `page`, `query`. |
| `get-program` | `GET /programs/{programId}` | Read a program, creator, application form, and authoritative `viewerApplication` for the current user. |
| `get-me` | `GET /me` | Read the current user profile and role. |
| `update-me` | `PATCH /me` | Update `email` and/or `walletAddress`. |
| `list-own-programs` | `GET /me/programs` | List programs editable by the current user. Query: `page`, `pageSize` (1-20). |
| `list-own-applications` | `GET /me/applications` | List the current user's applications. Query: `page`, `pageSize` (1-20). |
| `create-own-application` | `POST /me/applications` | Apply with `programId`, optional `answers`, `motivation`, and `timezone`. |
| `withdraw-own-application` | `POST /me/applications/{applicationId}/withdraw` | Withdraw an application. |
| `list-own-checkins` | `GET /me/check-ins` | List current user's notes. Query: `page`, `pageSize`, optional `programId`. |
| `create-own-checkin` | `POST /me/check-ins` | Create a note with `programId` and `content`. |
| `update-own-checkin` | `PATCH /me/check-ins/{checkinId}` | Replace a note's `content`. |

### Check-in preflight

Before `create-own-checkin`, call `get-program` for the exact target and verify both conditions:

1. The program has started. A `registering` program is not check-in eligible even when the application is approved; the API returns `403 forbidden` with `共学尚未开始，暂时不能打卡。`
2. `data.viewerApplication.status` is `approved`.

Use `get-program.data.viewerApplication` rather than filtering `/me/applications` by `programId`. The OpenAPI schema does not require `programId` in application list items, and the production response may omit it.

## Organizer resources

| Client operation | HTTP path | Purpose |
|---|---|---|
| `create-own-program` | `POST /me/programs` | Create a program. Requires the explicit note access fields below. |
| `update-own-program` | `PATCH /me/programs/{programId}` | Update an owned program; send `updatedAt` and changed fields. |
| `list-program-applications` | `GET /programs/{programId}/applications` | List applications for an owned/authorized program. Query: `page`, `pageSize`. |
| `review-program-application` | `POST /programs/{programId}/applications/{applicationId}/review` | Body: `{"status":"approved"}` or `{"status":"rejected"}`. |
| `list-program-events` | `GET /programs/{programId}/events` | List visible events. |
| `create-program-event` | `POST /programs/{programId}/events` | Body: `title`, `content`, `startsAt` (`YYYY-MM-DDTHH:mm`), `meetingUrl`. |
| `cancel-program-event` | `POST /programs/{programId}/events/{eventId}/cancel` | Cancel an event. |

### Program creation fields

Required: `noteAccessMode`, `name`, `description`, `courseInfo`, `language`, `registrationEnabled`, `signupStartAt`, `signupEndAt`, `startDate`, `endDate`, `durationWeeks`, `leaveAllowancePerWeek`, `targetAudience`, `tags`, `communityInfo`, `collectionSlug`, and `noteAccessAcknowledgement`.

- `noteAccessMode`: `PRIVATE_COHORT` or `PUBLIC_GITHUB`.
- Matching acknowledgement: `PRIVATE_COHORT_NOTES_CONFIRMED` or `PUBLIC_GITHUB_PUBLICATION_CONFIRMED`.
- `language`: `中文` or `English`.
- Lifecycle dates are UTC+8 calendar dates. `durationWeeks` is 1-52 or null; `leaveAllowancePerWeek` is 0-7.
- Optional fields include `communityInfoPublic`, `applicationForm`, `highlightConfig`, and `collectionSlug`. `highlightConfig.timezone` must be `UTC+8`.

## Administrator resources

These require an appropriate `admin` role. Do not use them unless the user explicitly asks for administrative work.

| Client operation | HTTP path | Purpose |
|---|---|---|
| `list-programs-for-review` | `GET /admin/programs/review` | List programs by `status` (`pending`, `approved`, `featured`, `rejected`). |
| `review-program` | `POST /admin/programs/{programId}/review` | Body status: `approved`, `featured`, or `rejected`. |
| `list-admin-collections` | `GET /admin/collections` | List collection catalog. |
| `create-admin-collection` | `POST /admin/collections` | Body: `name`, slug. |
| `update-admin-collection` | `PATCH /admin/collections/{collectionId}` | Update collection `name` and/or `slug`. |
| `delete-admin-collection` | `DELETE /admin/collections/{collectionId}` | Delete a collection. |
| `list-admin-tags` | `GET /admin/tags` | List tag catalog. |
| `create-admin-tag` | `POST /admin/tags` | Body: `tag`. |
| `update-admin-tag` | `PATCH /admin/tags/{tagId}` | Rename a tag with body `{"tag":"..."}`. |
| `delete-admin-tag` | `DELETE /admin/tags/{tagId}` | Delete an unused tag. |

## Website workflow facts

The public [Handbook](https://intensivecolearn.ing/handbook) documents the user workflow: GitHub login, program discovery, application, daily Markdown check-in, visible progress, and organizer creation. It describes 21-day programs, up to two leave days per week, and persistent public notes by default; the API's `noteAccessMode` is the authoritative setting for new program creation.

Community projects such as [intensivecolearn-bot](https://github.com/easyshellworld/intensivecolearn-bot) and [IntensiveColearnCheckin](https://github.com/atomlink-ye/IntensiveColearnCheckin) are not official API clients. The former manages Telegram/GitHub statistics; the latter is an independent on-chain check-in DApp. Do not substitute their interfaces for the official Agent API.
