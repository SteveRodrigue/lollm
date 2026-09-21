"""Run configured llama.cpp tests with durable artifacts and retry support."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "tools" / "reconcile_evidence.py"


@dataclass(frozen=True)
class Case:
    model: dict[str, Any]
    test: dict[str, Any]
    profile: dict[str, Any]
    context: int
    output_budget: int


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_folder(model: dict[str, Any]) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(model["id"])) + "-runner"


def merge_parameters(common: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for key, value in common.items():
        parameters[key] = value.get("value") if isinstance(value, dict) else value
    parameters.update(profile.get("parameters", {}))
    return parameters


def resolve_path(root: Path, value: str) -> Path:
    expanded = os.path.expandvars(value)
    unresolved = re.findall(r"\$\{([^}]+)\}|%([^%]+)%", expanded)
    if unresolved:
        names = sorted({name or alternate for name, alternate in unresolved})
        raise ValueError(
            "Missing environment variable(s) for configured path: " + ", ".join(names)
        )
    path = Path(expanded)
    return path if path.is_absolute() else root / path


def resolve_runtime(
    models_config: dict[str, Any], runtime_id: str | None = None
) -> tuple[str, dict[str, Any], Path]:
    selected_id = str(runtime_id or models_config.get("default_runtime", "vulkan"))
    runtimes = models_config.get("runtimes", {})
    if not isinstance(runtimes, dict) or selected_id not in runtimes:
        raise ValueError(f"Configured runtime is missing: {selected_id}")
    runtime_config = runtimes[selected_id]
    if not isinstance(runtime_config, dict):
        raise ValueError(f"Runtime configuration must be a mapping: {selected_id}")
    return (
        selected_id,
        runtime_config,
        resolve_path(ROOT, str(runtime_config["executable"])),
    )


def command_for(
    case: Case,
    executable: Path,
    prompt: str,
    runtime_config: dict[str, Any],
) -> list[str]:
    parameters = merge_parameters(case.profile.get("common", {}), case.profile)
    model_path = resolve_path(ROOT, str(case.model["path"]))
    devices = [str(device) for device in runtime_config.get("devices", [])]
    gpu_indices = [int(index) for index in runtime_config.get("gpu_indices", [0])]
    command = [
        str(executable),
        "-m",
        str(model_path),
        "-ngl",
        str(parameters.get("gpu_layers", 10)),
        "--device",
        ",".join(devices),
        "--split-mode",
        str(runtime_config.get("split_mode", "none")),
        "--main-gpu",
        str(gpu_indices[0] if gpu_indices else 0),
        "--load-mode",
        str(parameters.get("load_mode", "mmap")),
        "-c",
        str(case.context),
        "-n",
        str(case.output_budget),
        "--temp",
        str(parameters.get("temperature", 0.2)),
        "--top-p",
        str(parameters.get("top_p", 0.95)),
        "--seed",
        str(parameters.get("seed", 42)),
        "--reasoning",
        str(parameters.get("reasoning", "auto")),
        "--reasoning-budget",
        str(parameters.get("reasoning_budget", 4096)),
        "--single-turn",
        "--simple-io",
        "--color",
        "off",
        "-p",
        prompt,
    ]
    return command


def sample_gpu(gpu_log: Path, rows: list[str]) -> None:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return
    result = subprocess.run(
        [
            executable,
            "--query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            rows.append(line.strip())


def run_process(
    command: list[str], log_path: Path, gpu_log: Path
) -> tuple[int, float, str, dict[str, Any]]:
    started = time.perf_counter()
    gpu_rows: list[str] = []
    sample_gpu(gpu_log, gpu_rows)
    with log_path.open("wb") as log_stream:
        process = subprocess.Popen(
            command,
            stdout=log_stream,
            stderr=subprocess.STDOUT,
        )
        next_heartbeat = 15.0
        while process.poll() is None:
            sample_gpu(gpu_log, gpu_rows)
            elapsed = time.perf_counter() - started
            if elapsed >= next_heartbeat:
                print(
                    f"[runner] still running: {int(elapsed)}s; log={log_path}",
                    flush=True,
                )
                next_heartbeat += 15.0
            time.sleep(1.0)
        exit_code = process.wait()
    sample_gpu(gpu_log, gpu_rows)
    gpu_log.write_text(
        "timestamp, name, utilization.gpu [%], memory.used [MiB], memory.total [MiB]\n"
        + "\n".join(gpu_rows)
        + ("\n" if gpu_rows else ""),
        encoding="utf-8",
    )
    duration = time.perf_counter() - started
    output = log_path.read_bytes()
    stats: dict[str, Any] = {"status": "unavailable"}
    memory_values: list[float] = []
    utilization_values: list[float] = []
    for row in gpu_rows:
        fields = [field.strip() for field in row.split(",")]
        try:
            utilization_values.append(float(fields[2]))
            memory_values.append(float(fields[3]))
        except (IndexError, ValueError):
            continue
    if memory_values:
        stats = {
            "status": "available",
            "vram_peak_mib": max(memory_values),
            "gpu_utilization_peak_percent": max(utilization_values),
        }
    return exit_code, duration, output.decode("utf-8", errors="replace"), stats


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    if (
        raw.startswith((b"\xff\xfe", b"\xfe\xff"))
        or raw.count(b"\x00") > len(raw) // 10
    ):
        return raw.decode("utf-16", errors="replace")
    return raw.decode("utf-8-sig", errors="replace")


def classify_process_output(exit_code: int, output: str) -> str:
    lowered = output.lower()
    if re.search(r"outofmemory|out of memory|out-of-memory|device memory", lowered):
        return "out-of-memory"
    if re.search(
        r"context.*(exceed|overflow|full)|prompt.*too long|too many tokens", lowered
    ):
        return "context-overflow"
    if "invalid argument" in lowered or "unknown value for" in lowered:
        return "invalid-arguments"
    if re.search(r"generation:\s*0(?:\.0)?\s*t/s", lowered):
        return "zero-generation"
    if exit_code != 0:
        return "process-error"
    return "none"


def experiment_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("model"),
        row.get("prompt_name"),
        row.get("profile"),
        row.get("stage"),
        row.get("context"),
        row.get("output_budget"),
    )


def upsert_row(ledger: Path, row: dict[str, Any]) -> None:
    existing: list[dict[str, Any]] = []
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                existing.append(json.loads(line))
    key = experiment_key(row)
    replaced = False
    for index, previous in enumerate(existing):
        if experiment_key(previous) == key:
            existing[index] = row
            replaced = True
            break
    if not replaced:
        existing.append(row)
    ledger.write_text(
        "".join(json.dumps(item, ensure_ascii=True) + "\n" for item in existing),
        encoding="utf-8",
    )


def reconcile() -> None:
    subprocess.run(
        [
            sys.executable,
            str(RECONCILER),
            "--evidence",
            str(ROOT / "docs/evidences.md"),
            "--logs",
            str(ROOT / "logs"),
        ],
        check=True,
    )


def prior_failed_keys(
    log_root: Path, summary_path: Path | None = None
) -> set[tuple[str, str, int, int]]:
    if summary_path and summary_path.exists():
        summary = load_yaml(summary_path)
        results = summary.get("results", [])
        latest: dict[tuple[str, str, int, int], dict[str, Any]] = {}
        for row in results:
            key = (
                str(row.get("model_path")),
                str(row.get("test")),
                int(row.get("context", 0)),
                int(row.get("output_budget", 0)),
            )
            latest[key] = row
        return {
            key for key, row in latest.items() if row.get("status") != "practical-pass"
        }
    latest: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for ledger in log_root.glob("*/results.jsonl"):
        for line in ledger.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("stage") != "quality-validation":
                continue
            if "output_budget" not in row:
                continue
            key = (
                str(row.get("model")),
                str(row.get("prompt_name")),
                int(row.get("context", 0)),
                int(row["output_budget"]),
            )
            latest[key] = row
    return {key for key, row in latest.items() if row.get("status") != "practical-pass"}


def validate_case(
    case: Case, raw_path: Path, stem: str
) -> tuple[int, int, int, int, Path]:
    test = case.test
    language = test.get("language", "python")
    generated = raw_path.with_name(f"{stem}.py")
    extraction_log = raw_path.with_name(f"{stem}-extraction.txt")
    compile_log = raw_path.with_name(f"{stem}-compile.txt")
    unittest_log = raw_path.with_name(f"{stem}-unittest.txt")
    independent_json = raw_path.with_name(f"{stem}-independent.json")
    independent_log = raw_path.with_name(f"{stem}-independent.txt")

    if language != "python":
        output = read_text_file(raw_path)
        prompt = case.test.get("prompt_file_location", "")
        expected = str(test.get("our_test", {}).get("expected_response", ""))
        response_match = re.search(r">\s.*?\n(.*?)\n\s*\[ Prompt:", output, re.DOTALL)
        response = response_match.group(1).strip() if response_match else ""
        normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.lower())
        passed = bool(expected) and normalize(response) == normalize(expected)
        independent_log.write_text(
            f"expected={expected}\nresponse={response}\npassed={passed}\n",
            encoding="utf-8",
        )
        return 0, 0, 0, 0 if passed else 1, independent_log

    extraction = subprocess.run(
        [
            sys.executable,
            str(ROOT / test.get("extraction_tool", "tools/extract_model_python.py")),
            str(raw_path),
            str(generated),
            "--function",
            str(test.get("extraction_function", "normalize_events")),
            "--metadata",
            str(raw_path.with_name(f"{stem}-extraction.json")),
        ],
        capture_output=True,
    )
    extraction_log.write_bytes(extraction.stdout + extraction.stderr)
    if extraction.returncode != 0:
        compile_code = unittest_code = independent_code = 1
        compile_log.write_text("Skipped because extraction failed\n", encoding="utf-8")
        unittest_log.write_text("Skipped because extraction failed\n", encoding="utf-8")
        independent_log.write_text(
            "Skipped because extraction failed\n", encoding="utf-8"
        )
        return (
            extraction.returncode,
            compile_code,
            unittest_code,
            independent_code,
            independent_log,
        )

    compile_result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(generated)], capture_output=True
    )
    compile_log.write_bytes(compile_result.stdout + compile_result.stderr)
    compile_code = compile_result.returncode

    required_tests = bool(test.get("model_tests", {}).get("required", False))
    if required_tests:
        unittest_result = subprocess.run(
            [sys.executable, "-m", "unittest", str(generated), "-v"],
            capture_output=True,
        )
        unittest_log.write_bytes(unittest_result.stdout + unittest_result.stderr)
        unittest_code = unittest_result.returncode
    else:
        unittest_log.write_text(
            "Skipped: model-authored tests are not required by this test config.\n",
            encoding="utf-8",
        )
        unittest_code = 0

    checker = test.get("our_test", {}).get("checker")
    if checker:
        independent_result = subprocess.run(
            [
                sys.executable,
                str(ROOT / checker),
                str(generated),
                "--json-out",
                str(independent_json),
            ],
            capture_output=True,
        )
        independent_log.write_bytes(
            independent_result.stdout + independent_result.stderr
        )
        independent_code = independent_result.returncode
    else:
        independent_log.write_text(
            "Skipped: no independent checker configured.\n", encoding="utf-8"
        )
        independent_code = 0

    return 0, compile_code, unittest_code, independent_code, independent_log


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tests-config", type=Path, default=ROOT / "configs/tests.yaml"
    )
    parser.add_argument("--models", type=Path, default=ROOT / "configs/models.yaml")
    parser.add_argument(
        "--summary", type=Path, default=ROOT / "reports/latest/test-summary.yaml"
    )
    parser.add_argument(
        "--model", action="append", help="Model ID; repeat for multiple models"
    )
    parser.add_argument(
        "--test",
        action="append",
        dest="test_ids",
        help="Test ID; repeat for multiple tests",
    )
    parser.add_argument("--profile", help="Override the model's default profile")
    parser.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run all compatible generic profiles for each selected model",
    )
    parser.add_argument("--context", type=int, action="append")
    parser.add_argument("--output-budget", type=int, action="append")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Run only previously failed quality cases",
    )
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    tests_config = load_yaml(arguments.tests_config)
    models_config = load_yaml(arguments.models)
    test_defaults = tests_config.get("test_defaults", {})
    tests = {item["id"]: item for item in tests_config.get("tests", [])}
    models = {item["id"]: item for item in models_config.get("models", [])}
    profiles = models_config.get("profiles", {})
    common = models_config.get("common_parameters", {})
    selected_models = arguments.model or [
        model_id
        for model_id, model in models.items()
        if model.get("status") != "incompatible-inconsistent"
    ]
    selected_tests = arguments.test_ids or list(tests)

    def profile_names(model: dict[str, Any], test: dict[str, Any]) -> list[str]:
        if arguments.all_profiles and test.get("language") == "python":
            compatible: list[str] = []
            for profile_name, profile in profiles.items():
                if profile.get("status") == "incompatible-inconsistent":
                    continue
                profile_model = profile.get("model")
                if profile_model and profile_model != model.get("id"):
                    continue
                compatible.append(profile_name)
            return compatible
        if arguments.profile:
            return [arguments.profile]
        return [
            model.get("default_profile")
            if test.get("id") == "hello-readiness"
            else "controlled-quality-8k"
        ]

    failed = (
        prior_failed_keys(ROOT / "logs", arguments.summary)
        if arguments.retry_failed
        else set()
    )
    contexts = arguments.context
    budgets = arguments.output_budget

    planned_cases = 0
    for planned_model_id in selected_models:
        planned_model = models[planned_model_id]
        for planned_test_id in selected_tests:
            planned_test = tests[planned_test_id]
            for planned_profile_name in profile_names(planned_model, planned_test):
                planned_profile = profiles.get(planned_profile_name, {})
                planned_parameters = planned_profile.get("parameters", {})
                planned_contexts = contexts or (
                    [int(planned_parameters["context"])]
                    if "context" in planned_parameters
                    and (arguments.profile or arguments.all_profiles)
                    else test_defaults.get("contexts", [4096])
                )
                planned_budgets = budgets or (
                    [int(planned_parameters["output_tokens"])]
                    if "output_tokens" in planned_parameters
                    and (arguments.profile or arguments.all_profiles)
                    else test_defaults.get("output_budgets", [8192])
                )
                for planned_budget in planned_budgets:
                    for planned_context in planned_contexts:
                        planned_key = (
                            str(resolve_path(ROOT, str(planned_model["path"]))),
                            planned_test_id,
                            planned_context,
                            planned_budget,
                        )
                        if not arguments.retry_failed or planned_key in failed:
                            planned_cases += 1
    case_number = 0
    print(f"[runner] Planned tests: {planned_cases}", flush=True)

    for model_id in selected_models:
        model = models[model_id]
        for test_id in selected_tests:
            test = tests[test_id]
            for profile_name in profile_names(model, test):
                profile = dict(profiles.get(profile_name, {}))
                profile["common"] = common
                prompt_path = resolve_path(ROOT, str(test["prompt_file_location"]))
                prompt = prompt_path.read_text(
                    encoding=test_defaults.get("prompt_encoding", "utf-8")
                )
                prompt_hash = sha256_file(prompt_path)
                profile_parameters = profile.get("parameters", {})
                runtime_id, runtime_config, executable = resolve_runtime(
                    models_config, profile.get("runtime")
                )
                test_contexts = contexts or (
                    [int(profile_parameters["context"])]
                    if "context" in profile_parameters
                    and (arguments.profile or arguments.all_profiles)
                    else test_defaults.get("contexts", [4096])
                )
                test_budgets = budgets or (
                    [int(profile_parameters["output_tokens"])]
                    if "output_tokens" in profile_parameters
                    and (arguments.profile or arguments.all_profiles)
                    else test_defaults.get("output_budgets", [8192])
                )
                for budget in test_budgets:
                    for context in test_contexts:
                        key = (
                            str(resolve_path(ROOT, str(model["path"]))),
                            test_id,
                            context,
                            budget,
                        )
                        if arguments.retry_failed and key not in failed:
                            continue
                        case_number += 1
                        case = Case(model, test, profile, context, budget)
                        profile_tag = re.sub(
                            r"[^A-Za-z0-9_.-]+", "-", str(profile_name)
                        )
                        stem = f"{test_id}-{profile_tag}-n{budget}-c{context}"
                        directory = ROOT / "logs" / model_folder(model)
                        directory.mkdir(parents=True, exist_ok=True)
                        log_path = directory / f"{stem}.log"
                        gpu_log = directory / f"{stem}-gpu.csv"
                        ledger = directory / "results.jsonl"
                        command = command_for(case, executable, prompt, runtime_config)
                        if arguments.dry_run:
                            print(
                                f"[runner] Test {case_number} of {planned_cases}: "
                                f"would run model={model_id} test={test_id} "
                                f"profile={profile_name} context={context} output={budget}",
                                flush=True,
                            )
                            print(" ".join(command))
                            continue
                        print(
                            f"[runner] Test {case_number} of {planned_cases}: "
                            f"starting model={model_id} test={test_id} "
                            f"profile={profile_name} context={context} output={budget}",
                            flush=True,
                        )
                        now_utc = datetime.now(timezone.utc)
                        run_id = (
                            now_utc.strftime("%Y%m%d-%H%M%S")
                            + f"Z-n{budget}-c{context}"
                        )
                        exit_code, duration, process_output, gpu_stats = run_process(
                            command, log_path, gpu_log
                        )
                        raw_path = directory / f"{stem}.raw-output.txt"
                        raw_path.write_bytes(log_path.read_bytes())
                        failure_class = classify_process_output(
                            exit_code, process_output
                        )
                        generation_status = (
                            "generation-pass"
                            if exit_code == 0
                            and failure_class not in {"zero-generation"}
                            else "generation-fail"
                        )
                        common_row = {
                            "date": now_utc.isoformat(timespec="microseconds").replace(
                                "+00:00", "Z"
                            ),
                            "run_id": run_id,
                            "model": str(resolve_path(ROOT, str(model["path"]))),
                            "runtime": runtime_config.get("version"),
                            "runtime_id": runtime_id,
                            "backend": runtime_config.get("backend"),
                            "gpu_layers": profile.get("parameters", {}).get(
                                "gpu_layers",
                                common.get("gpu_layers", {}).get("value", 10),
                            ),
                            "stage": "quality-normalize-events",
                            "context": context,
                            "output_budget": budget,
                            "prompt_name": test_id,
                            "profile": profile_name,
                            "reasoning_mode": profile_parameters.get(
                                "reasoning",
                                common.get("reasoning", {}).get("value", "auto"),
                            ),
                            "reasoning_budget": profile_parameters.get(
                                "reasoning_budget",
                                common.get("reasoning_budget", {}).get("value", 4096),
                            ),
                            "temperature": profile_parameters.get(
                                "temperature",
                                common.get("temperature", {}).get("value", 0.2),
                            ),
                            "top_p": profile_parameters.get(
                                "top_p", common.get("top_p", {}).get("value", 0.95)
                            ),
                            "seed": profile_parameters.get(
                                "seed", common.get("seed", {}).get("value", 42)
                            ),
                            "prompt_file": str(prompt_path),
                            "prompt_sha256": prompt_hash,
                            "status": generation_status,
                            "outcome": f"failure_class={failure_class}; pending validation",
                            "failure_class": failure_class,
                            "exit_code": exit_code,
                            "duration_seconds": round(duration, 3),
                            "log": str(log_path),
                            "raw_output": str(raw_path),
                            "gpu_log": str(gpu_log),
                            "gpu_stats": gpu_stats,
                        }
                        upsert_row(ledger, common_row)
                        reconcile()
                        print(
                            f"[runner] generation complete: status={generation_status} "
                            f"duration={duration / 60:.2f}min log={log_path}",
                            flush=True,
                        )
                        if exit_code != 0:
                            continue
                        print(
                            f"[runner] validating output model={model_id} "
                            f"context={context} output={budget}",
                            flush=True,
                        )
                        (
                            extraction,
                            compile_code,
                            unittest_code,
                            independent_code,
                            independent_log,
                        ) = validate_case(case, raw_path, stem)
                        final_status = (
                            "practical-pass"
                            if extraction == 0
                            and compile_code == 0
                            and unittest_code == 0
                            and independent_code == 0
                            else "practical-fail"
                        )
                        upsert_row(
                            ledger,
                            {
                                **common_row,
                                "stage": "quality-validation",
                                "status": final_status,
                                "outcome": f"extraction={extraction}; compile={compile_code}; unittest={unittest_code}; independent={independent_code}",
                                "exit_code": independent_code,
                                "duration_seconds": 0,
                                "log": str(independent_log),
                                "raw_output": str(
                                    raw_path.with_name(f"{stem}-independent.json")
                                ),
                            },
                        )
                        reconcile()
                        print(
                            f"[runner] validation complete: status={final_status} "
                            f"compile={compile_code} model_tests={unittest_code} "
                            f"our_tests={independent_code}",
                            flush=True,
                        )
    if arguments.dry_run:
        print(
            f"[runner] Dry run complete: {planned_cases} tests would be performed.",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
