"""Independently validate a generated parse_and_average implementation."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def load_module(source_path: Path) -> ModuleType:
    specification = importlib.util.spec_from_file_location(
        "generated_parse_and_average", source_path
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(f"Could not load Python source: {source_path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def check_standard_library(source_path: Path) -> None:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    allowed = set(__import__("sys").stdlib_module_names)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name.split(".", 1)[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module.split(".", 1)[0]]
        else:
            continue
        for name in names:
            if name not in allowed and name != "pytest":
                raise AssertionError(f"non-standard import: {name}")


def pytest_function_count(source_path: Path) -> int:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    return sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(tree)
    )


def run_pytest(source_path: Path) -> tuple[str, str]:
    test_count = pytest_function_count(source_path)
    if test_count < 2:
        raise AssertionError(
            f"expected at least two pytest functions, found {test_count}"
        )
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(source_path), "-q", "--disable-warnings"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise AssertionError(f"pytest failed (exit {result.returncode}): {output}")
    return "pytest tests", output


def run_checks(module: ModuleType) -> tuple[list[str], list[dict[str, str]]]:
    function = module.__dict__.get("parse_and_average")
    if not callable(function):
        raise TypeError("missing callable parse_and_average")
    checks: list[tuple[str, Any]] = [
        ("normal average", lambda: function(["1", "2", "3"]) == 2.0),
        ("mixed invalid values", lambda: function(["1.5", "bad", "", "2.5"]) == 2.0),
        ("no valid values", lambda: function(["", "bad", "NaN?", " "]) == 0.0),
        ("empty input", lambda: function([]) == 0.0),
        ("rounding", lambda: function(["1", "2", "2"]) == 1.67),
        (
            "typing and docstring",
            lambda: (
                bool(inspect.getdoc(function))
                and bool(
                    inspect.signature(function).return_annotation
                    is not inspect.Signature.empty
                )
                and all(
                    parameter.annotation is not inspect.Signature.empty
                    for parameter in inspect.signature(function).parameters.values()
                )
            ),
        ),
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
        check_standard_library(arguments.source)
        result["passed"].append("dependency constraint")
        module = load_module(arguments.source)
        passed, failed = run_checks(module)
        result["passed"].extend(passed)
        result["failed"] = failed
        try:
            pytest_name, pytest_output = run_pytest(arguments.source)
        except Exception as error:  # noqa: BLE001 - report pytest failures as data.
            result["failed"].append({
                "name": "pytest snippet",
                "error": f"{type(error).__name__}: {error}",
            })
        else:
            result["passed"].append(pytest_name)
            result["pytest_output"] = pytest_output
        result["status"] = "pass" if not result["failed"] else "fail"
    except Exception as error:  # noqa: BLE001 - report test failures as data.
        result["error"] = f"{type(error).__name__}: {error}"
    output = json.dumps(result, indent=2) + "\n"
    print(output, end="")
    if arguments.json_out:
        arguments.json_out.write_text(output, encoding="utf-8")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
