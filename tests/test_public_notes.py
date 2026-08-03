from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills" / "intensivecolearn-api" / "scripts" / "icl_public_notes.py"
SPEC = importlib.util.spec_from_file_location("icl_public_notes", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicNotesParserTests(unittest.TestCase):
    def test_flight_text_record_uses_utf8_byte_length(self) -> None:
        records = MODULE.parse_flight_records('1:["$","p",null,{"children":"$2"}]\n2:T6,你好\n')
        self.assertEqual(records["2"], "你好")
        self.assertEqual(MODULE.resolve_references(records["1"], records)[3]["children"], "你好")

    def test_extracts_highlight_with_resolved_content(self) -> None:
        highlight = [
            "$",
            "article",
            "highlight-1",
            {
                "className": "programs_highlightCard__test",
                "children": [
                    ["$", "p", None, {"className": "programs_highlightDate__test", "children": "2026/08/02"}],
                    ["$", "p", None, {"className": "programs_highlightSummary__test", "children": "Useful summary"}],
                    [
                        "$",
                        "div",
                        None,
                        {
                            "className": "programs_highlightTagList__test",
                            "children": [["$", "span", None, {"children": "理性"}]],
                        },
                    ],
                    {"authorName": "alice", "content": "$2", "rank": 1},
                ],
            },
        ]
        section = [
            "$",
            "article",
            "daily-section",
            {
                "className": "programs_detailCard__test",
                "children": [
                    ["$", "h2", None, {"children": "每日优秀学习笔记"}],
                    highlight,
                ],
            },
        ]
        records = {"1": section, "2": "# Original note"}
        items, messages = MODULE.parse_highlight_sections(records)
        self.assertEqual(messages, {"daily": [], "final": []})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "highlight-1")
        self.assertEqual(items[0]["kind"], "daily")
        self.assertEqual(items[0]["author"], "alice")
        self.assertEqual(items[0]["content"], "# Original note")
        self.assertEqual(items[0]["summary"], "Useful summary")
        self.assertEqual(items[0]["tags"], ["理性"])

    def test_extracts_only_repository_links(self) -> None:
        page = (
            '<a href="https://github.com/IntensiveCoLearning">org</a>'
            '<a href="https://github.com/IntensiveCoLearning/example">repo</a>'
        )
        self.assertEqual(
            MODULE.extract_repository_url(page),
            "https://github.com/IntensiveCoLearning/example",
        )

    def test_rejects_non_icl_program_url(self) -> None:
        with self.assertRaises(MODULE.PublicNotesError):
            MODULE.program_url("https://example.com/programs/123")


if __name__ == "__main__":
    unittest.main()
