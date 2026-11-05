"""CLI entry point.

Runs any of the four agents in an interactive, human-in-the-loop loop in the
terminal. Each time the graph hits `interrupt()`, we print the request and read
the human's response from stdin, then resume.

Usage:
    career-agents list
    career-agents run linkedin_post
    career-agents run job_apply
    career-agents run create_profile
    career-agents run update_profile
"""
from __future__ import annotations

import uuid

import typer
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from career_agents.config import get_settings
from career_agents.graph import AGENT_DESCRIPTIONS, compile_agent

app = typer.Typer(add_completion=False, help="Human-in-the-loop career agents.")
console = Console()


@app.command("list")
def list_agents() -> None:
    """List available agents."""
    for name, desc in AGENT_DESCRIPTIONS.items():
        console.print(f"[bold cyan]{name}[/]: {desc}")


def _render_interrupt(payload: dict) -> None:
    action = payload.get("action", "input")
    console.print(Panel.fit(payload.get("message", ""), title=f"[yellow]HUMAN INPUT NEEDED: {action}[/]"))
    for key in ("topics", "jobs", "draft", "cover_letter", "profile_drafts", "update", "options"):
        if key in payload and payload[key]:
            console.print(f"[bold]{key}:[/]")
            console.print(payload[key])


@app.command("run")
def run(agent: str, resume_thread: str = typer.Option("", help="Resume an existing thread id")) -> None:
    """Run an agent interactively with human-in-the-loop checkpoints."""
    settings = get_settings()
    profile = settings.load_profile()
    graph = compile_agent(agent)
    thread_id = resume_thread or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    console.print(f"[green]Starting agent[/] [bold]{agent}[/] (thread {thread_id})")
    state_in: object = {"agent": agent, "profile": profile, "results": []}

    while True:
        result = graph.invoke(state_in, config=config)
        interrupts = result.get("__interrupt__") if isinstance(result, dict) else None

        if interrupts:
            payload = interrupts[0].value
            _render_interrupt(payload if isinstance(payload, dict) else {"message": str(payload)})
            answer = Prompt.ask("[bold magenta]Your response[/]")
            # Pass structured decisions where the node expects them.
            state_in = Command(resume=_coerce(answer, payload))
            continue

        # Finished.
        for line in result.get("results", []):
            console.print(f"[green]*[/] {line}")
        console.print("[bold green]Done.[/]")
        break


def _coerce(answer: str, payload: object) -> object:
    """Shape the raw stdin answer into what the interrupting node expects."""
    action = payload.get("action", "") if isinstance(payload, dict) else ""
    answer = answer.strip()

    if action == "choose_topic":
        kind = "article" if "article" in answer.lower() else "post"
        topic = answer.replace("article", "").replace("post", "").strip() or answer
        return {"topic": topic, "content_kind": kind}

    if action in ("review_draft", "review_cover_letter", "review_profiles", "review_updates"):
        low = answer.lower()
        if low.startswith("approve") or low in ("y", "yes", "ok"):
            return {"decision": "approve"}
        return {"decision": "revise", "notes": answer}

    if action == "select_job":
        digits = "".join(ch for ch in answer if ch.isdigit())
        return {"index": int(digits) if digits else 0}

    return answer


if __name__ == "__main__":
    app()
