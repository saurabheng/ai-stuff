"""Agent 3 - Create Profile agent.

Takes the candidate's info (same profile data Agent 2 uses) and drafts a
platform-tailored profile/bio for each target platform. The human reviews every
draft, then the agent opens each platform's signup/profile page so the human can
create the account and paste the reviewed content.

ToS note: these platforms forbid automated account creation, so we never create
accounts or submit forms programmatically - the human does that final step.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from career_agents.llm import build_llm
from career_agents.state import CareerState
from career_agents.tools.browser import PLATFORM_URLS, open_platform

DEFAULT_CREATE_PLATFORMS = [
    "toptal", "turing","crossover","arc.dev","braintrust",
    "instahyre", "hirist", "wellfound", "cutshort",
    "gulftalent", "bayt", "remoteleaf",
]

_PLATFORM_HINTS = {
    "toptal": "Toptal values elite, top-3% framing and strong measurable achievements.",
    "turing": "Turing is remote US-company focused; emphasize remote collaboration & core stack.",
    "crossover": "Crossover emphasizes high-performance remote work and metrics.",
    "arc.dev": "Arc.dev is remote-first; highlight timezone overlap and async skills.",
    "braintrust": "Braintrust is a talent network; be concise and outcome-driven.",
    "instahyre": "Instahyre (India) values clear current CTC-free skill highlights.",
    "hirist": "Hirist (India) is tech-focused; lead with stack and years.",
    "wellfound": "Wellfound (AngelList) is startup-focused; show impact & ownership.",
    "cutshort": "Cutshort (India) uses skill tags; list precise skills.",
    "gulftalent": "GulfTalent targets the Middle East market; note relocation openness.",
    "bayt": "Bayt targets MENA region; include languages and relocation preferences.",
    "remoteleaf": "Remoteleaf curates remote jobs; emphasize remote-ready profile.",
}


def _draft_profiles(state: CareerState) -> dict:
    profile = state.get("profile", {})
    platforms = state.get("platforms") or DEFAULT_CREATE_PLATFORMS
    platforms = [p for p in platforms if p in PLATFORM_URLS]
    llm = build_llm(temperature=0.5)

    drafts: dict[str, str] = {}
    for platform in platforms:
        hint = _PLATFORM_HINTS.get(platform, "")
        prompt = (
            f"Write a profile summary/bio tailored for the platform '{platform}'. {hint}\n"
            f"Candidate profile data: {profile}\n"
            "Return: (1) a 1-line headline, (2) a 3-4 sentence bio, (3) a comma-separated skills list. "
            "Keep it honest and specific."
        )
        resp = llm.invoke([SystemMessage(content="You craft tailored professional profiles."),
            HumanMessage(content=prompt)])
        drafts[platform] = str(resp.content).strip()
    return {"profile_drafts": drafts, "platforms": platforms,
        "results": [f"Drafted profiles for {len(drafts)} platforms."]}


def _review_profiles(state: CareerState) -> dict:
    decision = interrupt(
        {
            "action": "review_profiles",
            "message": "Review the per-platform profile drafts. Approve to open signup pages, or request changes.",
            "profile_drafts": state.get("profile_drafts", {}),
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
    # Simple revision: regenerate all drafts incorporating the notes.
    profile = dict(state.get("profile", {}))
    profile["_reviewer_feedback"] = state.get("revision_notes", "")
    return _draft_profiles({**state, "profile": profile})


def _open_pages(state: CareerState) -> dict:
    msgs = [open_platform(p) for p in state.get("platforms", [])]
    msgs.append("Paste the reviewed profile text into each page and submit manually.")
    return {"results": msgs, "revision_notes": ""}


def build_create_profile_graph() -> StateGraph:
    g = StateGraph(CareerState)
    g.add_node("draft_profiles", _draft_profiles)
    g.add_node("review_profiles", _review_profiles)
    g.add_node("revise", _revise)
    g.add_node("open_pages", _open_pages)

    g.add_edge(START, "draft_profiles")
    g.add_edge("draft_profiles", "review_profiles")
    g.add_conditional_edges("review_profiles", _route, {"revise": "revise", "open_pages": "open_pages"})
    g.add_edge("revise", "review_profiles")
    g.add_edge("open_pages", END)
    return g
