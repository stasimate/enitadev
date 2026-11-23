"""Run the Enita evals with the real LLM. The exit code is 0 only if all gates pass.

    uv run python -m evals.run            # all evals
    uv run python -m evals.run review     # only the review eval

Gates:
- review: the decision (rules check + verifier + option check) is correct in >= 7 of 8 cases.
- trajectory: 3 of 3 generations are approved, the writer calls get_theory_card first and
  then get_learner_profile, and each generation is in the time budget.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from datapizza.tracing import ContextTracing

from enita.agent.pipeline import DecisionNode, VerifierNode, generate_exercise, rule_issues
from enita.audit import summarize_spans
from enita.content.loader import ContentRepository
from enita.practice.service import default_agents, mcp_tools
from enita.settings import get_settings
from evals.cases import REVIEW_CASES, TRAJECTORY_TOPICS

REVIEW_MIN_PASS = 7
TIME_BUDGET_S = 30.0
REPORT = Path(__file__).parent / "last_report.json"


async def review_eval() -> dict[str, Any]:
    settings = get_settings()
    content = ContentRepository(settings.content_dir)
    _, verifier = default_agents(settings)([])
    results = []
    for case in REVIEW_CASES:
        card = content.get(case.topic_id).as_markdown()
        rules = rule_issues(case.draft, case.draft.type)
        verification = await VerifierNode(verifier).a_run(draft=case.draft, card=card)
        decision = DecisionNode().run(
            draft=case.draft, rule_issues=rules, verification=verification
        )
        results.append(
            {
                "id": case.id,
                "edge": case.edge,
                "expected": case.expect_approved,
                "approved": decision.approved,
                "passed": decision.approved == case.expect_approved,
                "defect": case.defect,
                "issues": decision.issues,
                "correct_options": verification.correct_options,
            }
        )
    passed = sum(r["passed"] for r in results)
    return {
        "name": "review",
        "score": f"{passed}/{len(results)}",
        "gate": f">= {REVIEW_MIN_PASS}/{len(results)}",
        "passed": passed >= REVIEW_MIN_PASS,
        "cases": results,
    }


async def trajectory_eval() -> dict[str, Any]:
    settings = get_settings()
    content = ContentRepository(settings.content_dir)
    results = []
    for topic_id, kind in TRAJECTORY_TOPICS:
        start = time.perf_counter()
        error = None
        attempts = 0
        with ContextTracing().trace("eval.trajectory") as trace:
            try:
                async with mcp_tools(settings)() as tools:
                    writer, verifier = default_agents(settings)(tools)
                    result = await generate_exercise(
                        writer,
                        verifier,
                        topic_id=topic_id,
                        exercise_type=kind,
                        card=content.get(topic_id).as_markdown(),
                        max_attempts=settings.max_writer_attempts,
                    )
                    attempts = result.attempts
            except Exception as exc:  # noqa: BLE001 - the eval records every failure
                error = f"{type(exc).__name__}: {exc}"[:300]
            summary = summarize_spans(trace.get_spans())
        seconds = round(time.perf_counter() - start, 1)
        tools_used = [
            s["name"].removeprefix("Tool ") for s in summary["steps"] if s["type"] == "tool"
        ]
        checks = {
            "approved": error is None,
            "theory_card_first": bool(tools_used) and tools_used[0] == "get_theory_card",
            "profile_used": "get_learner_profile" in tools_used,
            "in_time_budget": seconds <= TIME_BUDGET_S,
        }
        results.append(
            {
                "topic_id": topic_id,
                "type": kind,
                "passed": all(checks.values()),
                "checks": checks,
                "tools": tools_used,
                "attempts": attempts,
                "seconds": seconds,
                "tokens": summary["tokens"],
                "error": error,
            }
        )
    passed = sum(r["passed"] for r in results)
    return {
        "name": "trajectory",
        "score": f"{passed}/{len(results)}",
        "gate": f"{len(results)}/{len(results)}",
        "passed": passed == len(results),
        "cases": results,
    }


def _print(report: dict[str, Any]) -> None:
    for ev in report["evals"]:
        mark = "PASS" if ev["passed"] else "FAIL"
        print(f"\n[{mark}] {ev['name']}: {ev['score']} (gate {ev['gate']})")
        for c in ev["cases"]:
            ok = "ok  " if c["passed"] else "FAIL"
            if ev["name"] == "review":
                edge = " (edge)" if c["edge"] else ""
                print(
                    f"  {ok} {c['id']}{edge}: expected approved={c['expected']}, "
                    f"got {c['approved']}"
                )
            else:
                failed = [k for k, v in c["checks"].items() if not v]
                print(
                    f"  {ok} {c['topic_id']} {c['type']}: {c['seconds']}s, "
                    f"attempts {c['attempts']}, tools {c['tools']}"
                    + (f", failed {failed}" if failed else "")
                )
    print(f"\nRESULT: {'PASS' if report['passed'] else 'FAIL'}  (report: {REPORT.name})")


async def main(selected: list[str]) -> int:
    logging.disable(logging.WARNING)
    settings = get_settings()
    runners = {"review": review_eval, "trajectory": trajectory_eval}
    names = selected or list(runners)
    evals = [await runners[n]() for n in names]
    report = {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": settings.provider,
        "model": settings.model,
        "writer_model": settings.writer_model or settings.model,
        "verifier_model": settings.verifier_model or settings.model,
        "passed": all(e["passed"] for e in evals),
        "evals": evals,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _print(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
