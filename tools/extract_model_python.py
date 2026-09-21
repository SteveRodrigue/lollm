"""Extract a Python candidate from an immutable model-output artifact."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any


FENCED_BLOCK = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.IGNORECASE | re.DOTALL)


def is_candidate(source: str, function_name: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
        for node in ast.walk(tree)
    )


def extract_fenced(text: str, function_name: str) -> tuple[str | None, bool]:
    blocks = [match.group(1).strip() for match in FENCED_BLOCK.finditer(text)]
    for block in blocks:
        if is_candidate(block, function_name):
            return block + "\n", True
    return None, bool(blocks)


def extract_unfenced(text: str, function_name: str) -> str | None:
    lines = text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(
            rf"^(?:from\s+\S+\s+import|import\s+\S+|def\s+{re.escape(function_name)})",
            line,
        )
    ]
    for start in starts:
        candidate_lines = lines[start:]
        for end in range(len(candidate_lines), 0, -1):
            candidate = "\n".join(candidate_lines[:end]).strip() + "\n"
            if is_candidate(candidate, function_name):
                return candidate
    return None


def extract(
    text: str, function_name: str = "normalize_events"
) -> tuple[str, dict[str, Any]]:
    text = text.lstrip("\ufeff")
    fenced, had_fence = extract_fenced(text, function_name)
    if fenced is not None:
        return fenced, {"source": "fenced-block", "had_fence": had_fence}
    unfenced = extract_unfenced(text, function_name)
    if unfenced is not None:
        return unfenced, {"source": "unfenced-python", "had_fence": had_fence}
    raise ValueError(f"No syntactically valid {function_name} Python candidate found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_output", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--function", default="normalize_events")
    arguments = parser.parse_args()

    try:
        candidate, metadata = extract(
            arguments.raw_output.read_text(encoding="utf-8-sig"),
            arguments.function,
        )
        arguments.output.write_text(candidate, encoding="utf-8")
        metadata.update({"status": "pass", "output": str(arguments.output)})
        exit_code = 0
    except Exception as error:  # noqa: BLE001 - report extraction failures as test data.
        metadata = {"status": "fail", "error": f"{type(error).__name__}: {error}"}
        exit_code = 1

    serialized = json.dumps(metadata, indent=2) + "\n"
    print(serialized, end="")
    if arguments.metadata:
        arguments.metadata.write_text(serialized, encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
