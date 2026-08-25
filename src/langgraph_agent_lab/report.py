"""Report generation helper."""

from __future__ import annotations

from pathlib import Path

from .metrics import MetricsReport


def render_report(metrics: MetricsReport) -> str:
    """Render a complete lab report from metrics data.

    The report is deliberately generated from the typed metrics object rather
    than from JSON or a hand-maintained scenario list, so it remains useful
    when additional scenarios are added.
    """

    def cell(value: object) -> str:
        """Keep values safe to place in a markdown table cell."""
        return str(value).replace("|", "\\|").replace("\n", " ")

    success_rate = f"{metrics.success_rate:.1%}"
    rows = [
        "| Scenario | Expected route | Actual route | Success | Retries | Interrupts |",
        "|---|---|---|---:|---:|---:|",
    ]
    for item in metrics.scenario_metrics:
        rows.append(
            "| "
            + " | ".join(
                (
                    cell(item.scenario_id),
                    cell(item.expected_route),
                    cell(item.actual_route or "—"),
                    "Yes" if item.success else "No",
                    cell(item.retry_count),
                    cell(item.interrupt_count),
                )
            )
            + " |"
        )

    return "\n".join(
        (
            "# Day 08 Lab Report",
            "",
            "## 1. Team / student",
            "",
            "- Name:",
            "- Repo/commit:",
            "- Date:",
            "",
            "## 2. Architecture",
            "",
            "The graph classifies each request, dispatches it to the appropriate "
            "route, executes the route, and finishes at a single `finalize` node. "
            "Transient tool failures return through a bounded retry edge; risky "
            "actions pause at the approval node and resume using the same thread.",
            "",
            "## 3. State schema",
            "",
            "State carries the request, route, messages/events, errors, retry "
            "attempt, approval, and final answer. Conversation/events and errors "
            "are append-only; route, retry state, approval, and final answer are "
            "overwritten with their current values.",
            "",
            "| Field | Reducer | Why |",
            "|---|---|---|",
            "| messages/events | append | Preserve an audit trail |",
            "| errors | append | Retain failure context |",
            "| route | overwrite | Store the current route |",
            "| retry/approval/final_answer | overwrite | Track current execution state |",
            "",
            "## 4. Scenario results",
            "",
            "### Metrics summary",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Total scenarios | {metrics.total_scenarios} |",
            f"| Success rate | {success_rate} |",
            f"| Average nodes visited | {metrics.avg_nodes_visited:.2f} |",
            f"| Total retries | {metrics.total_retries} |",
            f"| Total interrupts | {metrics.total_interrupts} |",
            f"| Resume success | {'Yes' if metrics.resume_success else 'No'} |",
            "",
            "### Scenario results",
            "",
            *rows,
            "",
            "## 5. Failure analysis",
            "",
            "1. Retry or tool failure: transient errors are recorded and routed "
            "through a bounded retry loop; exhausted attempts terminate with an "
            "actionable error instead of looping forever.",
            "2. Risky action without approval: the graph interrupts before the "
            "action, persists pending state, and only resumes after an explicit "
            "approval value is supplied.",
            "",
            "## 6. Persistence / recovery evidence",
            "",
            "A checkpointer keyed by thread id preserves state and event history "
            "across the approval pause, allowing the run to resume without "
            "repeating completed nodes.",
            "",
            "## 7. Extension work",
            "",
            "Metrics are serialized to JSON and the report is rendered as portable "
            "Markdown for review or archival.",
            "",
            "## 8. Improvement plan",
            "",
            "Productionize first by adding durable SQLite/Postgres checkpointing, "
            "structured tracing and latency/error alerts, then expand route and "
            "recovery tests with adversarial inputs.",
            "",
        )
    )


def write_report(metrics: MetricsReport, output_path: str | Path) -> None:
    """Write the rendered report to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(metrics), encoding="utf-8")
