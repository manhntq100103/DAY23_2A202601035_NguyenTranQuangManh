# Day 08 Lab Report

## 1. Team / student

- Name:
- Repo/commit:
- Date:

## 2. Architecture

The graph classifies each request, dispatches it to the appropriate route, executes the route, and finishes at a single `finalize` node. Transient tool failures return through a bounded retry edge; risky actions pause at the approval node and resume using the same thread.

## 3. State schema

State carries the request, route, messages/events, errors, retry attempt, approval, and final answer. Conversation/events and errors are append-only; route, retry state, approval, and final answer are overwritten with their current values.

| Field | Reducer | Why |
|---|---|---|
| messages/events | append | Preserve an audit trail |
| errors | append | Retain failure context |
| route | overwrite | Store the current route |
| retry/approval/final_answer | overwrite | Track current execution state |

## 4. Scenario results

### Metrics summary

| Metric | Value |
|---|---:|
| Total scenarios | 7 |
| Success rate | 85.7% |
| Average nodes visited | 5.57 |
| Total retries | 1 |
| Total interrupts | 2 |
| Resume success | No |

### Scenario results

| Scenario | Expected route | Actual route | Success | Retries | Interrupts |
|---|---|---|---:|---:|---:|
| S01_simple | simple | simple | Yes | 0 | 0 |
| S02_tool | tool | tool | Yes | 0 | 0 |
| S03_missing | missing_info | missing_info | Yes | 0 | 0 |
| S04_risky | risky | risky | Yes | 0 | 1 |
| S05_error | error | missing_info | No | 0 | 0 |
| S06_delete | risky | risky | Yes | 0 | 1 |
| S07_dead_letter | error | error | Yes | 1 | 0 |

## 5. Failure analysis

1. Retry or tool failure: transient errors are recorded and routed through a bounded retry loop; exhausted attempts terminate with an actionable error instead of looping forever.
2. Risky action without approval: the graph interrupts before the action, persists pending state, and only resumes after an explicit approval value is supplied.

## 6. Persistence / recovery evidence

A checkpointer keyed by thread id preserves state and event history across the approval pause, allowing the run to resume without repeating completed nodes.

## 7. Extension work

Metrics are serialized to JSON and the report is rendered as portable Markdown for review or archival.

## 8. Improvement plan

Productionize first by adding durable SQLite/Postgres checkpointing, structured tracing and latency/error alerts, then expand route and recovery tests with adversarial inputs.
