"""Node functions for the LangGraph workflow."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel

from .llm import get_llm
from .state import AgentState, make_event


def intake_node(state: AgentState) -> dict:
    """Normalize raw query."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route using an LLM."""

    class Classification(BaseModel):
        route: Literal["simple", "tool", "missing_info", "risky", "error"]

    result = get_llm().with_structured_output(Classification).invoke(
        "Classify the request as simple, tool, missing_info, risky, or error. "
        "Priority: risky, tool, missing_info, error, simple. "
        f"Request: {state.get('query', '')}"
    )
    route = result.route
    return {
        "route": route,
        "risk_level": "high" if route == "risky" else "low",
        "events": [make_event("classify", "completed", f"classified as {route}")],
    }


def tool_node(state: AgentState) -> dict:
    """Execute a mock tool call, including transient error simulation."""
    attempt = state.get("attempt", 0)
    if state.get("route") == "error" and attempt < 2:
        result, event_type = f"ERROR: transient failure on attempt {attempt + 1}", "failed"
    else:
        result, event_type = f"Mock tool success for: {state.get('query', '')}", "completed"
    return {"tool_results": [result], "events": [make_event("tool", event_type, result)]}


def evaluate_node(state: AgentState) -> dict:
    """Determine whether the most recent tool result should be retried."""
    results = state.get("tool_results", [])
    latest = results[-1] if results else "ERROR: no tool result"
    evaluation = "needs_retry" if "ERROR" in latest.upper() else "success"
    return {
        "evaluation_result": evaluation,
        "events": [make_event("evaluate", "completed", f"result is {evaluation}")],
    }


def answer_node(state: AgentState) -> dict:
    """Generate a final, context-grounded response with an LLM."""
    response = get_llm().invoke(
        "Give a concise, helpful answer grounded only in this context.\n"
        f"Query: {state.get('query', '')}\n"
        f"Tool results: {state.get('tool_results', [])}\n"
        f"Approval: {state.get('approval')}"
    )
    answer = getattr(response, "content", str(response))
    if isinstance(answer, list):
        answer = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in answer)
    return {
        "final_answer": str(answer),
        "events": [make_event("answer", "completed", "response generated")],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask the user for the information needed to continue."""
    question = f"Could you provide more details about what you need for: {state.get('query', '')}?"
    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("clarify", "completed", "requested missing information")],
    }


def risky_action_node(state: AgentState) -> dict:
    """Describe a risky action before it is approved."""
    proposed_action = f"Perform the requested action: {state.get('query', '')}"
    return {
        "proposed_action": proposed_action,
        "events": [make_event("risky_action", "pending_approval", "action requires approval")],
    }


def approval_node(state: AgentState) -> dict:
    """Use mock approval by default, or a LangGraph interrupt when enabled."""
    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        decision = interrupt({"proposed_action": state.get("proposed_action", "")})
        approved = bool(decision.get("approved", False)) if isinstance(decision, dict) else bool(decision)
        approval = {
            "approved": approved,
            "reviewer": "human-reviewer",
            "comment": decision.get("comment", "") if isinstance(decision, dict) else "",
        }
    else:
        approval = {"approved": True, "reviewer": "mock-reviewer", "comment": "auto-approved"}
    return {
        "approval": approval,
        "events": [make_event("approval", "completed", "decision recorded", **approval)],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a failed attempt before the retry routing decision."""
    attempt = state.get("attempt", 0) + 1
    error = f"Retry {attempt} requested after an unsatisfactory tool result"
    return {
        "attempt": attempt,
        "errors": [error],
        "events": [make_event("retry", "completed", error)],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Produce a final response after bounded retries are exhausted."""
    return {
        "final_answer": "I could not complete this request after the allowed retries. Please try again later.",
        "events": [make_event("dead_letter", "failed", "maximum retries exceeded")],
    }


def finalize_node(state: AgentState) -> dict:
    """Emit the workflow's final audit event."""
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
