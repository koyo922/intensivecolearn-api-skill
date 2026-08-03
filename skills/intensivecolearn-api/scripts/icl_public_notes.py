#!/usr/bin/env python3
"""Read public ICL highlights and public GitHub notes without an ICL key."""

from __future__ import annotations

import argparse
import html as html_lib
import http.client
import json
import os
import re
import sys
import time
from typing import Any, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


ICL_ORIGIN = "https://intensivecolearn.ing"
GITHUB_API = "https://api.github.com"
USER_AGENT = "intensivecolearn-api-skill/1.0 (+https://github.com/koyo922/intensivecolearn-api-skill)"
FLIGHT_FRAME_RE = re.compile(r"self\.__next_f\.push\((\[.*?\])\)</script>", re.DOTALL)
FLIGHT_REFERENCE_RE = re.compile(r"^\$(?:L)?([0-9a-f]+)$")
GITHUB_REPO_RE = re.compile(r'href="(https://github\.com/[^/\"<]+/[^/\"?#<]+)')
SECTION_TITLES = {
    "每日优秀学习笔记": "daily",
    "结营优秀学习笔记": "final",
}


class PublicNotesError(RuntimeError):
    pass


def output_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def fetch_text(url: str, *, accept: str | None = None) -> str:
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    if url.startswith(GITHUB_API):
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    for attempt in range(3):
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code == 404:
                raise PublicNotesError(f"public resource not found: {url}") from exc
            if exc.code == 403 and url.startswith(GITHUB_API):
                raise PublicNotesError(
                    "GitHub rejected the request or its anonymous rate limit was reached; "
                    "set GITHUB_TOKEN or GH_TOKEN to increase the limit"
                ) from exc
            raise PublicNotesError(f"HTTP {exc.code} from {url}: {detail[:300]}") from exc
        except (http.client.IncompleteRead, http.client.RemoteDisconnected, TimeoutError, OSError, URLError, UnicodeDecodeError) as exc:
            if attempt == 2:
                raise PublicNotesError(f"could not read {url} after 3 attempts: {exc}") from exc
            time.sleep(0.5 * (attempt + 1))
    raise AssertionError("unreachable")


def program_url(target: str) -> str:
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme != "https" or parsed.netloc != "intensivecolearn.ing":
            raise PublicNotesError("program URL must use https://intensivecolearn.ing/programs/...")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) != 2 or parts[0] != "programs":
            raise PublicNotesError("program URL must use https://intensivecolearn.ing/programs/PROGRAM_ID")
        return f"{ICL_ORIGIN}/programs/{quote(parts[1], safe='')}"
    if not target or "/" in target:
        raise PublicNotesError("program target must be a program ID or ICL program URL")
    return f"{ICL_ORIGIN}/programs/{quote(target, safe='')}"


def flight_stream(page_html: str) -> str:
    parts: list[str] = []
    for match in FLIGHT_FRAME_RE.finditer(page_html):
        try:
            frame = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if len(frame) > 1 and isinstance(frame[1], str):
            parts.append(frame[1])
    if not parts:
        raise PublicNotesError("the public program page did not contain readable Next.js data")
    return "".join(parts)


def parse_flight_records(stream: str) -> dict[str, Any]:
    """Parse the subset of React Flight records used by the public program page."""
    data = stream.encode("utf-8")
    records: dict[str, Any] = {}
    cursor = 0
    while cursor < len(data):
        line_end = data.find(b"\n", cursor)
        colon = data.find(b":", cursor, line_end if line_end >= 0 else len(data))
        if colon < 0:
            break
        record_id_raw = data[cursor:colon]
        if not re.fullmatch(rb"[0-9a-f]+", record_id_raw):
            cursor = (line_end + 1) if line_end >= 0 else len(data)
            continue
        record_id = record_id_raw.decode("ascii")
        payload_start = colon + 1
        if data[payload_start:payload_start + 1] == b"T":
            comma = data.find(b",", payload_start + 1)
            if comma < 0:
                break
            try:
                length = int(data[payload_start + 1:comma], 16)
            except ValueError:
                cursor = (line_end + 1) if line_end >= 0 else len(data)
                continue
            text_start = comma + 1
            text_end = text_start + length
            if text_end > len(data):
                raise PublicNotesError("the public program page contained a truncated note")
            records[record_id] = data[text_start:text_end].decode("utf-8")
            cursor = text_end + (1 if data[text_end:text_end + 1] == b"\n" else 0)
            continue
        if line_end < 0:
            line_end = len(data)
        raw_payload = data[payload_start:line_end].decode("utf-8")
        if raw_payload[:1] in {"[", "{", '"'}:
            try:
                records[record_id] = json.loads(raw_payload)
            except json.JSONDecodeError:
                pass
        cursor = line_end + 1
    return records


