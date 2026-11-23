"""Run the Enita evals with the real LLM. The exit code is 0 only if all gates pass.

    uv run python -m evals.run            # all evals
    uv run python -m evals.run review     # only the review eval

Gates:
- review: the decision (rules check + verifier + option check) is correct in >= 10 of 11 cases.
- trajectory: 3 of 3 generations are approved, the writer calls get_theory_card first and
  then get_learner_profile, and each generation is in the time budget.
- rag: 4 real "Spiegami meglio" explanations, no errors, mean RAGAS faithfulness and context
  precision above the gates.
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

from enita.agent.formats import prepare
from enita.agent.pipeline import DecisionNode, VerifierNode, generate_exercise, rule_issues
from enita.audit import summarize_spans
from enita.content.loader import ContentRepository
from enita.practice.service import default_agents, mcp_tools
from enita.settings import get_settings
from evals.cases import RAG_TOPICS, REVIEW_CASES, TRAJECTORY_TOPICS

RAG_MIN_FAITHFULNESS = 0.85  # measured 0.954 (2026-11-23)
RAG_MIN_CONTEXT_PRECISION = 0.70  # measured 0.819 (2026-11-23)
REVIEW_MIN_PASS = 10  # of 11 cases: one known edge case may change between runs
TIME_BUDGET_S = 30.0
REPORT = Path(__file__).parent / "last_report.json"


async def review_eval() -> dict[str, Any]:
    settings = get_settings()
    content = ContentRepository(settings.content_dir)
    _, verifier = default_agents(settings)([])
    results = []
    for case in REVIEW_CASES:
        card = content.get(case.topic_id).as_markdown()
        draft = prepare(case.draft)
        rules = rule_issues(draft, draft.type)
        verification = await VerifierNode(verifier).a_run(draft=draft, card=card)
        decision = DecisionNode().run(draft=draft, rule_issues=rules, verification=verification)
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


async def rag_eval() -> dict[str, Any]:
    """RAGAS on "Spiegami meglio": faithfulness and context precision of real explanations."""
    import warnings

    from langchain_openai import ChatOpenAI
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.llms import LangchainLLMWrapper

    from enita.practice.explain import ExplainService
    from enita.rag.index import build_passages
    from enita.storage.db import Database

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithoutReference

    base = get_settings()
    eval_db = base.db_path.parent / "eval.db"  # same folder: the embedding cache is shared
    eval_db.unlink(missing_ok=True)
    settings = base.model_copy(update={"db_path": eval_db})
    content = ContentRepository(settings.content_dir)
    passages = {p.rule_ref: p.text for p in build_passages(content)}
    service = ExplainService(settings, content, Database(eval_db))

    samples, cases = [], []
    for topic_id in RAG_TOPICS:
        error = None
        try:
            out = await service.explain(topic_id)
        except Exception as exc:  # noqa: BLE001 - the eval records every failure
            error = f"{type(exc).__name__}: {exc}"[:300]
        record = service.db.list_audit(1)[0]["data"]
        retrieved = record.get("retrieved", [])
        cases.append(
            {
                "topic_id": topic_id,
                "retrieved": retrieved,
                "error": error,
                "sources": [s.rule_ref for s in out.sources] if not error else [],
            }
        )
        if not error:
            samples.append(
                SingleTurnSample(
                    user_input=f"Spiegami meglio: {content.get(topic_id).title}",
                    response=out.explanation,
                    retrieved_contexts=[passages[r] for r in retrieved if r in passages],
                )
            )
    eval_db.unlink(missing_ok=True)

    scores: dict[str, float] = {}
    if samples:
        llm = LangchainLLMWrapper(
            ChatOpenAI(model=settings.model, api_key=settings.openai_api_key.get_secret_value())
        )
        result = evaluate(
            EvaluationDataset(samples=samples),
            metrics=[Faithfulness(), LLMContextPrecisionWithoutReference()],
            llm=llm,
            show_progress=False,
        )
        df = result.to_pandas()
        for name in ("faithfulness", "llm_context_precision_without_reference"):
            scores[name] = round(float(df[name].mean()), 3)
        for case, (_, row) in zip([c for c in cases if not c["error"]], df.iterrows(), strict=True):
            case["faithfulness"] = round(float(row["faithfulness"]), 3)
            case["context_precision"] = round(
                float(row["llm_context_precision_without_reference"]), 3
            )

    faith = scores.get("faithfulness", 0.0)
    precision = scores.get("llm_context_precision_without_reference", 0.0)
    passed = (
        all(not c["error"] for c in cases)
        and faith >= RAG_MIN_FAITHFULNESS
        and precision >= RAG_MIN_CONTEXT_PRECISION
    )
    for c in cases:
        c["passed"] = not c["error"]
    return {
        "name": "rag",
        "score": f"faithfulness {faith}, context precision {precision}",
        "gate": f"faithfulness >= {RAG_MIN_FAITHFULNESS}, "
        f"context precision >= {RAG_MIN_CONTEXT_PRECISION}, no errors",
        "passed": passed,
        "cases": cases,
    }


def _print(report: dict[str, Any]) -> None:
    for ev in report["evals"]:
        mark = "PASS" if ev["passed"] else "FAIL"
        print(f"\n[{mark}] {ev['name']}: {ev['score']} (gate {ev['gate']})")
        for c in ev["cases"]:
            ok = "ok  " if c["passed"] else "FAIL"
            if ev["name"] == "rag":
                print(
                    f"  {ok} {c['topic_id']}: faithfulness {c.get('faithfulness')}, "
                    f"context precision {c.get('context_precision')}, "
                    f"sources {c['sources']}" + (f", error {c['error']}" if c["error"] else "")
                )
            elif ev["name"] == "review":
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
    runners = {"review": review_eval, "trajectory": trajectory_eval, "rag": rag_eval}
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
