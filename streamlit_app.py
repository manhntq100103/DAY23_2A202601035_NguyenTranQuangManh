"""Streamlit approval console for the LangGraph workflow."""

from __future__ import annotations

import os
import uuid

import streamlit as st
from langgraph.types import Command

from langgraph_agent_lab.graph import build_graph
from langgraph_agent_lab.persistence import build_checkpointer
from langgraph_agent_lab.state import Route, Scenario, initial_state

os.environ["LANGGRAPH_INTERRUPT"] = "true"

st.set_page_config(page_title="LangGraph HITL", page_icon="✅")
st.title("Human approval console")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = f"ui-{uuid.uuid4().hex}"
if "graph" not in st.session_state:
    st.session_state.graph = build_graph(build_checkpointer("sqlite", "checkpoints.sqlite"))
if "pending" not in st.session_state:
    st.session_state.pending = None

query = st.text_area("Request", placeholder="Refund this customer and send confirmation email")
if st.button("Run workflow", type="primary") and query.strip():
    scenario = Scenario(id=st.session_state.thread_id, query=query, expected_route=Route.SIMPLE)
    config = {"configurable": {"thread_id": st.session_state.thread_id}}
    result = st.session_state.graph.invoke(initial_state(scenario), config=config)
    st.session_state.pending = result if "__interrupt__" in result else None
    if st.session_state.pending is None:
        st.success(result.get("final_answer", "Workflow completed"))

pending = st.session_state.pending
if pending:
    interrupts = pending.get("__interrupt__", [])
    payload = interrupts[0].value if interrupts else {}
    st.warning("Human approval required")
    st.write(payload.get("proposed_action", payload))
    col_a, col_r = st.columns(2)
    decision = None
    if col_a.button("Approve", type="primary"):
        decision = {"approved": True, "comment": "Approved in Streamlit"}
    if col_r.button("Reject"):
        decision = {"approved": False, "comment": "Rejected in Streamlit"}
    if decision is not None:
        config = {"configurable": {"thread_id": st.session_state.thread_id}}
        result = st.session_state.graph.invoke(Command(resume=decision), config=config)
        st.session_state.pending = result if "__interrupt__" in result else None
        st.rerun()

st.caption(f"Thread: {st.session_state.thread_id} (SQLite checkpointed)")
