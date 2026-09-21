"""Refresh the auto-managed ledger summary and reports."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BEGIN = "<!-- BEGIN AUTO TEST LEDGER -->"
END = "<!-- END AUTO TEST LEDGER -->"
REPORT_NAME = "test-results.md"
SUMMARY_REPORT_NAME = "test-summary.md"
SUMMARY_YAML_NAME = "test-summary.yaml"


def report_directory(evidence_path: Path) -> Path:
    return evidence_path.parent.parent / "reports" / "latest"


def read_rows(log_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ledger_path in sorted(log_root.glob("*/results.jsonl")):
        for line_number, line in enumerate(
            ledger_path.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON in {ledger_path}:{line_number}: {error}"
                ) from error
            row["ledger"] = str(ledger_path)
            rows.append(row)
    return rows


def markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        BEGIN,
        "## Durable Test Ledger Summary",
        "",
        "This section is generated from per-model `results.jsonl` files. It is updated after each completed test.",
        "",
        "| Date | Model | Stage | Context | GPU layers | Status | Outcome | Log |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        values = [
            str(row.get("date", "")),
            str(row.get("model", "")).replace("|", "\\|"),
            str(row.get("stage", "")),
            str(row.get("context", "")),
            str(row.get("gpu_layers", "")),
            str(row.get("status", "")),
            str(row.get("outcome", "")).replace("|", "\\|"),
            str(row.get("log", "")).replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend([END, ""])
    return "\n".join(lines)


def update_evidence(evidence_path: Path, summary: str) -> None:
    content = evidence_path.read_text(encoding="utf-8")
    if BEGIN in content and END in content:
        before, remainder = content.split(BEGIN, 1)
        _, after = remainder.split(END, 1)
        evidence_path.write_text(
            before + summary + after.lstrip("\n"), encoding="utf-8"
        )
        return

    anchor = "## Local hardware"
    if anchor not in content:
        raise ValueError(
            f"Could not find insertion anchor {anchor!r} in {evidence_path}"
        )
    before, after = content.split(anchor, 1)
    evidence_path.write_text(before + summary + "\n" + anchor + after, encoding="utf-8")


def model_name(row: dict[str, Any]) -> str:
    return Path(str(row.get("model", "unknown"))).parent.name or "unknown"


def unittest_score(row: dict[str, Any]) -> tuple[int, int, int]:
    ledger_path = Path(str(row.get("ledger", "")))
    context = int(row.get("context", 0))
    raw_output_path = Path(str(row.get("raw_output", "")))
    if raw_output_path.name.endswith("-independent.json"):
        test_log = raw_output_path.with_name(
            raw_output_path.name.replace("-independent.json", "-unittest.txt")
        )
    elif context == 4096:
        test_log = ledger_path.parent / "normalize-events-unittest.txt"
    else:
        test_log = ledger_path.parent / f"normalize-events-c{context}-unittest.txt"
    if not test_log.exists():
        return 0, 0, 6
    raw = test_log.read_bytes()
    if (
        raw.startswith((b"\xff\xfe", b"\xfe\xff"))
        or raw.count(b"\x00") > len(raw) // 10
    ):
        text = raw.decode("utf-16", errors="replace")
    else:
        text = raw.decode("utf-8-sig", errors="replace")
    ran_match = re.search(r"Ran (\d+) tests?", text)
    ran = int(ran_match.group(1)) if ran_match else 0
    failed_match = re.search(r"FAILED \(([^)]*)\)", text)
    failed = 0
    if failed_match:
        failure_counts = re.findall(r"(?:failures|errors)=(\d+)", failed_match.group(1))
        failed = sum(int(count) for count in failure_counts)
    passed = max(0, min(6, ran - failed))
    return passed, ran, 6


def compile_status(row: dict[str, Any]) -> str:
    match = re.search(r"(?:^|; )compile=(\d+)", str(row.get("outcome", "")))
    if match:
        return "success" if match.group(1) == "0" else "fail"
    compile_log = Path(str(row.get("ledger", ""))).parent / (
        "normalize-events-compile.txt"
        if int(row.get("context", 0)) == 4096
        else f"normalize-events-c{row.get('context')}-compile.txt"
    )
    if not compile_log.exists():
        return "fail"
    return "success" if not compile_log.read_text(errors="replace").strip() else "fail"


def independent_score(row: dict[str, Any]) -> tuple[int, int]:
    path = Path(str(row.get("raw_output", "")))
    if not path.exists():
        return 0, 6
    try:
        result = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return 0, 6
    passed = [
        name for name in result.get("passed", []) if name != "dependency constraint"
    ]
    return min(6, len(passed)), 6


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if (
        raw.startswith((b"\xff\xfe", b"\xfe\xff"))
        or raw.count(b"\x00") > len(raw) // 10
    ):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def generation_speed(row: dict[str, Any]) -> str:
    log_path = Path(str(row.get("log", "")))
    if not log_path.exists():
        return "N/A"
    match = re.search(r"Generation:\s*([0-9.]+)\s*t/s", read_text_file(log_path))
    return f"{match.group(1)}" if match else "N/A"


def peak_vram(row: dict[str, Any]) -> str:
    stats = row.get("gpu_stats")
    if isinstance(stats, dict) and stats.get("vram_peak_mib") is not None:
        return f"{float(stats['vram_peak_mib']):.0f}"
    return "N/A"


def test_completion(row: dict[str, Any]) -> str:
    if row.get("status") == "generation-pass":
        return "true"
    failure_class = row.get("failure_class")
    if failure_class and failure_class != "none":
        return f"false ({failure_class})"
    outcome = str(row.get("outcome", ""))
    match = re.search(r"failure_class=([^;]+)", outcome)
    if match and match.group(1) != "none":
        return f"false ({match.group(1)})"
    return "false (process-error)"


def latest_generation_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("model", "")),
            str(row.get("prompt_name", "")),
            int(row.get("context", 0)),
            int(row.get("output_budget", 0)),
        )
        latest[key] = row
    return list(latest.values())


def duration_minutes(row: dict[str, Any]) -> str:
    value = row.get("duration_seconds")
    if value is None:
        return "N/A"
    try:
        return f"{float(value) / 60:.2f}"
    except (TypeError, ValueError):
        return "N/A"


def utc_timestamp(value: Any) -> str:
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return (
        parsed
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def test_time_window(rows: list[dict[str, Any]], budget: int) -> str:
    dates = [
        utc_timestamp(row.get("date", ""))
        for row in rows
        if int(row.get("output_budget", 0)) == budget and row.get("date")
    ]
    if not dates:
        return "no runs"
    dates.sort()
    return f"{dates[0]} and {dates[-1]}"


def summary_markdown(rows: list[dict[str, Any]], test_name: str | None = None) -> str:
    if test_name is not None:
        rows = [row for row in rows if str(row.get("prompt_name", "")) == test_name]
        if test_name == "pi-1000-digits":
            return pi_summary_markdown(rows)
    lines = [
        "# Coding Test Summary",
        "",
        "> Controlled `r2` quality runs only. Preliminary `-n 1024` runs and invalid-flag attempts are excluded.",
        "",
        "`test-completion` means the model process completed with exit code 0. `compiled` and both test scores are evaluated from the paired validation row.",
        "",
    ]
    generation_rows = latest_generation_rows([
        row
        for row in rows
        if row.get("stage") == "quality-normalize-events"
        and int(row.get("output_budget", 0)) in {8192, 16384}
    ])
    validation_rows = [row for row in rows if row.get("stage") == "quality-validation"]
    profiles: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in generation_rows:
        profile_name = row.get("profile")
        if not profile_name:
            profile_name = f"legacy-output-{row.get('output_budget', 'unknown')}"
        budget = int(row.get("output_budget", 0))
        profiles.setdefault((str(profile_name), budget), []).append(row)
    for (profile_name, budget), profile_rows in sorted(profiles.items()):
        budget_tests = sorted({
            str(row.get("prompt_name", "unknown")) for row in profile_rows
        })
        tests_label = ", ".join(budget_tests) if budget_tests else "none yet"
        lines.extend([
            f"## Profile `{profile_name}` | Output `-n {budget}` | "
            f"Reasoning `{profile_rows[0].get('reasoning_mode') or ('unspecified' if profile_name != 'legacy-output-' + str(budget) else 'legacy')}` / "
            f"budget `{profile_rows[0].get('reasoning_budget') if profile_rows[0].get('reasoning_budget') is not None else ('unspecified' if profile_name != 'legacy-output-' + str(budget) else 'legacy')}`",
            "",
            f"**Output budget:** `-n {budget}`",
            f"**Tests represented:** `{tests_label}`",
            f"**Test occurred between:** {test_time_window(profile_rows, budget)}",
            "",
            "| Test | Model | Context | Test completion | Compiled | Model-test | Our-test | Token/s | Duration (min) | Peak VRAM (MiB) | Both 6/6 |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ])
        budget_rows = profile_rows
        for generation in sorted(
            budget_rows,
            key=lambda row: (model_name(row), int(row.get("context", 0))),
        ):
            matches = [
                row
                for row in validation_rows
                if row.get("run_id") == generation.get("run_id")
                and row.get("model") == generation.get("model")
                and int(row.get("context", 0)) == int(generation.get("context", 0))
                and int(row.get("output_budget", 0)) == budget
            ]
            validation = matches[-1] if matches else {}
            compiled = (
                "true"
                if validation and compile_status(validation) == "success"
                else "false"
            )
            model_tests = unittest_score(validation)[0] if validation else 0
            our_tests = independent_score(validation)[0] if validation else 0
            duration = duration_minutes(generation)
            both_passed = "✅" if model_tests == 6 and our_tests == 6 else ""
            lines.append(
                f"| {generation.get('prompt_name', 'unknown')} | {model_name(generation)} | "
                f"{int(generation.get('context', 0)) // 1024}K | "
                f"{test_completion(generation)} | {compiled} | {model_tests}/6 | "
                f"{our_tests}/6 | {generation_speed(generation)} | {duration} | "
                f"{peak_vram(generation)} | {both_passed} |"
            )
        lines.append("")
    return "\n".join(lines)


def pi_summary_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Pi 1000-Digit Test Summary",
        "",
        "> The Pi test does not require model-authored unit tests. `our-test` is the independent Pi checker with six checks.",
        "",
    ]
    generation_rows = latest_generation_rows([
        row
        for row in rows
        if row.get("stage") == "quality-normalize-events"
        and int(row.get("output_budget", 0)) in {8192, 16384}
    ])
    validation_rows = [row for row in rows if row.get("stage") == "quality-validation"]
    profiles: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in generation_rows:
        profile = str(row.get("profile") or "unknown")
        profiles.setdefault((profile, int(row.get("output_budget", 0))), []).append(row)
    for (profile, budget), profile_rows in sorted(profiles.items()):
        lines.extend([
            f"## Profile `{profile}` | Output `-n {budget}`",
            "",
            f"**Test occurred between:** {test_time_window(profile_rows, budget)}",
            "",
            "| Test | Model | Context | Generation | Compiled | Our-test (Pi-check) | Token/s | Duration (min) | Peak VRAM (MiB) | All gates |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
        ])
        for generation in sorted(
            profile_rows,
            key=lambda row: (model_name(row), int(row.get("context", 0))),
        ):
            matches = [
                row
                for row in validation_rows
                if row.get("run_id") == generation.get("run_id")
                and row.get("model") == generation.get("model")
                and int(row.get("context", 0)) == int(generation.get("context", 0))
                and int(row.get("output_budget", 0)) == budget
            ]
            validation = matches[-1] if matches else {}
            checker_path = Path(str(validation.get("raw_output", "")))
            checker_available = bool(validation) and checker_path.exists()
            checker_score = independent_score(validation)[0] if checker_available else 0
            checker_value = f"{checker_score}/6" if checker_available else "N/A"
            compiled = (
                "N/A"
                if not validation
                else ("true" if compile_status(validation) == "success" else "false")
            )
            all_gates = "✅" if compiled == "true" and checker_score == 6 else ""
            lines.append(
                f"| {generation.get('prompt_name', 'pi-1000-digits')} | {model_name(generation)} | "
                f"{int(generation.get('context', 0)) // 1024}K | "
                f"{test_completion(generation)} | {compiled} | {checker_value} | "
                f"{generation_speed(generation)} | {duration_minutes(generation)} | "
                f"{peak_vram(generation)} | {all_gates} |"
            )
        lines.append("")
    return "\n".join(lines)


def summary_records(
    rows: list[dict[str, Any]], test_name: str | None = None
) -> list[dict[str, Any]]:
    if test_name is not None:
        rows = [row for row in rows if str(row.get("prompt_name", "")) == test_name]
    generation_rows = latest_generation_rows([
        row
        for row in rows
        if row.get("stage") == "quality-normalize-events"
        and int(row.get("output_budget", 0)) in {8192, 16384}
    ])
    validation_rows = [row for row in rows if row.get("stage") == "quality-validation"]
    records: list[dict[str, Any]] = []
    for generation in generation_rows:
        matches = [
            row
            for row in validation_rows
            if row.get("run_id") == generation.get("run_id")
            and row.get("model") == generation.get("model")
            and int(row.get("context", 0)) == int(generation.get("context", 0))
            and int(row.get("output_budget", 0))
            == int(generation.get("output_budget", 0))
        ]
        validation = matches[-1] if matches else {}
        is_pi = generation.get("prompt_name") == "pi-1000-digits"
        records.append({
            "model": model_name(generation),
            "model_path": generation.get("model"),
            "test": generation.get("prompt_name"),
            "context": int(generation.get("context", 0)),
            "output_budget": int(generation.get("output_budget", 0)),
            "test_completion": generation.get("status") == "generation-pass",
            "compiled": bool(validation) and compile_status(validation) == "success",
            "model_test": None
            if is_pi
            else (unittest_score(validation)[0] if validation else 0),
            "our_test": independent_score(validation)[0] if validation else 0,
            "checker": "pi-check" if is_pi else "independent-check",
            "token_per_second": generation_speed(generation),
            "duration_seconds": generation.get("duration_seconds"),
            "vram_peak_mib": (generation.get("gpu_stats") or {}).get("vram_peak_mib"),
            "status": validation.get("status", "pending"),
            "log": generation.get("log"),
        })
    return sorted(
        records,
        key=lambda item: (item["output_budget"], item["model"], item["context"]),
    )


def summary_yaml(rows: list[dict[str, Any]], test_name: str | None = None) -> str:
    lines = [
        "version: 1",
        "description: Controlled coding test summary generated from r2 ledgers.",
        "results:",
    ]
    for record in summary_records(rows, test_name):
        lines.append("  -")
        for key, value in record.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif value is None:
                rendered = "null"
            elif isinstance(value, (int, float)):
                rendered = str(value)
            else:
                rendered = json.dumps(str(value))
            lines.append(f"    {key}: {rendered}")
    return "\n".join(lines) + "\n"


def output_budget(row: dict[str, Any]) -> int:
    value = row.get("output_budget")
    if value is not None:
        return int(value)
    outcome = str(row.get("outcome", ""))
    return (
        1024
        if "compile=" in outcome or row.get("stage", "").startswith("quality-")
        else 0
    )


def format_score(score: int) -> str:
    value = f"{score}/6"
    return f"<strong>{value}</strong>" if score == 6 else value


def format_compile(status: str) -> str:
    return (
        f"<strong>compile={status}</strong>"
        if status == "success"
        else f"compile={status}"
    )


def report_markdown(rows: list[dict[str, Any]], log_root: Path) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(model_name(row), []).append(row)

    lines = [
        "# Model Test Results",
        "",
        "> Human-readable digest generated from the durable per-model ledgers. Refreshes after every completed test.",
        ">",
        "> **Important:** Existing coding-quality results are preliminary because they used `-n 1024`. The controlled next round uses the parameters documented in `docs/test-protocol.md`.",
        "",
        "## Comparison Overview",
        "",
        "| Model | Load | Highest allocation pass | Quality contexts | Latest quality outcome | Artifacts |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for name, model_rows in sorted(grouped.items()):
        load_rows = [row for row in model_rows if row.get("stage") == "load"]
        allocation_rows = [
            row for row in model_rows if row.get("stage") == "allocation"
        ]
        quality_rows = [
            row
            for row in model_rows
            if str(row.get("stage", "")).startswith("quality-")
        ]
        load_status = load_rows[-1].get("status", "pending") if load_rows else "pending"
        passed_contexts = [
            int(row["context"])
            for row in allocation_rows
            if row.get("status") == "allocation-pass"
        ]
        highest = str(max(passed_contexts)) if passed_contexts else "none"
        validation_rows = [
            row
            for row in quality_rows
            if row.get("stage") in {"quality-validation", "quality-revalidation"}
        ]
        latest_by_context: dict[int, dict[str, Any]] = {}
        for row in validation_rows:
            latest_by_context[int(row.get("context", 0))] = row
        quality_contexts = (
            ", ".join(
                f"n={output_budget(row)} c={row.get('context')}: {format_compile(compile_status(row))}, "
                f"m-test={format_score(unittest_score(row)[0])}, "
                f"our-test={format_score(independent_score(row)[0])}"
                for row in sorted(
                    latest_by_context.values(),
                    key=lambda item: int(item.get("context", 0)),
                )
            )
            or "pending"
        )
        final_quality = "pending"
        if validation_rows:
            final_quality = validation_rows[-1].get("status", "pending")
        artifact_path = (
            Path(str(validation_rows[-1].get("ledger", log_root))).parent
            if validation_rows
            else log_root
        )
        lines.append(
            f"| {name} | {load_status} | {highest} | {quality_contexts} | "
            f"{final_quality} | `{artifact_path}` |"
        )

    lines.extend([
        "",
        "## Quality Outcomes",
        "",
        "Each row is a completed coding-quality validation. `generation-pass` means only that the model produced output; it is not a quality pass.",
        "",
        "| Date | Model | Context | Result | Outcome | Validation artifact |",
        "| --- | --- | ---: | --- | --- | --- |",
    ])
    for row in rows:
        if row.get("stage") not in {"quality-validation", "quality-revalidation"}:
            continue
        lines.append(
            f"| {row.get('date', '')} | {model_name(row)} | {row.get('context', '')} | "
            f"{format_compile(compile_status(row))}; m-test={format_score(unittest_score(row)[0])}; "
            f"our-test={format_score(independent_score(row)[0])}; {row.get('status', '')} | "
            f"{str(row.get('outcome', '')).replace('|', '\\|')} | "
            f"`{row.get('log', '')}` |"
        )

    lines.extend([
        "",
        "## Coding Test Matrix",
        "",
        "Each cell reports compile status, model-authored tests (`m-test`), and independent tests (`our-test`). Both test scores are out of six; dependency compliance remains a separate gate. Preliminary `n=1024` results are separate from controlled budgets.",
        "",
    ])
    matrix_models = sorted(grouped)
    for budget in (8192, 16384):
        lines.extend([
            f"### Output budget `-n {budget}`",
            "",
            "| Context | " + " | ".join(matrix_models) + " |",
            "| ---: | " + " | ".join("---:" for _ in matrix_models) + " |",
        ])
        for context in (4096, 16384, 32768, 65536, 98304, 131072, 196608, 262144):
            cells: list[str] = []
            for name in matrix_models:
                validation_rows = [
                    row
                    for row in grouped[name]
                    if row.get("stage")
                    in {"quality-validation", "quality-revalidation"}
                    and int(row.get("context", 0)) == context
                    and output_budget(row) == budget
                ]
                if validation_rows:
                    row = validation_rows[-1]
                    cells.append(
                        f"{format_compile(compile_status(row))}<br>"
                        f"m-test={format_score(unittest_score(row)[0])}<br>"
                        f"our-test={format_score(independent_score(row)[0])}"
                    )
                else:
                    cells.append("pending")
            lines.append(f"| {context // 1024}K | " + " | ".join(cells) + " |")
        lines.append("")

    lines.extend([
        "",
        "## Recent Checkpoints",
        "",
        "| Date | Model | Stage | Context | Status | Outcome |",
        "| --- | --- | --- | ---: | --- | --- |",
    ])
    for row in rows[-20:]:
        lines.append(
            f"| {row.get('date', '')} | {model_name(row)} | {row.get('stage', '')} | "
            f"{row.get('context', '')} | {row.get('status', '')} | "
            f"{str(row.get('outcome', '')).replace('|', '\\|')} |"
        )
    lines.extend([
        "",
        "## Reading the Results",
        "",
        "- `allocation-pass` is a memory/allocation result only.",
        "- `practical-pass` requires extraction, compilation, model tests, independent checks, and dependency compliance.",
        "- The `x/6` score covers only the model-authored unittest suite; it is not the final quality verdict.",
        "- Raw outputs and detailed logs remain under the model artifact folder shown above.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--logs", type=Path, required=True)
    arguments = parser.parse_args()
    rows = read_rows(arguments.logs)
    update_evidence(arguments.evidence, markdown(rows))
    reports = report_directory(arguments.evidence)
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / REPORT_NAME
    report_path.write_text(report_markdown(rows, arguments.logs), encoding="utf-8")
    summary_path = reports / SUMMARY_REPORT_NAME
    summary_path.write_text(summary_markdown(rows), encoding="utf-8")
    summary_yaml_path = reports / SUMMARY_YAML_NAME
    summary_yaml_path.write_text(summary_yaml(rows), encoding="utf-8")
    test_names = sorted({
        str(row.get("prompt_name"))
        for row in rows
        if row.get("stage") == "quality-normalize-events" and row.get("prompt_name")
    })
    for test_name in test_names:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", test_name)
        test_report = reports / f"test-summary-{safe_name}.md"
        test_yaml = reports / f"test-summary-{safe_name}.yaml"
        test_report.write_text(summary_markdown(rows, test_name), encoding="utf-8")
        test_yaml.write_text(summary_yaml(rows, test_name), encoding="utf-8")
        print(f"Updated {test_report}.")
        print(f"Updated {test_yaml}.")
    print(f"Updated {arguments.evidence} from {len(rows)} ledger rows.")
    print(f"Updated {report_path}.")
    print(f"Updated {summary_path}.")
    print(f"Updated {summary_yaml_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
