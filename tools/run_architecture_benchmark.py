"""Run isolated runtime and GPU-layer architecture benchmarks."""

from __future__ import annotations

import argparse
import csv
import ctypes
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "Reply with exactly READY, then continue with a concise technical explanation of GPU offload."
GENERATION_RE = re.compile(r"Generation:\s*([0-9.]+)\s*t/s")
PROMPT_RE = re.compile(r"Prompt eval time.*?([0-9.]+)\s*t/s")
RESULT_FIELDS = [
    "run_id",
    "backend",
    "runtime",
    "gpu_index",
    "gpu_name",
    "model",
    "gpu_layers",
    "repeat",
    "context",
    "output_tokens",
    "status",
    "exit_code",
    "duration_seconds",
    "process_peak_rss_mib",
    "process_peak_private_mib",
    "system_ram_total_mib",
    "system_ram_available_mib_start",
    "system_ram_available_mib_end",
    "system_ram_peak_used_mib",
    "peak_gpu_utilization_percent",
    "peak_vram_mib",
    "generation_tokens_per_second",
    "prompt_tokens_per_second",
    "log",
]


class MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_physical", ctypes.c_ulonglong),
        ("available_physical", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("available_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("available_virtual", ctypes.c_ulonglong),
        ("available_extended_virtual", ctypes.c_ulonglong),
    ]


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("page_fault_count", ctypes.c_ulong),
        ("peak_working_set_size", ctypes.c_size_t),
        ("working_set_size", ctypes.c_size_t),
        ("quota_peak_paged_pool_usage", ctypes.c_size_t),
        ("quota_paged_pool_usage", ctypes.c_size_t),
        ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
        ("quota_non_paged_pool_usage", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t),
        ("peak_pagefile_usage", ctypes.c_size_t),
    ]


def sample_memory(process_id: int) -> dict[str, float]:
    if not hasattr(ctypes, "windll"):
        return {}
    memory_status = MemoryStatusEx()
    memory_status.length = ctypes.sizeof(memory_status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status)):
        return {}
    process_handle = ctypes.windll.kernel32.OpenProcess(0x0410, False, process_id)
    if not process_handle:
        return {}
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    try:
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            process_handle, ctypes.byref(counters), counters.cb
        ):
            return {}
    finally:
        ctypes.windll.kernel32.CloseHandle(process_handle)
    mib = 2**20
    return {
        "process_peak_rss_mib": counters.peak_working_set_size / mib,
        "process_peak_private_mib": counters.peak_pagefile_usage / mib,
        "system_ram_total_mib": memory_status.total_physical / mib,
        "system_ram_available_mib": memory_status.available_physical / mib,
        "system_ram_used_mib": (
            memory_status.total_physical - memory_status.available_physical
        )
        / mib,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run architecture-only llama.cpp benchmarks in an isolated directory."
    )
    parser.add_argument(
        "--models-config",
        type=Path,
        default=ROOT / "configs/models.yaml",
        help="Model registry; eligible models are used when --model is omitted.",
    )
    parser.add_argument(
        "--model",
        action="append",
        help="Model ID or GGUF path; repeat to restrict the matrix.",
    )
    parser.add_argument(
        "--vulkan-runtime",
        type=Path,
        help="Override the Vulkan executable; defaults to the model registry runtime.",
    )
    parser.add_argument(
        "--cuda-runtime",
        type=Path,
        help="Override the CUDA executable; defaults to the downloaded isolated runtime.",
    )
    parser.add_argument("--backend", choices=("Vulkan", "CUDA", "Both"))
    parser.add_argument(
        "--gpu-layers",
        type=int,
        nargs="+",
        default=None,
    )
    parser.add_argument(
        "--context",
        type=int,
        nargs="+",
        default=None,
        help="One or more context sizes; defaults to common_parameters.context.values.",
    )
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--repeats", type=int)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and print the planned test count without writing files or running inference.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("logs") / "architecture-optimization",
    )
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    expanded = os.path.expandvars(str(path))
    unresolved = re.findall(r"\$\{([^}]+)\}|%([^%]+)%", expanded)
    if unresolved:
        names = sorted({name or alternate for name, alternate in unresolved})
        raise ValueError(
            "Missing environment variable(s) for configured path: " + ", ".join(names)
        )
    resolved = Path(expanded)
    return resolved if resolved.is_absolute() else ROOT / resolved


