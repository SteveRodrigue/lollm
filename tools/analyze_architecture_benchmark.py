"""Analyze architecture benchmark CSVs and propose runtime profiles."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALL_LAYERS_SENTINEL = 99


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Propose context and GPU-layer profiles from architecture benchmark results."
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=ROOT / "logs" / "architecture-optimization",
        help="Directory containing architecture benchmark run directories.",
    )
    parser.add_argument(
        "--models-config",
        type=Path,
        default=ROOT / "configs" / "models.yaml",
    )
    parser.add_argument(
        "--minimum-context",
        type=int,
        default=32768,
        help="Minimum context for the throughput recommendation.",
    )
    parser.add_argument(
        "--target-context",
        type=int,
        default=262144,
        help="Preferred maximum context when a stable result exists.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional Markdown output path; stdout is used by default.",
    )
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_config(path: Path) -> dict[str, Any]:
    with resolve_path(path).open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"Expected a YAML mapping: {path}")
    return value


def expected_repeats(config: dict[str, Any]) -> int:
    defaults = config.get("architecture_defaults", {})
    if not isinstance(defaults, dict):
        return 2
    return int(defaults.get("repeats", 2))


def read_rows(results_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(resolve_path(results_root).rglob("results.csv")):
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                try:
                    row["context"] = int(row["context"])
                    row["gpu_layers"] = int(row["gpu_layers"])
                    row["repeat"] = int(row["repeat"])
                    row["generation_tokens_per_second"] = float(
                        row["generation_tokens_per_second"]
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                row["source"] = str(path)
                rows.append(row)
    return rows


def newest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the newest run for each backend/model matrix identity."""
    by_matrix: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row["backend"]), str(row["model"]), str(row["run_id"]))
        by_matrix[key].append(row)
    latest_by_backend_model: dict[
        tuple[str, str], tuple[str, list[dict[str, Any]]]
    ] = {}
    for (backend, model, run_id), matrix_rows in by_matrix.items():
        key = (backend, model)
        previous = latest_by_backend_model.get(key)
        if previous is None or run_id > previous[0]:
            latest_by_backend_model[key] = (run_id, matrix_rows)
    return [
        row
        for _, matrix_rows in latest_by_backend_model.values()
        for row in matrix_rows
    ]


def eligible_cells(
    rows: list[dict[str, Any]], repeats: int
) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    grouped: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            str(row["backend"]),
            str(row["model"]),
            int(row["context"]),
            int(row["gpu_layers"]),
        )
        grouped[key].append(row)
    cells: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for key, values in grouped.items():
        if len(values) < repeats or not all(
            row.get("status") == "pass" for row in values
        ):
            continue
        speeds = [float(row["generation_tokens_per_second"]) for row in values]
        cells[key] = {
            "backend": key[0],
            "model": key[1],
            "context": key[2],
            "gpu_layers": key[3],
            "speed": mean(speeds),
            "repeats": len(values),
            "source": values[-1].get("source"),
        }
    return cells


def yaml_quote(value: str) -> str:
    return yaml.safe_dump(value, default_flow_style=True).strip()


def profile_snippet(cell: dict[str, Any], name: str) -> str:
    model_name = Path(cell["model"]).stem
    runtime_id = str(cell["backend"]).lower()
    return "\n".join([
        f"  {name}:",
        f"    model: {yaml_quote(model_name)}",
        f"    runtime: {runtime_id}",
        "    purpose: Architecture benchmark proposal; validate before promotion.",
        "    parameters:",
        f"      gpu_layers: {cell['gpu_layers']}",
        f"      context: {cell['context']}",
        "      load_mode: mmap",
        f"    evidence: {yaml_quote(str(cell['source']))}"
        if cell.get("source")
        else "",
    ]).rstrip()


def format_context(context: int) -> str:
    return f"{context // 1024}K" if context % 1024 == 0 else str(context)


def render(
    cells: dict[tuple[str, str, int, int], dict[str, Any]],
    minimum_context: int,
    target_context: int,
) -> str:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for cell in cells.values():
        groups[(cell["backend"], cell["model"])].append(cell)
    lines = [
        "# Architecture Profile Proposals",
        "",
        f"Only complete passing cells are considered. `-ngl {ALL_LAYERS_SENTINEL}` is retained as comparison evidence but is never proposed as a profile. Throughput recommendation context floor: `{format_context(minimum_context)}`.",
        "",
    ]
    snippets: list[str] = []
    for backend, model in sorted(groups):
        options = [
            cell
            for cell in groups[(backend, model)]
            if cell["gpu_layers"] != ALL_LAYERS_SENTINEL
        ]
        if not options:
            lines.extend([
                f"## {backend}: {Path(model).stem}",
                "",
                f"No fixed-layer proposals available; only `-ngl {ALL_LAYERS_SENTINEL}` completed.",
                "",
            ])
            continue
        max_context = max(cell["context"] for cell in options)
        max_context_options = [
            cell for cell in options if cell["context"] == max_context
        ]
        context_choice = max(max_context_options, key=lambda cell: cell["speed"])
        throughput_options = [
            cell for cell in options if cell["context"] >= minimum_context
        ]
        if not throughput_options:
            throughput_options = options
        throughput_choice = max(throughput_options, key=lambda cell: cell["speed"])
        lines.extend([
            f"## {backend}: {Path(model).stem}",
            "",
            f"Context window: {format_context(max_context)} > `-ngl {context_choice['gpu_layers']}` ({context_choice['speed']:.1f} t/s)",
            f"Max token/sec: {throughput_choice['speed']:.1f} t/s at {format_context(throughput_choice['context'])} > `-ngl {throughput_choice['gpu_layers']}`",
            f"Target context available: {'yes' if max_context >= target_context else 'no'}",
            "",
        ])
        safe_model = Path(model).stem.lower().replace(".", "-").replace("_", "-")
        snippets.append(
            profile_snippet(
                context_choice, f"architecture-{backend.lower()}-{safe_model}-context"
            )
        )
        snippets.append(
            profile_snippet(
                throughput_choice,
                f"architecture-{backend.lower()}-{safe_model}-throughput",
            )
        )
    lines.extend(["## Proposed `configs/models.yaml` profiles", "", "```yaml"])
    lines.extend(snippets or ["  # No complete passing cells found."])
    lines.extend([
        "```",
        "",
        "Validate these proposals with the real coding test before promotion.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if args.minimum_context < 1 or args.target_context < 1:
        raise ValueError("Context thresholds must be positive")
    config = load_config(args.models_config)
    rows = newest_rows(read_rows(args.results_root))
    cells = eligible_cells(rows, expected_repeats(config))
    report = render(cells, args.minimum_context, args.target_context)
    if args.output:
        resolve_path(args.output).write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
