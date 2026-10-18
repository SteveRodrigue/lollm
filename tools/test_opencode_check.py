import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import opencode_check as oc  # noqa: E402

BASE = "http://127.0.0.1:8080/v1"
USER = {"model": "strata/old", "providers": {"strata": {"name": "x", "package": "pkg", "settings": {"baseURL": BASE, "apiKey": "secret-key", "timeout": 5},
                                                        "models": {"old": {"limit": {"context": 131072, "output": 8192}}}}}, "skills": ["a"]}


def test_window_from_metrics_json_and_text():
    assert oc.window_from_metrics('{"engine": {"max_context": 98304}}') == 98304
    assert oc.window_from_metrics("strata_engine_max_context 65536\n") == 65536
    assert oc.window_from_metrics("garbage") is None


def test_recommended_limits():
    assert oc.recommended_limits(131072) == (32768, 36864)
    out, res = oc.recommended_limits(65536)
    assert out == 21504 and res == 25600
    assert oc.recommended_limits(65536, 8000, 9000) == (8000, 9000)


def test_audit_reports_stale_model_small_output_and_missing_compaction():
    f = oc.audit(USER, "m", 98304, BASE, 32768, 36864)
    text = " ".join(t for _, t in f)
    assert "model 'm' is not defined" in text and "other model ids" in text
    assert any(s == "FIX" and "compaction.reserved" in t for s, t in f)


def test_update_keeps_other_keys_and_the_users_package_and_key_and_passes_audit():
    new = oc.apply_fixes(USER, "m", 98304, BASE, 32768, 36864)
    assert new["skills"] == ["a"] and set(new["providers"]) == {"strata"} and "provider" not in new
    p = new["providers"]["strata"]
    assert p["package"] == "pkg" and p["settings"]["apiKey"] == "secret-key" and p["settings"]["timeout"] == 5
    assert p["models"]["m"]["limit"] == {"context": 98304, "output": 32768}
    assert p["models"]["m"]["capabilities"]["reasoning"]["supported"] is True
    assert new["model"] == "strata/m" and new["compaction"]["reserved"] == 36864
    assert all(s != "FIX" for s, _ in oc.audit(new, "m", 98304, BASE, 32768, 36864))


def test_deprecated_singular_provider_block_is_warned_about_and_left_alone():
    cfg = {"provider": {"strata": {"npm": "x"}}}
    assert any(s == "WARN" and "deprecated" in t for s, t in oc.audit(cfg, "m", 98304, BASE, 32768, 36864))
    assert oc.apply_fixes(cfg, "m", 98304, BASE, 32768, 36864)["provider"] == {"strata": {"npm": "x"}}


def test_context_larger_than_the_window_is_a_fix_and_a_bigger_user_output_is_kept():
    cfg = oc.apply_fixes({}, "m", 131072, BASE, 32768, 36864)
    lim = cfg["providers"]["strata"]["models"]["m"]["limit"]
    lim.update(context=200000, output=40000)
    f = oc.audit(cfg, "m", 131072, BASE, 32768, 36864)
    assert any(s == "FIX" and "MORE than the window" in t for s, t in f)
    again = oc.apply_fixes(cfg, "m", 131072, BASE, 32768, 36864)
    assert again["providers"]["strata"]["models"]["m"]["limit"] == {"context": 131072, "output": 40000}
    json.dumps(again)


def test_update_is_idempotent_when_the_window_changes_between_launches():
    cfg = {}
    for w in (98304, 65536, 98304, 131072):
        out, res = oc.recommended_limits(w)
        cfg = oc.apply_fixes(cfg, "m", w, BASE, out, res)
        assert all(s != "FIX" for s, _ in oc.audit(cfg, "m", w, BASE, out, res)), w
        lim = cfg["providers"]["strata"]["models"]["m"]["limit"]
        assert lim["output"] <= w // 2 and cfg["compaction"]["reserved"] <= w // 2 + 4096


def test_thinking_is_optional_set_and_removed_again_without_touching_other_body_keys():
    cfg = oc.apply_fixes({}, "m", 98304, BASE, 32768, 36864)
    assert "body" not in cfg["providers"]["strata"]["models"]["m"]
    low = oc.apply_fixes(cfg, "m", 98304, BASE, 32768, 36864, "low")
    assert low["providers"]["strata"]["models"]["m"]["body"] == {"reasoning_effort": "low"}
    assert all(s != "FIX" for s, _ in oc.audit(low, "m", 98304, BASE, 32768, 36864, "low"))
    assert any(s == "FIX" for s, _ in oc.audit(low, "m", 98304, BASE, 32768, 36864, "default"))
    low["providers"]["strata"]["models"]["m"]["body"]["top_k"] = 20
    back = oc.apply_fixes(low, "m", 98304, BASE, 32768, 36864, "default")
    assert back["providers"]["strata"]["models"]["m"]["body"] == {"top_k": 20}
    off = oc.apply_fixes(cfg, "m", 98304, BASE, 32768, 36864, "off")
    assert off["providers"]["strata"]["models"]["m"]["body"] == {"reasoning_effort": "none"}


def test_a_reasoning_effort_the_user_chose_is_left_alone_by_default():
    cfg = oc.apply_fixes({}, "m", 98304, BASE, 32768, 36864)
    cfg["providers"]["strata"]["models"]["m"]["body"] = {"reasoning_effort": "medium"}
    assert any(s == "WARN" and "set by you" in t for s, t in oc.audit(cfg, "m", 98304, BASE, 32768, 36864))
    assert oc.apply_fixes(cfg, "m", 98304, BASE, 32768, 36864)["providers"]["strata"]["models"]["m"]["body"] == {"reasoning_effort": "medium"}
