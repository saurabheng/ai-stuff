"""Shared typed state passed between nodes in the LangGraph graphs."""
from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages

AgentName = Literal["linkedin_post", "job_apply", "create_profile", "update_profile"]


class CareerState(TypedDict, total=False):
    """State shared across all agents.

    `messages` keeps the running chat transcript; everything else is scratch
    space that individual agents read/write.
    """

    messages: Annotated[list, add_messages]

    # Routing
    agent: AgentName
    task: str

    # Profile data (loaded from config/profile.json)
    profile: dict[str, Any]

    # Agent 1 - LinkedIn post / article
    topics: list[str]
    chosen_topic: str
    content_kind: Literal["post", "article"]
    draft: str
    revision_notes: str

    # Agent 2 - job apply
    jobs: list[dict[str, Any]]
    selected_job: dict[str, Any]
    cover_letter: str

    # Agents 3 & 4 - profiles
    platforms: list[str]
    profile_drafts: dict[str, str]

    # Generic result log surfaced to the user
    results: list[str]