"""Tests for the computed-window launcher (no GPU, no Strata)."""
import json
from pathlib import Path

import pytest

import strata_fit_launch as fl

REPO = Path(__file__).resolve().parents[1]
TABLE = json.loads((REPO / "configs" / "vram-model.json").read_text(encoding="utf-8"))["models"]
CFG = {"model_name": "qwen3.8-flash-next-iq2_xs", "args": ["--vram-reserve-mib", "1024", "--kv", "q4_0", "--mtp", "x"]}
MODEL = TABLE["qwen3.8-flash-next-iq2_xs"]


def window(total, used, minimum=32768, maximum=262144):
    return fl.compute(CFG, MODEL, total, used, 150, maximum, minimum)["window"]


def test_window_grows_with_the_card_and_shrinks_with_the_desktop():
    small, bigger_card, busier_desktop = window(8192, 500), window(12288, 500), window(8192, 900)
    assert bigger_card > small > busier_desktop
    assert bigger_card == 262144                      # a 12 GB card reaches the model's maximum
    assert small % fl.STEP == 0


def test_below_the_minimum_the_window_is_under_it_and_the_shortfall_is_reported():
    r = fl.compute(CFG, MODEL, 8192, 1500, 150, 262144, 32768)
    assert r["window"] < 32768 and r["short_mib_for_min_window"] > 0


def test_maximum_is_respected():
    assert window(24576, 500, maximum=65536) == 65536


def test_confirm_accepts_declines_and_takes_a_smaller_number():
    assert fl.confirm_window(98304, 32768, True) == 98304                         # --always-start: no question
    assert fl.confirm_window(98304, 32768, False, ask=lambda _: "", interactive=True) == 98304
    assert fl.confirm_window(98304, 32768, False, ask=lambda _: "y", interactive=True) == 98304
    assert fl.confirm_window(98304, 32768, False, ask=lambda _: "n", interactive=True) is None
    assert fl.confirm_window(98304, 32768, False, ask=lambda _: "48k", interactive=True) == 49152
    answers = iter(["99999", "1000", "40000"])                                       # too big, too small, then fine (rounded down to the step)
    assert fl.confirm_window(98304, 32768, False, ask=lambda _: next(answers), interactive=True) == 36864


def test_no_console_means_no_start_unless_always():
    assert fl.confirm_window(98304, 32768, False, interactive=False) is None
    assert fl.confirm_window(98304, 32768, True, interactive=False) == 98304


def test_kv_grow_mode_only_needs_the_minimum_window_kv_and_is_capped_at_the_verified_window():
    cfg = json.loads((REPO / "configs" / "strata-coder-iq1_m.json").read_text(encoding="utf-8-sig"))
    model = json.loads((REPO / "configs" / "vram-model.json").read_text(encoding="utf-8"))["models"][cfg["model_name"]]
    reserved = fl.compute(cfg, model, 8192, 700, 150, 262144, 32768)
    grown = fl.compute(cfg, model, 8192, 700, 150, 262144, 32768, kv_grow=True)
    assert grown["window"] == int(model.get("verified_max_window", 131072))
    assert reserved["window"] < grown["window"]


def test_write_config_keeps_kv_grow_only_when_asked():
    cfg = json.loads((REPO / "configs" / "strata-coder-iq1_m.json").read_text(encoding="utf-8-sig"))
    on = json.loads(fl.write_config(cfg, 65536, 8081, False, True).read_text(encoding="utf-8"))["args"]
    off = json.loads(fl.write_config(cfg, 65536, 8081, False, False).read_text(encoding="utf-8"))["args"]
    assert "--kv-grow" in on and "--kv-grow" not in off
