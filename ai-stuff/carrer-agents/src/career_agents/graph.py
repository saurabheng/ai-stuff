"""Graph registry + a reusable human-in-the-loop run loop.

Each agent is an independent LangGraph compiled with a checkpointer so it can
pause at `interrupt()` and resume after a human responds.
"""
from __future__ import annotations

from typing import Callable

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from career_agents.agents import (
    build_create_profile_graph,
    build_job_apply_graph,
    build_linkedin_post_graph,
    build_update_profile_graph,
)

AGENT_BUILDERS: dict[str, Callable[[], object]] = {
    "linkedin_post": build_linkedin_post_graph,
    "job_apply": build_job_apply_graph,
    "create_profile": build_create_profile_graph,
    "update_profile": build_update_profile_graph,
}

AGENT_DESCRIPTIONS = {
    "linkedin_post": "Suggest topics -> write post/article -> human review -> publish (official API).",
    "job_apply": "Search jobs from tech stack -> human picks -> cover letter -> human review -> open to apply.",
    "create_profile": "Draft profiles for Toptal/Turing/Arc.dev/... -> human review -> open signup pages.",
    "update_profile": "Refresh headline/summary across LinkedIn/Naukri/... -> human review -> open pages.",
}


def compile_agent(agent: str, checkpointer: MemorySaver | None = None) -> CompiledStateGraph:
    if agent not in AGENT_BUILDERS:
        raise ValueError(f"Unknown agent '{agent}'. Choices: {', '.join(AGENT_BUILDERS)}")
    builder = AGENT_BUILDERS[agent]()
    return builder.compile(checkpointer=checkpointer or MemorySaver())  # type: ignore[attr-defined]
