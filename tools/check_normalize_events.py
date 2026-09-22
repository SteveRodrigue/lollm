"""Run independent checks for a model-generated normalize_events implementation."""

from __future__ import annotations

import argparse
import ast
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

Event = dict[str, Any]


def load_module(source_path: Path) -> ModuleType:
    module_spec = importlib.util.spec_from_file_location(
        "generated_normalize_events", source_path
    )
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"Could not load Python source: {source_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def check_dependency_constraint(source_path: Path) -> None:
    source = source_path.read_text(encoding="utf-8")
    forbidden_text = re.compile(
        r"\b(?:pip|uv|winget|conda|poetry|install package|package manager)\b",
        re.IGNORECASE,
    )
    if forbidden_text.search(source):
        raise AssertionError("dependency constraint: package-install instruction found")

    syntax_tree = ast.parse(source, filename=str(source_path))
    standard_library = getattr(sys, "stdlib_module_names", set())
    for node in ast.walk(syntax_tree):
        if isinstance(node, ast.Import):
            imported_names = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names = [node.module.split(".", 1)[0]]
        else:
            continue
        for imported_name in imported_names:
            if standard_library and imported_name not in standard_library:
                raise AssertionError(
                    f"dependency constraint: non-standard import {imported_name!r}"
                )


def assert_equal(actual: Any, expected: Any, case_name: str) -> None:
    if actual != expected:
        raise AssertionError(f"{case_name}: expected {expected!r}, got {actual!r}")


def assert_raises_value_error(
    function: Any, events: list[Event], case_name: str, field_name: str
) -> None:
    try:
        function(events)
    except ValueError as error:
        if field_name.lower() not in str(error).lower():
            raise AssertionError(
                f"{case_name}: ValueError did not mention {field_name!r}: {error}"
            ) from error
    else:
        raise AssertionError(f"{case_name}: expected ValueError")


def run_checks(function: Any) -> tuple[list[str], list[dict[str, str]]]:
    checks: list[tuple[str, Any]] = []

    def check_empty_and_single() -> None:
        assert_equal(function([]), [], "empty input")
        event = {
            "id": "single",
            "timestamp": "2026-01-01T00:00:00Z",
            "payload": {"x": 1},
        }
        events = [event]
        result = function(events)
        assert_equal(result, [event], "single event")
        if result is events:
            raise AssertionError("single event: result list must be new")

    def check_sorting_and_ties() -> None:
        events = [
            {"id": "b", "timestamp": "2026-01-01T00:00:02Z", "payload": "b"},
            {"id": "z", "timestamp": "2026-01-01T00:00:01Z", "payload": "z"},
            {"id": "a", "timestamp": "2026-01-01T00:00:01Z", "payload": "a"},
        ]
        expected = [events[2], events[1], events[0]]
        assert_equal(function(events), expected, "timestamp and id sorting")

    def check_newest_duplicate_wins() -> None:
        older = {
            "id": "duplicate",
            "timestamp": "2026-01-01T00:00:01Z",
            "payload": "old",
        }
        newer = {
            "id": "duplicate",
            "timestamp": "2026-01-01T00:00:03Z",
            "payload": "new",
            "metadata": {"source": "test"},
        }
        result = function([newer, older])
        assert_equal(result, [newer], "newest duplicate wins")

    def check_field_preservation() -> None:
        event = {
            "id": "fields",
            "timestamp": "2026-01-01T00:00:00Z",
            "category": "example",
            "payload": {"nested": [1, 2, 3]},
            "metadata": {"owner": "qa"},
        }
        assert_equal(function([event]), [event], "payload and metadata preservation")

    def check_invalid_records() -> None:
        assert_raises_value_error(
            function,
            [{"timestamp": "2026-01-01T00:00:00Z"}],
            "missing id",
            "id",
        )
        assert_raises_value_error(
            function,
            [{"id": "missing-time"}],
            "missing timestamp",
            "timestamp",
        )

    def check_immutability_and_determinism() -> None:
        events = [
            {"id": "b", "timestamp": "2026-01-01T00:00:02Z", "payload": {"value": 2}},
            {"id": "a", "timestamp": "2026-01-01T00:00:01Z", "payload": {"value": 1}},
        ]
        original = copy.deepcopy(events)
        first = function(events)
        second = function(events)
        assert_equal(events, original, "input immutability")
        assert_equal(first, second, "deterministic output")
        if first is events:
            raise AssertionError("input immutability: result list must be independent")
        if any(result is event for result in first for event in events):
            raise AssertionError(
                "input immutability: result dictionaries must be independent"
            )
        events[0]["id"] = "mutated"
        events[0]["payload"]["value"] = 999
        events.append({"id": "added", "timestamp": "2026-01-01T00:00:03Z"})
        if first[0]["id"] == "mutated" or first[0]["payload"]["value"] == 999:
            raise AssertionError(
                "input immutability: post-return input mutation changed result"
            )

    checks.extend(
        [
            ("empty and single input", check_empty_and_single),
            ("sorting and ties", check_sorting_and_ties),
            ("newest duplicate wins", check_newest_duplicate_wins),
            ("field preservation", check_field_preservation),
            ("invalid records", check_invalid_records),
            ("immutability and determinism", check_immutability_and_determinism),
        ]
    )

    passed: list[str] = []
    failed: list[dict[str, str]] = []
    for check_name, check_function in checks:
        try:
            check_function()
        except Exception as error:  # noqa: BLE001 - report every independent failure.
            failed.append(
                {
                    "name": check_name,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
        else:
            passed.append(check_name)
    return passed, failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json-out", type=Path)
    arguments = parser.parse_args()

    result: dict[str, Any] = {
        "source": str(arguments.source),
        "status": "fail",
        "passed": [],
    }
    try:
        check_dependency_constraint(arguments.source)
        result["passed"].append("dependency constraint")
        module = load_module(arguments.source)
        function = module.__dict__["normalize_events"]
        passed, failed = run_checks(function)
        result["passed"].extend(passed)
        result["failed"] = failed
        result["status"] = "pass" if not failed else "fail"
    except Exception as error:  # noqa: BLE001 - the checker must report any model failure.
        result["error"] = f"{type(error).__name__}: {error}"

    output = json.dumps(result, indent=2)
    print(output)
    if arguments.json_out:
        arguments.json_out.write_text(output + "\n", encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
