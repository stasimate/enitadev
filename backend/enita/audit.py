"""Convert ContextTracing spans into a compact audit record (RNF-04)."""

from typing import Any


def _seconds(span: Any) -> float | None:
    if span.end_time and span.start_time:
        return round((span.end_time - span.start_time) / 1e9, 3)
    return None


def summarize_spans(spans: list[Any]) -> dict[str, Any]:
    """Keep the agents, the tool calls and the LLM calls with model and tokens.

    Tool results are not stored: they are large and the content is in the repository.
    """
    steps: list[dict[str, Any]] = []
    tokens = {"prompt": 0, "completion": 0}
    for span in sorted(spans, key=lambda s: s.start_time or 0):
        attrs = dict(span.attributes or {})
        kind = attrs.get("type")
        if kind not in ("agent", "tool", "generation"):
            continue
        step: dict[str, Any] = {"name": span.name, "type": kind, "seconds": _seconds(span)}
        if kind == "tool":
            step["arguments"] = str(attrs.get("tool_arguments", ""))[:200]
        if kind == "generation":
            step["model"] = attrs.get("model_name")
            step["prompt_tokens"] = int(attrs.get("prompt_tokens_used", 0) or 0)
            step["completion_tokens"] = int(attrs.get("completion_tokens_used", 0) or 0)
            tokens["prompt"] += step["prompt_tokens"]
            tokens["completion"] += step["completion_tokens"]
        steps.append(step)
    return {"steps": steps, "tokens": tokens}