def load_yaml(path: Path) -> dict[str, object]:
    with resolve_path(path).open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a YAML mapping: {path}")
    return value


def configured_models(args: argparse.Namespace) -> list[dict[str, str]]:
    configuration = load_yaml(args.models_config)
    models = configuration.get("models", [])
    if not isinstance(models, list):
        raise TypeError("models config must contain a models list")
    by_id = {
        str(model["id"]): model
        for model in models
        if isinstance(model, dict) and "id" in model
    }
    selected = args.model or list(by_id)
    result = []
    for selection in selected:
        model = by_id.get(selection)
        if model is None:
            path = resolve_path(Path(selection))
            model = {"id": path.stem, "path": str(path)}
        if model.get("status") == "incompatible-inconsistent":
            print(f"Skipping incompatible model: {model['id']}")
            continue
        result.append({"id": str(model["id"]), "path": str(model["path"])})
    if not result:
        raise ValueError("No eligible models selected")
    return result


def selected_runtimes(
    args: argparse.Namespace, configuration: dict[str, object]
) -> list[tuple[str, Path, list[str], list[int], str]]:
    runtimes: list[tuple[str, Path, list[str], list[int], str]] = []
    runtime_registry = configuration.get("runtimes", {})
    if not isinstance(runtime_registry, dict):
        raise TypeError("runtimes must be a mapping")

    def add_runtime(runtime_id: str, override: Path | None) -> None:
        runtime_config = runtime_registry.get(runtime_id)
        if not isinstance(runtime_config, dict):
            raise TypeError(f"Runtime is not configured: {runtime_id}")
        backend = str(runtime_config.get("backend", runtime_id))
        vendor = str(runtime_config.get("vendor", "NVIDIA"))
        gpu_indices = [int(index) for index in runtime_config.get("gpu_indices", [0])]
        devices = [str(device) for device in runtime_config.get("devices", [])]
        if not devices:
            raise ValueError(f"No devices configured for runtime {runtime_id}")
        path = resolve_path(override or Path(str(runtime_config["executable"])))
        runtimes.append((backend, path, devices, gpu_indices, vendor))

    if args.backend in ("Vulkan", "Both"):
        add_runtime("vulkan", args.vulkan_runtime)
    if args.backend in ("CUDA", "Both"):
        add_runtime("cuda", args.cuda_runtime)
    if not runtimes:
        raise ValueError("No architecture backend selected")
    return runtimes


