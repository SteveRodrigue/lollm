"""Independently validate a model-generated 1000-digit pi implementation."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import math
import sys
from decimal import Decimal, getcontext
from pathlib import Path
from types import ModuleType
from typing import Any

DIGITS_AFTER_DECIMAL = 1000


def load_module(source_path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location("generated_pi", source_path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Could not load Python source: {source_path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def expected_pi() -> str:
    getcontext().prec = DIGITS_AFTER_DECIMAL + 30
    total = Decimal(0)
    for index in range(18):
        numerator = Decimal((-1) ** index * math.factorial(6 * index))
        numerator *= Decimal(13591409 + 545140134 * index)
        denominator = Decimal(math.factorial(3 * index))
        denominator *= Decimal(math.factorial(index)) ** 3
        denominator *= Decimal(640320) ** (3 * index)
        term = numerator / denominator
        total += term
    value = Decimal(426880) * Decimal(10005).sqrt() / total
    return f"{value:.{DIGITS_AFTER_DECIMAL}f}"


def check_dependency_constraint(source_path: Path) -> None:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    standard_library = getattr(sys, "stdlib_module_names", set())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".", 1)[0]]
        else:
            continue
        for name in names:
            if standard_library and name not in standard_library:
                raise AssertionError(f"non-standard import: {name}")


def run_checks(module: ModuleType) -> tuple[list[str], list[dict[str, str]]]:
    function = module.__dict__.get("generate_pi")
    if not callable(function):
        raise TypeError("missing callable generate_pi")
    expected = expected_pi()
    checks: list[tuple[str, Any]] = [
        ("string result", lambda: isinstance(function(), str)),
        ("decimal shape", lambda: function().startswith("3.")),
        ("exact length", lambda: len(function()) == DIGITS_AFTER_DECIMAL + 2),
        ("digit content", lambda: function()[2:].isdigit()),
        ("pi correctness", lambda: function() == expected),
        ("deterministic result", lambda: function() == function()),
    ]
    passed: list[str] = []
    failed: list[dict[str, str]] = []
    for name, check in checks:
        try:
            if not check():
                raise AssertionError("condition returned false")
        except Exception as error:  # noqa: BLE001 - report every independent failure.
            failed.append({"name": name, "error": f"{type(error).__name__}: {error}"})
        else:
            passed.append(name)
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
        passed, failed = run_checks(module)
        result["passed"].extend(passed)
        result["failed"] = failed
        result["status"] = "pass" if not failed else "fail"
    except Exception as error:  # noqa: BLE001 - report validation failures.
        result["error"] = f"{type(error).__name__}: {error}"
    output = json.dumps(result, indent=2) + "\n"
    print(output, end="")
    if arguments.json_out:
        arguments.json_out.write_text(output, encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
