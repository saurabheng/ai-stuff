"""MCP server exposing the career agents with HUMAN-IN-THE-LOOP via elicitation.

Run this as an MCP server (stdio) and connect it from any MCP client
(VS Code, Claude Desktop, etc.). Each agent is a tool; whenever the underlying
LangGraph hits an `interrupt()`, the server uses MCP *elicitation* to ask the
connected human to approve / edit / choose, then resumes the graph.

Start it:
    python -m career_agents.mcp_server
or register the command in your MCP client config (see README).
"""
from __future__ import annotations

import uuid

from mcp.server.fastmcp import Context, FastMCP
from langgraph.types import Command
from pydantic import BaseModel, Field

from career_agents.config import get_settings
from career_agents.graph import AGENT_DESCRIPTIONS, compile_agent

mcp = FastMCP("career-agents")


class HumanResponse(BaseModel):
    """Free-form human reply used to resume the graph."""

    response: str = Field(
        description=(
            "Your decision. For reviews type 'approve' or describe the changes. "
            "For a topic/job choice type the number or the topic text."
        )
    )


async def _run_agent(agent: str, ctx: Context) -> str:
    settings = get_settings()
    profile = settings.load_profile()
    graph = compile_agent(agent)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    state_in: object = {"agent": agent, "profile": profile, "results": []}

    transcript: list[str] = []
    while True:
        result = graph.invoke(state_in, config=config)
        interrupts = result.get("__interrupt__") if isinstance(result, dict) else None

        if interrupts:
            payload = interrupts[0].value
            message = _format_payload(payload)
            elicited = await ctx.elicit(message=message, schema=HumanResponse)

            if elicited.action != "accept" or elicited.data is None:
                transcript.append("Human cancelled the workflow.")
                break

            state_in = Command(resume=_coerce(elicited.data.response, payload))
            continue

        transcript.extend(result.get("results", []))
        transcript.append("workflow complete.")
        break

    return "\n".join(f"- {line}" for line in transcript)


def _format_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return str(payload)
    parts = [payload.get("message", "")]
    for key in ("topics", "draft", "cover_letter", "jobs", "profile_drafts", "update", "options"):
        if payload.get(key):
            parts.append(f"\n{key}:\n{payload[key]}")
    return "\n".join(p for p in parts if p)


def _coerce(answer: str, payload: object) -> object:
    action = payload.get("action", "") if isinstance(payload, dict) else ""
    answer = answer.strip()
    if action == "choose_topic":
        kind = "article" if "article" in answer.lower() else "post"
        topic = answer.replace("article", "").replace("post", "").strip() or answer
        return {"topic": topic, "content_kind": kind}
    if action in ("review_draft", "review_cover_letter", "review_profiles", "review_updates"):
        if answer.lower().startswith("approve") or answer.lower() in ("y", "yes", "ok"):
            return {"decision": "approve"}
        return {"decision": "revise", "notes": answer}
    if action == "select_job":
        digits = "".join(ch for ch in answer if ch.isdigit())
        return {"index": int(digits) if digits else 0}
    return answer


# Register one MCP tool per agent.
@mcp.tool(description=AGENT_DESCRIPTIONS["linkedin_post"])
async def linkedin_post_agent(ctx: Context) -> str:
    return await _run_agent("linkedin_post", ctx)


@mcp.tool(description=AGENT_DESCRIPTIONS["job_apply"])
async def job_apply_agent(ctx: Context) -> str:
    return await _run_agent("job_apply", ctx)


@mcp.tool(description=AGENT_DESCRIPTIONS["create_profile"])
async def create_profile_agent(ctx: Context) -> str:
    return await _run_agent("create_profile", ctx)


@mcp.tool(description=AGENT_DESCRIPTIONS["update_profile"])
async def update_profile_agent(ctx: Context) -> str:
    return await _run_agent("update_profile", ctx)


def main() -> None:
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
