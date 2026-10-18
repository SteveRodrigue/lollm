#!/usr/bin/env python3
"""Write configs/strata-iq3_xxs.json: the IQ2_XS best-flags config with the IQ3_XXS pack, shards and expert profile that Strata's
setup generated (runtimes/strata/strata-iq3_xxs.json), converted to repository-relative paths."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
gen = json.loads((REPO / "runtimes" / "strata" / "strata-iq3_xxs.json").read_text(encoding="utf-8-sig"))
base = json.loads((REPO / "configs" / "strata-iq2_xs.json").read_text(encoding="utf-8"))


def rel(p: str) -> str:
    q = Path(p)
    try:
        return q.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return p


def arg(args, flag):
    return args[args.index(flag) + 1]


a = base["args"]
for flag in ("--pack", "--native", "--ple-gguf", "--expert-profile"):
    a[a.index(flag) + 1] = rel(arg(gen["args"], flag))
base["tokenizer"] = rel(gen["tokenizer"])
base["model_name"] = gen["model_name"]
base["log"] = "logs/strata-iq3_xxs.log"
(REPO / "configs" / "strata-iq3_xxs.json").write_text(json.dumps(base, indent=1), encoding="utf-8")
print("wrote configs/strata-iq3_xxs.json for", base["model_name"])