def sample_gpu(gpu_indices: list[int]) -> tuple[str | None, float | None, float | None]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None, None
    names: list[str] = []
    utilizations: list[float] = []
    memories: list[float] = []
    for gpu_index in gpu_indices:
        result = subprocess.run(
            [
                executable,
                "-i",
                str(gpu_index),
                "--query-gpu=name,utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        try:
            name, utilization, memory = [
                value.strip() for value in result.stdout.split(",")
            ]
            names.append(name)
            utilizations.append(float(utilization))
            memories.append(float(memory))
        except (ValueError, TypeError):
            continue
    if not names:
        return None, None, None
    return "; ".join(names), max(utilizations), max(memories)


def validate_gpu_vendor(gpu_indices: list[int], vendor: str) -> None:
    if vendor.upper() != "NVIDIA":
        raise ValueError(
            f"Unsupported architecture GPU vendor {vendor!r}; "
            "add a vendor-specific runtime and telemetry provider first"
        )
    executable = shutil.which("nvidia-smi")
    if not executable:
        raise FileNotFoundError("nvidia-smi is required for NVIDIA architecture tests")
    for gpu_index in gpu_indices:
        result = subprocess.run(
            [
                executable,
                "-i",
                str(gpu_index),
                "--query-gpu=name",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        name = result.stdout.strip()
        if result.returncode != 0 or not name or "NVIDIA" not in name.upper():
            raise ValueError(
                f"GPU index {gpu_index} is not an NVIDIA GPU: {name or 'unavailable'}"
            )


def detect_gpu_info(gpu_indices: list[int]) -> tuple[str | None, float | None]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None
    names: list[str] = []
    total_memory_mib = 0.0
    for gpu_index in gpu_indices:
        result = subprocess.run(
            [
                executable,
                "-i",
                str(gpu_index),
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            continue
        try:
            name, memory = [value.strip() for value in result.stdout.split(",")]
            names.append(name)
            total_memory_mib += float(memory)
        except (ValueError, TypeError):
            continue
    if not names:
        return None, None
    return "; ".join(names), total_memory_mib


def run_command(
    executable: Path, arguments: list[str], log_path: Path, gpu_indices: list[int]
) -> tuple[int, str, str | None, float | None, float | None, dict[str, float]]:
    gpu_name = None
    peak_utilization = None
    peak_memory = None
    memory_stats: dict[str, float] = {}
    with log_path.open("w", encoding="utf-8", errors="replace") as log_stream:
        process = subprocess.Popen(
            [str(executable), *arguments],
            stdout=log_stream,
            stderr=subprocess.STDOUT,
            cwd=ROOT,
        )
        while process.poll() is None:
            name, utilization, memory = sample_gpu(gpu_indices)
            gpu_name = gpu_name or name
            if utilization is not None:
                peak_utilization = max(peak_utilization or utilization, utilization)
            if memory is not None:
                peak_memory = max(peak_memory or memory, memory)
            sample = sample_memory(process.pid)
            for key, value in sample.items():
                if key.endswith(("peak_rss_mib", "peak_private_mib")):
                    memory_stats[key] = max(memory_stats.get(key, 0.0), value)
                elif key.endswith("total_mib"):
                    memory_stats[key] = value
                elif key.endswith("available_mib"):
                    memory_stats.setdefault("system_ram_available_mib_start", value)
                    memory_stats["system_ram_available_mib_end"] = value
                elif key.endswith("used_mib"):
                    memory_stats["system_ram_peak_used_mib"] = max(
                        memory_stats.get("system_ram_peak_used_mib", 0.0), value
                    )
            time.sleep(0.5)
        exit_code = process.wait()
    return (
        exit_code,
        log_path.read_text(encoding="utf-8", errors="replace"),
        gpu_name,
        peak_utilization,
        peak_memory,
        memory_stats,
    )


def write_matrix_report(
    path: Path, rows: list[dict[str, object]], expected_repeats: int
) -> None:
    grouped: dict[tuple[str, str, int, int], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            str(row["backend"]),
            str(row["model"]),
            int(row["context"]),
            int(row["gpu_layers"]),
        )
        grouped.setdefault(key, []).append(row)
    backends = sorted({str(row["backend"]) for row in rows})
    models = sorted({str(row["model"]) for row in rows})
    contexts = sorted({int(row["context"]) for row in rows})
    layers = sorted({int(row["gpu_layers"]) for row in rows})
    lines = [
        "# Architecture Benchmark Matrix",
        "",
        "Each cell is `status; average generation t/s; peak VRAM MiB` across repeats.",
        "",
    ]
    for backend in backends:
        for model in models:
            if not any(
                row["backend"] == backend and row["model"] == model for row in rows
            ):
                continue
            lines.extend([
                f"## {backend}: {Path(model).stem}",
                "",
                "| Context | " + " | ".join(f"-ngl {layer}" for layer in layers) + " |",
                "| ---: | " + " | ".join("---" for _ in layers) + " |",
            ])
            for context in contexts:
                cells = []
                for layer in layers:
                    values = grouped.get((backend, model, context, layer), [])
                    if not values:
                        cells.append("N/A")
                        continue
                    if len(values) < expected_repeats:
                        cells.append(f"incomplete ({len(values)}/{expected_repeats})")
                        continue
                    passed = [
                        row
                        for row in values
                        if row["status"] == "pass"
                        and row["generation_tokens_per_second"] is not None
                    ]
                    if not passed:
                        cells.append("fail")
                        continue
                    speed = sum(
                        float(row["generation_tokens_per_second"]) for row in passed
                    ) / len(passed)
                    memory_values = [
                        float(row["peak_vram_mib"])
                        for row in passed
                        if row["peak_vram_mib"] is not None
                    ]
                    memory = f"; {max(memory_values):.0f} MiB" if memory_values else ""
                    cells.append(f"pass; {speed:.1f} t/s{memory}")
                lines.append(f"| {context} | " + " | ".join(cells) + " |")
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def append_result(path: Path, row: dict[str, object]) -> None:
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=RESULT_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()


def main() -> int:
    args = parse_args()
    configuration = load_yaml(args.models_config)
    architecture_defaults = configuration.get("architecture_defaults", {})
    if not isinstance(architecture_defaults, dict):
        raise TypeError("architecture_defaults must be a mapping")
    default_backends = architecture_defaults.get("backends", ["Vulkan"])
    if not isinstance(default_backends, list) or not default_backends:
        raise ValueError("architecture_defaults.backends must be a non-empty list")
    if args.backend is None:
        if set(default_backends) == {"Vulkan", "CUDA"}:
            args.backend = "Both"
        elif len(default_backends) == 1:
            args.backend = str(default_backends[0])
        else:
            raise ValueError(
                "Use --backend when architecture defaults contain multiple backends"
            )
    args.gpu_layers = args.gpu_layers or architecture_defaults.get(
        "gpu_layers", [1, 5, 10, 15, 20, 30, 99]
    )
    args.output_tokens = args.output_tokens or int(
        architecture_defaults.get("output_tokens", 256)
    )
    args.repeats = args.repeats or int(architecture_defaults.get("repeats", 2))
    models = configured_models(args)
    configured_contexts = (
        configuration.get("common_parameters", {}).get("context", {}).get("values", [])
    )
    contexts = args.context or [int(value) for value in configured_contexts]
    if not contexts:
        raise ValueError("No contexts selected and no context.values configured")
    if (
        args.repeats < 1
        or any(context < 1 for context in contexts)
        or args.output_tokens < 1
    ):
        raise ValueError("repeats, context, and output-tokens must be positive")

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:8]}"
    run_directory = resolve_path(args.output_root) / run_id
    runtimes = selected_runtimes(args, configuration)
    available_runtimes = []
    for backend, runtime, devices, gpu_indices, split_mode in runtimes:
        if not runtime.exists():
            raise FileNotFoundError(f"Runtime does not exist: {runtime}")
        available_runtimes.append((backend, runtime, devices, gpu_indices, split_mode))
    for model in models:
        model_path = resolve_path(Path(model["path"]))
        if not model_path.exists():
            raise FileNotFoundError(f"Model does not exist: {model_path}")
    selected_gpu_indices = sorted({
        gpu_index
        for _, _, _, gpu_indices, _ in available_runtimes
        for gpu_index in gpu_indices
    })
    for _, _, _, gpu_indices, vendor in available_runtimes:
        validate_gpu_vendor(gpu_indices, vendor)
    gpu_name, gpu_memory_mib = detect_gpu_info(selected_gpu_indices)
    if not gpu_name or gpu_memory_mib is None:
        raise ValueError("Unable to identify the selected GPU")
    print(f"GPU: {gpu_name} (VRAM: {gpu_memory_mib / 1024:.1f} GB)", flush=True)
    total_tests = (
        len(available_runtimes)
        * len(models)
        * len(contexts)
        * len(args.gpu_layers)
        * args.repeats
    )
    if args.dry_run:
        print("Architecture benchmark dry run: configuration valid")
        print(f"Backends: {', '.join(backend for backend, *_ in available_runtimes)}")
        print(f"Models: {', '.join(model['id'] for model in models)}")
        print(f"Contexts: {', '.join(map(str, contexts))}")
        print(f"GPU layers: {', '.join(map(str, args.gpu_layers))}")
        print(f"Output tokens: {args.output_tokens}")
        print(f"Repeats: {args.repeats}")
        print(f"Tests planned: {total_tests}")
        return 0

    run_directory.mkdir(parents=True, exist_ok=True)
    (run_directory / "run-manifest.txt").write_text(
        "\n".join([
            f"run_id={run_id}",
            f"models={','.join(model['id'] for model in models)}",
            f"contexts={','.join(map(str, contexts))}",
            f"output_tokens={args.output_tokens}",
            f"repeats={args.repeats}",
            f"gpu_layers={','.join(map(str, args.gpu_layers))}",
            f"backends={','.join(backend for backend, *_ in runtimes)}",
            *[
                f"runtime_{backend.lower()}={path}; devices={','.join(devices)}; "
                f"gpu_indices={','.join(map(str, gpu_indices))}; split_mode={split_mode}"
                for backend, path, devices, gpu_indices, split_mode in runtimes
            ],
            "purpose=architecture-optimization; excluded from normal model comparison",
        ])
        + "\n",
        encoding="utf-8",
    )

    rows: list[dict[str, object]] = []
    results_path = run_directory / "results.csv"
    results_path.touch()
    completed_tests = 0
    for backend, runtime, devices, gpu_indices, split_mode in available_runtimes:
        version = subprocess.run(
            [str(runtime), "--version"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
        ).stdout.strip()
        backend_directory = run_directory / backend
        backend_directory.mkdir()

        for model in models:
            model_path = resolve_path(Path(model["path"]))
            if not model_path.exists():
                raise FileNotFoundError(f"Model does not exist: {model_path}")
            model_name = model_path.stem
            for context in contexts:
                for layers in args.gpu_layers:
                    for repeat in range(1, args.repeats + 1):
                        stem = f"{model_name}-c{context}-ngl{layers}-r{repeat}"
                        log_path = backend_directory / f"{stem}.log"
                        arguments = [
                            "-m",
                            str(model_path),
                            "-ngl",
                            str(layers),
                            "--device",
                            ",".join(devices),
                            "--split-mode",
                            split_mode,
                            "--main-gpu",
                            "0",
                            "--load-mode",
                            "mmap",
                            "-c",
                            str(context),
                            "-n",
                            str(args.output_tokens),
                            "--temp",
                            "0",
                            "--top-p",
                            "0.95",
                            "--seed",
                            "42",
                            "--reasoning",
                            "off",
                            "--reasoning-budget",
                            "0",
                            "--single-turn",
                            "--simple-io",
                            "--color",
                            "off",
                            "-p",
                            PROMPT,
                        ]
                        start = datetime.now(timezone.utc)
                        (
                            exit_code,
                            output,
                            gpu_name,
                            peak_utilization,
                            peak_memory,
                            memory_stats,
                        ) = run_command(runtime, arguments, log_path, gpu_indices)
                        duration = (datetime.now(timezone.utc) - start).total_seconds()
                        generation = GENERATION_RE.search(output)
                        prompt_rate = PROMPT_RE.search(output)
                        generation_rate = (
                            float(generation.group(1)) if generation else None
                        )
                        status = (
                            "pass"
                            if exit_code == 0
                            and generation_rate
                            and generation_rate > 0
                            else "fail"
                        )
                        rows.append({
                            "run_id": run_id,
                            "backend": backend,
                            "runtime": version,
                            "gpu_index": ",".join(map(str, gpu_indices)),
                            "gpu_name": gpu_name,
                            "model": str(model_path),
                            "gpu_layers": layers,
                            "repeat": repeat,
                            "context": context,
                            "output_tokens": args.output_tokens,
                            "status": status,
                            "exit_code": exit_code,
                            "duration_seconds": round(duration, 3),
                            **memory_stats,
                            "peak_gpu_utilization_percent": peak_utilization,
                            "peak_vram_mib": peak_memory,
                            "generation_tokens_per_second": generation_rate,
                            "prompt_tokens_per_second": (
                                float(prompt_rate.group(1)) if prompt_rate else None
                            ),
                            "log": str(log_path),
                        })
                        append_result(results_path, rows[-1])
                        write_matrix_report(
                            run_directory / "matrix.md", rows, args.repeats
                        )
                        completed_tests += 1
                        print(
                            f"Test {completed_tests} of {total_tests}: "
                            f"{model['id']} {backend} context {context} "
                            f"-ngl {layers} repeat {repeat} -> {status}",
                            flush=True,
                        )

    write_matrix_report(run_directory / "matrix.md", rows, args.repeats)
    print(f"Architecture benchmark complete: {run_directory}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
