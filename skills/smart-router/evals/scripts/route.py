#!/usr/bin/env python3
"""
Routing decision validator for smart-router.

Given an analyzer JSON (scores + overall) and the eval suite, computes which
tier the routing logic should pick and compares to the expected_routing block.

Usage:
    # interactive: read analyzer JSON from stdin, evaluate against eval id 1
    python evals/scripts/route.py --eval 1 < analyzer_output.json

    # compute tier from raw scores (skip analyzer)
    python evals/scripts/route.py --scores '{"reasoning":4,"code":1,"creativity":4,"context_size":3,"domain_expertise":4,"ambiguity":2}'

    # run a self-check on the embedded golden expectations
    python evals/scripts/route.py --selfcheck
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DIMENSIONS = (
    "reasoning",
    "code",
    "creativity",
    "context_size",
    "domain_expertise",
    "ambiguity",
)


def extract_json(blob: str) -> dict[str, Any]:
    """Robust JSON extraction: tolerate prose, ```json fences, etc."""
    blob = blob.strip()
    if not blob:
        raise ValueError("empty input")
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    # find first '{' and last matching '}'
    start = blob.find("{")
    end = blob.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("no JSON object found in input")
    candidate = blob[start : end + 1]
    return json.loads(candidate)


def compute_overall(scores: dict[str, int]) -> float:
    values = [int(scores[d]) for d in DIMENSIONS]
    s = sum(values)
    sorted_desc = sorted(values, reverse=True)
    top, second = sorted_desc[0], sorted_desc[1]
    return (s + 0.5 * top + 0.5 * second) / 7.0


def select_tier(scores: dict[str, int], overall: float) -> tuple[str, list[str]]:
    """Return (tier, list_of_rules_triggered)."""
    rules: list[str] = []
    code = scores["code"]
    ctx = scores["context_size"]
    high_dims = sum(1 for v in scores.values() if v >= 4)

    # Rule A: code override (global)
    if code >= 4:
        rules.append("code-override")
        if overall >= 3.5:
            return ("code-heavy", rules)
        return ("code-mid", rules)

    # Rule B: multi-peak override
    if high_dims >= 3:
        rules.append("multi-peak")
        if overall >= 4.0:
            return ("frontier", rules)
        return ("heavy", rules)

    # Rule D: base table
    if overall < 1.8:
        tier = "cheap"
    elif overall < 3.0:
        tier = "balanced"
    elif overall < 4.2:
        tier = "heavy"
    else:
        tier = "frontier"

    # Rule C: context-size guard (post-base, escalates cheap → balanced)
    if ctx == 5 and tier == "cheap":
        rules.append("context-guard")
        tier = "balanced"

    return (tier, rules)


def load_evals(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_against_eval(eval_entry: dict[str, Any], tier: str, overall: float, rules: list[str]) -> tuple[bool, list[str]]:
    expected = eval_entry.get("expected_routing", {})
    failures: list[str] = []

    if "tier" in expected and tier != expected["tier"]:
        failures.append(f"tier mismatch: got {tier!r}, expected {expected['tier']!r}")
    if "tier_one_of" in expected and tier not in expected["tier_one_of"]:
        failures.append(f"tier mismatch: got {tier!r}, expected one of {expected['tier_one_of']!r}")

    if "overall_range" in expected:
        lo, hi = expected["overall_range"]
        if not (lo <= overall <= hi):
            failures.append(f"overall {overall:.2f} outside expected range [{lo}, {hi}]")

    must = set(expected.get("must_trigger_rules", []))
    must_not = set(expected.get("must_not_trigger_rules", []))
    triggered = set(rules)
    missing = must - triggered
    forbidden = triggered & must_not
    if missing:
        failures.append(f"missing required rules: {sorted(missing)}")
    if forbidden:
        failures.append(f"forbidden rules triggered: {sorted(forbidden)}")

    return (not failures, failures)


def selfcheck() -> int:
    """Verify the routing table against documented golden cases from SKILL.md."""
    cases = [
        # (name, scores, expected_tier, expected_rules)
        ("multiply",           {"reasoning":1,"code":1,"creativity":1,"context_size":1,"domain_expertise":1,"ambiguity":1}, "cheap",      []),
        ("csv-to-json",        {"reasoning":1,"code":1,"creativity":1,"context_size":1,"domain_expertise":1,"ambiguity":1}, "cheap",      []),
        ("async-refactor",     {"reasoning":3,"code":4,"creativity":2,"context_size":1,"domain_expertise":3,"ambiguity":2}, "code-mid",   ["code-override"]),
        ("ethics-essay",       {"reasoning":4,"code":1,"creativity":4,"context_size":3,"domain_expertise":4,"ambiguity":2}, "heavy",      ["multi-peak"]),
        ("distributed-cache",  {"reasoning":5,"code":5,"creativity":3,"context_size":3,"domain_expertise":4,"ambiguity":3}, "code-heavy", ["code-override"]),
        ("borges-story",       {"reasoning":4,"code":1,"creativity":5,"context_size":4,"domain_expertise":3,"ambiguity":3}, "heavy",      ["multi-peak"]),
        # context_size==5 must never resolve to 'cheap'. The weighted formula already
        # guarantees overall>=1.857 (=> balanced) here, so 'context-guard' stays dormant.
        ("huge-ctx-trivial",   {"reasoning":1,"code":1,"creativity":1,"context_size":5,"domain_expertise":1,"ambiguity":1}, "balanced",   []),
        # Base-table boundaries (semi-open intervals). overall = (sum + 0.5*max + 0.5*2nd)/7.
        ("base-cheap-top",     {"reasoning":2,"code":1,"creativity":1,"context_size":1,"domain_expertise":1,"ambiguity":1}, "cheap",      []),   # overall about 1.21
        ("base-balanced-low",  {"reasoning":2,"code":2,"creativity":2,"context_size":2,"domain_expertise":2,"ambiguity":2}, "balanced",   []),   # overall about 2.00
        ("base-heavy-low",     {"reasoning":3,"code":3,"creativity":3,"context_size":3,"domain_expertise":3,"ambiguity":3}, "heavy",      []),   # overall about 3.00
        ("multipeak-frontier", {"reasoning":5,"code":1,"creativity":5,"context_size":5,"domain_expertise":5,"ambiguity":3}, "frontier",   ["multi-peak"]),  # overall about 4.14
    ]
    ok = 0
    for name, scores, exp_tier, exp_rules in cases:
        overall = compute_overall(scores)
        tier, rules = select_tier(scores, overall)
        status = "OK" if (tier == exp_tier and set(exp_rules).issubset(set(rules))) else "FAIL"
        print(f"[{status}] {name:20s} overall={overall:.2f} tier={tier:12s} rules={rules} (expected tier={exp_tier}, rules⊇{exp_rules})")
        if status == "OK":
            ok += 1
    total = len(cases)
    print(f"\n{ok}/{total} selfcheck cases passed.")
    return 0 if ok == total else 1


def _load_scores(args: argparse.Namespace) -> tuple[dict[str, int], float | None]:
    """Return (scores, overall_provided_or_None) from CLI args.

    Accepts both the analyzer envelope ({"scores": {...}, "overall": ...}) and a
    flat scores object ({"reasoning": ..., ...}). Raises ValueError on bad input.
    """
    if args.scores:
        return json.loads(args.scores), None
    raw = Path(args.analyzer).read_text(encoding="utf-8") if args.analyzer else sys.stdin.read()
    parsed = extract_json(raw)
    scores = parsed.get("scores")
    if scores is None:
        # Tolerate a flat object that already contains the dimension keys.
        if all(d in parsed for d in DIMENSIONS):
            return parsed, None
        raise ValueError("analyzer JSON is missing the 'scores' object")
    return scores, parsed.get("overall")


def _validate_scores(scores: dict[str, Any]) -> str | None:
    """Return error message if invalid, else None."""
    for d in DIMENSIONS:
        v = scores.get(d)
        if not isinstance(v, int) or not (1 <= v <= 5):
            return f"invalid score for {d!r}: {v!r}"
    return None


def _build_parser(default_evals: Path) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Smart-router routing validator")
    p.add_argument("--eval", type=int, default=None, help="eval id to validate against")
    p.add_argument("--scores", type=str, default=None, help='inline JSON scores, e.g. \'{"reasoning":3,...}\'')
    p.add_argument("--analyzer", type=str, default=None, help="path to file containing analyzer JSON (default: stdin)")
    p.add_argument("--evals-path", type=Path, default=default_evals)
    p.add_argument("--selfcheck", action="store_true", help="run embedded golden checks and exit")
    return p


def _report_eval(args: argparse.Namespace, tier: str, overall: float, rules: list[str]) -> int:
    evals = load_evals(args.evals_path)
    entry = next((e for e in evals["evals"] if e["id"] == args.eval), None)
    if not entry:
        print(f"ERROR: no eval with id {args.eval}", file=sys.stderr)
        return 2
    ok, failures = validate_against_eval(entry, tier, overall, rules)
    print(f"\n--- eval #{args.eval}: {'PASS' if ok else 'FAIL'} ---")
    for f in failures:
        print(f"  - {f}")
    return 0 if ok else 1


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    args = _build_parser(here / "evals.json").parse_args()

    if args.selfcheck:
        return selfcheck()

    try:
        scores, overall_provided = _load_scores(args)
    except ValueError as exc:  # json.JSONDecodeError is a subclass of ValueError
        print(f"ERROR: could not parse analyzer output: {exc}", file=sys.stderr)
        return 2
    err = _validate_scores(scores)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 2

    overall = compute_overall(scores)
    if overall_provided is not None and abs(overall_provided - overall) > 0.05:
        print(f"[warn] analyzer overall {overall_provided:.3f} differs from recomputed {overall:.3f}", file=sys.stderr)

    tier, rules = select_tier(scores, overall)
    print(f"scores  : {scores}")
    print(f"overall : {overall:.3f}")
    print(f"rules   : {rules}")
    print(f"tier    : {tier}")

    if args.eval is not None:
        return _report_eval(args, tier, overall, rules)
    return 0


if __name__ == "__main__":
    sys.exit(main())
