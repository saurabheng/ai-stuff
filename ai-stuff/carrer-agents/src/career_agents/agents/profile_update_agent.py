"""Agent 4 - Update Profile agent.

Periodically refreshes the candidate's profile text across all platforms
(LinkedIn, Naukri + the Agent-3 set). It generates an updated headline/summary,
the human approves, then it opens each profile page for the human to paste and
save. Designed to be triggered on a schedule (see README: GitHub Actions cron).

ToS note: updates are applied by the human on each site; no automated form
submission or scraping is performed.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from career_agents.llm import build_llm
from career_agents.state import CareerState
from career_agents.tools.browser import PLATFORM_URLS, open_platform

DEFAULT_UPDATE_PLATFORMS = [
    "linkedin",
    "naukri",
    "toptal",
    "turing",
    "crossover",
    "arc.dev",
    "braintrust",
    "instahyre",
    "hirist",
    "wellfound",
    "cutshort",
    "gulftalent",
    "bayt",
    "remoteleaf",
]


def _draft_updates(state: CareerState) -> dict:
    profile = state.get("profile", {})
    platforms = state.get("platforms") or DEFAULT_UPDATE_PLATFORMS
    platforms = [p for p in platforms if p in PLATFORM_URLS]
    llm = build_llm(temperature=0.4)

    prompt = (
        "The candidate wants to refresh their professional profile. Based on the "
        "profile data, produce an UPDATED headline and an UPDATED 3-4 sentence summary "
        "that reflect current skills and recent achievements. Keep it honest.\n"
        f"Profile data: {profile}"
    )
    resp = llm.invoke([
        SystemMessage(content="You keep professional profiles current and compelling."),
        HumanMessage(content=prompt),
    ])
    updated = str(resp.content).strip()
    drafts = {p: updated for p in platforms}
    return {
        "profile_drafts": drafts,
        "platforms": platforms,
        "results": [f"Prepared profile updates for {len(platforms)} platforms."],
    }


def _review_updates(state: CareerState) -> dict:
    decision = interrupt(
        {
            "action": "review_updates",
            "message": "Review the updated headline/summary. Approve to open each profile page, or request changes.",
            "update": next(iter(state.get("profile_drafts", {}).values()), ""),
            "platforms": state.get("platforms", []),
            "options": ["approve", "revise"],
        }
    )
    if isinstance(decision, dict):
        verdict = decision.get("decision", "revise")
        notes = decision.get("notes", "")
    else:
        verdict = "approve" if str(decision).strip().lower().startswith("approve") else "revise"
        notes = "" if verdict == "approve" else str(decision)
    return {"revision_notes": notes}


def _route(state: CareerState) -> str:
    return "revise" if state.get("revision_notes") else "open_pages"


def _revise(state: CareerState) -> dict:
    profile = dict(state.get("profile", {}))
    profile["_reviewer_feedback"] = state.get("revision_notes", "")
    return _draft_updates({**state, "profile": profile})


def _open_pages(state: CareerState) -> dict:
    msgs = [open_platform(p) for p in state.get("platforms", [])]
    msgs.append("Paste the approved headline/summary into each profile page and save.")
    return {"results": msgs, "revision_notes": ""}


def build_update_profile_graph() -> StateGraph:
    g = StateGraph(CareerState)
    g.add_node("draft_updates", _draft_updates)
    g.add_node("review_updates", _review_updates)
    g.add_node("revise", _revise)
    g.add_node("open_pages", _open_pages)

    g.add_edge(START, "draft_updates")
    g.add_edge("draft_updates", "review_updates")
    g.add_conditional_edges("review_updates", _route, {"revise": "revise", "open_pages": "open_pages"})
    g.add_edge("revise", "review_updates")
    g.add_edge("open_pages", END)
    return g
