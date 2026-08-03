#!/usr/bin/env python3
"""Small standard-library client for the Intensive CoLearn Agent API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE = "https://intensivecolearn.ing/api/v1"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

OPERATIONS: dict[str, tuple[str, str]] = {
    "get-me": ("GET", "/me"),
    "update-me": ("PATCH", "/me"),
    "list-programs": ("GET", "/programs"),
    "get-program": ("GET", "/programs/{programId}"),
    "list-own-programs": ("GET", "/me/programs"),
    "create-own-program": ("POST", "/me/programs"),
    "update-own-program": ("PATCH", "/me/programs/{programId}"),
    "list-own-applications": ("GET", "/me/applications"),
    "create-own-application": ("POST", "/me/applications"),
    "withdraw-own-application": ("POST", "/me/applications/{applicationId}/withdraw"),
    "list-own-checkins": ("GET", "/me/check-ins"),
    "create-own-checkin": ("POST", "/me/check-ins"),
    "update-own-checkin": ("PATCH", "/me/check-ins/{checkinId}"),
    "list-program-applications": ("GET", "/programs/{programId}/applications"),
    "review-program-application": ("POST", "/programs/{programId}/applications/{applicationId}/review"),
    "list-program-events": ("GET", "/programs/{programId}/events"),
    "create-program-event": ("POST", "/programs/{programId}/events"),
    "cancel-program-event": ("POST", "/programs/{programId}/events/{eventId}/cancel"),
    "list-programs-for-review": ("GET", "/admin/programs/review"),
    "review-program": ("POST", "/admin/programs/{programId}/review"),
    "list-admin-collections": ("GET", "/admin/collections"),
    "create-admin-collection": ("POST", "/admin/collections"),
    "update-admin-collection": ("PATCH", "/admin/collections/{collectionId}"),
    "delete-admin-collection": ("DELETE", "/admin/collections/{collectionId}"),
    "list-admin-tags": ("GET", "/admin/tags"),
    "create-admin-tag": ("POST", "/admin/tags"),
    "update-admin-tag": ("PATCH", "/admin/tags/{tagId}"),
    "delete-admin-tag": ("DELETE", "/admin/tags/{tagId}"),
}


def parse_pairs(values: list[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise ValueError(f"{label} must use NAME=VALUE: {item}")
        name, value = item.split("=", 1)
        if not name:
            raise ValueError(f"{label} name cannot be empty")
        result[name] = value
    return result


def read_json(args: argparse.Namespace) -> Any | None:
    if args.data is not None and args.data_file is not None:
        raise ValueError("Use only one of --data and --data-file")
    raw: str | None = args.data
    if args.data_file:
        raw = sys.stdin.read() if args.data_file == "-" else Path(args.data_file).read_text(encoding="utf-8")
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"request body is not valid JSON: {exc}") from exc


def render_path(template: str, params: dict[str, str]) -> str:
    required = [part[1:-1] for part in template.split("/") if part.startswith("{") and part.endswith("}")]
    missing = [name for name in required if name not in params]
    if missing:
        raise ValueError("missing --param " + ", ".join(f"{name}=..." for name in missing))
    return template.format(**params)


def output_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Call the Intensive CoLearn Agent API without exposing the Access Key.")
    parser.add_argument("operation", nargs="?", choices=sorted(OPERATIONS))
    parser.add_argument("--list-operations", action="store_true")
    parser.add_argument("--base-url", default=os.environ.get("INTENSIVE_COLEARN_API_BASE", DEFAULT_BASE))
    parser.add_argument("--user-agent", default=os.environ.get("INTENSIVE_COLEARN_USER_AGENT", DEFAULT_USER_AGENT), help=argparse.SUPPRESS)
    parser.add_argument("--param", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--query", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--data", help="JSON request body")
    parser.add_argument("--data-file", metavar="FILE", help="Read JSON request body from FILE, or - for stdin")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--status-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list_operations:
        for name, (method, path) in sorted(OPERATIONS.items()):
            print(f"{name}\t{method}\t{path}")
        return 0
    if not args.operation:
        parser.error("operation is required unless --list-operations is used")

    try:
        method, template = OPERATIONS[args.operation]
        params = parse_pairs(args.param, "--param")
        query = parse_pairs(args.query, "--query")
        body = read_json(args)
        path = render_path(template, params)
        base = args.base_url.rstrip("/")
        url = f"{base}{path}"
        if query:
            url += "?" + urlencode(query)
        key = os.environ.get("INTENSIVE_COLEARN_APIKEY")
        if not key and not args.dry_run:
            raise ValueError("INTENSIVE_COLEARN_APIKEY is not set")
        headers = {"Accept": "application/json", "User-Agent": args.user_agent}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        if method != "GET":
            headers["Idempotency-Key"] = args.idempotency_key or f"icl-skill-{uuid.uuid4()}"
        if args.dry_run:
            output_json({"method": method, "url": url, "headers": {name: ("<redacted>" if name == "Authorization" else value) for name, value in headers.items()}, "body": body})
            return 0

        request = Request(url, method=method, headers=headers)
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        with urlopen(request, data=payload, timeout=30) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw) if raw else None
            if args.status_only:
                output_json({"ok": True, "status": response.status})
            else:
                output_json(result)
            return 0
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail: Any = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            detail = raw
        output_json({"ok": False, "status": exc.code, "error": detail})
        return 1
    except (OSError, URLError, ValueError, KeyError) as exc:
        output_json({"ok": False, "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