def resolve_references(value: Any, records: dict[str, Any], stack: frozenset[str] = frozenset()) -> Any:
    if isinstance(value, str):
        match = FLIGHT_REFERENCE_RE.fullmatch(value)
        if not match:
            return value
        record_id = match.group(1)
        if record_id not in records or record_id in stack:
            return value
        return resolve_references(records[record_id], records, stack | {record_id})
    if isinstance(value, list):
        return [resolve_references(item, records, stack) for item in value]
    if isinstance(value, dict):
        return {key: resolve_references(item, records, stack) for key, item in value.items()}
    return value


def walk(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, list):
        for item in value:
            yield from walk(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk(item)


def is_element(value: Any, tag: str | None = None) -> bool:
    return (
        isinstance(value, list)
        and len(value) >= 4
        and value[0] == "$"
        and (tag is None or value[1] == tag)
        and isinstance(value[3], dict)
    )


def element_class(value: Any) -> str:
    if not is_element(value):
        return ""
    class_name = value[3].get("className", "")
    return class_name if isinstance(class_name, str) else ""


def child_text(value: Any) -> str | None:
    if not is_element(value):
        return None
    children = value[3].get("children")
    return children if isinstance(children, str) else None


def first_class_text(value: Any, class_fragment: str) -> str | None:
    for node in walk(value):
        if class_fragment in element_class(node):
            text = child_text(node)
            if text is not None:
                return text
    return None


def action_props(value: Any) -> dict[str, Any] | None:
    for node in walk(value):
        if isinstance(node, dict) and {"authorName", "content", "rank"} <= set(node):
            if isinstance(node["authorName"], str) and isinstance(node["content"], str):
                return node
    return None


def parse_highlight_card(card: list[Any], kind: str) -> dict[str, Any] | None:
    action = action_props(card)
    if not action:
        return None
    tags: list[str] = []
    for node in walk(card):
        if "highlightTagList" in element_class(node):
            for child in walk(node[3].get("children")):
                text = child_text(child)
                if text and text not in tags:
                    tags.append(text)
    content = action["content"]
    return {
        "id": card[2] if isinstance(card[2], str) else None,
        "kind": kind,
        "rank": action["rank"],
        "author": action["authorName"],
        "profileUrl": f"{ICL_ORIGIN}/profile/{quote(action['authorName'], safe='')}",
        "date": first_class_text(card, "highlightDate"),
        "summary": first_class_text(card, "highlightSummary"),
        "tags": tags,
        "content": content,
        "contentLength": len(content),
    }


def contains_text(value: Any, expected: str) -> bool:
    return any(node == expected for node in walk(value))


def parse_highlight_sections(records: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    highlights: list[dict[str, Any]] = []
    section_messages: dict[str, list[str]] = {"daily": [], "final": []}
    seen_sections: set[tuple[str, str]] = set()
    seen_highlights: set[tuple[str, str | None, str, Any]] = set()
    resolved_models = [resolve_references(value, records) for value in records.values() if isinstance(value, (list, dict))]

    for model in resolved_models:
        for node in walk(model):
            if not is_element(node, "article") or "detailCard" not in element_class(node):
                continue
            kind = next((value for title, value in SECTION_TITLES.items() if contains_text(node, title)), None)
            if not kind:
                continue
            section_key = (kind, str(node[2]))
            if section_key in seen_sections:
                continue
            seen_sections.add(section_key)
            for child in walk(node):
                if is_element(child, "article") and "highlightCard" in element_class(child):
                    parsed = parse_highlight_card(child, kind)
                    if parsed:
                        key = (kind, parsed["id"], parsed["author"], parsed["rank"])
                        if key not in seen_highlights:
                            seen_highlights.add(key)
                            highlights.append(parsed)
                if "detailSectionText" in element_class(child):
                    text = child_text(child)
                    if text and text not in section_messages[kind]:
                        section_messages[kind].append(text)

    if not highlights:
        for model in resolved_models:
            for node in walk(model):
                if not (is_element(node, "article") and "highlightCard" in element_class(node)):
                    continue
                parsed = parse_highlight_card(node, "unknown")
                if parsed:
                    key = ("unknown", parsed["id"], parsed["author"], parsed["rank"])
                    if key not in seen_highlights:
                        seen_highlights.add(key)
                        highlights.append(parsed)
    return highlights, section_messages


def extract_repository_url(page_html: str) -> str | None:
    for match in GITHUB_REPO_RE.finditer(page_html):
        url = html_lib.unescape(match.group(1)).rstrip("/")
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 2 and parts != ["IntensiveCoLearning"]:
            return url.removesuffix(".git")
    return None


def inspect_program(target: str) -> dict[str, Any]:
    url = program_url(target)
    page_html = fetch_text(url)
    title_match = re.search(r"<title>(.*?)</title>", page_html, re.DOTALL)
    title = html_lib.unescape(title_match.group(1)).removeprefix("残酷共学｜") if title_match else None
    records = parse_flight_records(flight_stream(page_html))
    highlights, section_messages = parse_highlight_sections(records)
    visibility = "private_cohort" if "学员私享" in page_html else "public_github" if "开源" in page_html else "unknown"
    return {
        "program": title,
        "programUrl": url,
        "noteVisibility": visibility,
        "repositoryUrl": extract_repository_url(page_html),
        "highlights": highlights,
        "highlightSectionMessages": section_messages,
        "source": {
            "type": "public_website",
            "url": url,
            "officialAgentApi": False,
            "notice": "Read from the public ICL website, not from the official Agent API.",
        },
    }


def parse_repo_target(target: str) -> tuple[str, str]:
    parsed = urlparse(target)
    if parsed.scheme:
        if parsed.scheme != "https" or parsed.netloc != "github.com":
            raise PublicNotesError("repository URL must use https://github.com/OWNER/REPO")
        parts = [part for part in parsed.path.split("/") if part]
    else:
        parts = [part for part in target.split("/") if part]
    if len(parts) != 2:
        raise PublicNotesError("repository target must be OWNER/REPO or a GitHub repository URL")
    return parts[0], parts[1].removesuffix(".git")


def resolve_repository(target: str) -> tuple[str, str, str | None]:
    if target.startswith("https://intensivecolearn.ing/") or "/" not in target:
        inspected = inspect_program(target)
        repository_url = inspected["repositoryUrl"]
        if not repository_url:
            raise PublicNotesError(
                "this program page does not expose a public GitHub repository; "
                "use list-highlights for any publicly selected notes"
            )
        owner, repo = parse_repo_target(repository_url)
        return owner, repo, inspected["programUrl"]
    owner, repo = parse_repo_target(target)
    return owner, repo, None


def github_json(path: str) -> Any:
    return json.loads(fetch_text(f"{GITHUB_API}{path}", accept="application/vnd.github+json"))


def list_repository_notes(target: str, limit: int) -> dict[str, Any]:
    owner, repo, program_source = resolve_repository(target)
    metadata = github_json(f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}")
    branch = metadata["default_branch"]
    root_tree = github_json(
        f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/git/trees/{quote(branch, safe='')}"
    )
    notes_entry = next(
        (item for item in root_tree.get("tree", []) if item.get("type") == "tree" and item.get("path") == "notes"),
        None,
    )
    if notes_entry:
        notes_tree = github_json(
            f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/git/trees/{quote(notes_entry['sha'], safe='')}"
        )
        notes = [
            {**item, "path": f"notes/{item['path']}"}
            for item in notes_tree.get("tree", [])
            if item.get("type") == "blob"
            and isinstance(item.get("path"), str)
            and item["path"].lower().endswith(".md")
        ]
    else:
        notes = [
            item for item in root_tree.get("tree", [])
            if item.get("type") == "blob"
            and isinstance(item.get("path"), str)
            and item["path"].lower().endswith(".md")
            and item["path"].lower() != "readme.md"
        ]
    notes.sort(key=lambda item: item["path"].casefold())
    selected = notes[:limit]
    repository_url = f"https://github.com/{owner}/{repo}"
    return {
        "repository": f"{owner}/{repo}",
        "repositoryUrl": repository_url,
        "defaultBranch": branch,
        "total": len(notes),
        "truncated": len(notes) > limit,
        "items": [
            {
                "path": item["path"],
                "size": item.get("size"),
                "url": f"{repository_url}/blob/{quote(branch, safe='')}/{quote(item['path'], safe='/')}",
            }
            for item in selected
        ],
        "source": {
            "type": "public_github",
            "url": repository_url,
            "programUrl": program_source,
            "officialAgentApi": False,
            "notice": "Read from a public GitHub repository, not from the official Agent API.",
        },
    }


def get_repository_note(target: str, note_path: str) -> dict[str, Any]:
    if not note_path.lower().endswith(".md") or any(part in {"", ".", ".."} for part in note_path.split("/")):
        raise PublicNotesError("note path must be a repository-relative Markdown path")
    owner, repo, program_source = resolve_repository(target)
    metadata = github_json(f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}")
    branch = metadata["default_branch"]
    encoded_path = quote(note_path, safe="/")
    raw_url = f"https://raw.githubusercontent.com/{quote(owner, safe='')}/{quote(repo, safe='')}/{quote(branch, safe='')}/{encoded_path}"
    content = fetch_text(raw_url)
    html_url = f"https://github.com/{owner}/{repo}/blob/{quote(branch, safe='')}/{encoded_path}"
    return {
        "repository": f"{owner}/{repo}",
        "path": note_path,
        "url": html_url,
        "content": content,
        "contentLength": len(content),
        "source": {
            "type": "public_github",
            "url": html_url,
            "programUrl": program_source,
            "officialAgentApi": False,
            "notice": "Read from a public GitHub repository, not from the official Agent API.",
        },
    }


def without_content(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if key != "content"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read public ICL excellent notes and public GitHub notes without an ICL Access Key."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-program", help="Inspect public note sources and highlight status")
    inspect_parser.add_argument("target", help="ICL program ID or URL")
    inspect_parser.add_argument("--include-content", action="store_true")

    list_highlights_parser = subparsers.add_parser("list-highlights", help="List website-selected excellent notes")
    list_highlights_parser.add_argument("target", help="ICL program ID or URL")

    get_highlight_parser = subparsers.add_parser("get-highlight", help="Read one website-selected excellent note")
    get_highlight_parser.add_argument("target", help="ICL program ID or URL")
    get_highlight_parser.add_argument("highlight_id", help="ID returned by list-highlights")

    list_notes_parser = subparsers.add_parser("list-public-notes", help="List Markdown notes in a public project repository")
    list_notes_parser.add_argument("target", help="ICL program ID/URL or OWNER/REPO")
    list_notes_parser.add_argument("--limit", type=int, default=30)

    get_note_parser = subparsers.add_parser("get-public-note", help="Read one Markdown note from a public project repository")
    get_note_parser.add_argument("target", help="ICL program ID/URL or OWNER/REPO")
    get_note_parser.add_argument("path", help="Repository-relative Markdown path")

    args = parser.parse_args()
    try:
        if args.command == "inspect-program":
            result = inspect_program(args.target)
            if not args.include_content:
                result["highlights"] = [without_content(item) for item in result["highlights"]]
        elif args.command == "list-highlights":
            inspected = inspect_program(args.target)
            result = {
                "program": inspected["program"],
                "programUrl": inspected["programUrl"],
                "items": [without_content(item) for item in inspected["highlights"]],
                "total": len(inspected["highlights"]),
                "sectionMessages": inspected["highlightSectionMessages"],
                "source": inspected["source"],
            }
        elif args.command == "get-highlight":
            inspected = inspect_program(args.target)
            matches = [item for item in inspected["highlights"] if item["id"] == args.highlight_id]
            if len(matches) != 1:
                raise PublicNotesError(f"highlight ID not found: {args.highlight_id}")
            result = {**matches[0], "program": inspected["program"], "programUrl": inspected["programUrl"], "source": inspected["source"]}
        elif args.command == "list-public-notes":
            if not 1 <= args.limit <= 500:
                raise PublicNotesError("--limit must be between 1 and 500")
            result = list_repository_notes(args.target, args.limit)
        else:
            result = get_repository_note(args.target, args.path)
        output_json(result)
        return 0
    except (PublicNotesError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        output_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
