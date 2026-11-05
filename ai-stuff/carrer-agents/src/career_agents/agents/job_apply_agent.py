"""Agent 2 - Job Apply agent.

Flow:
    read tech stack from profile -> search jobs (free API + human-clickable links)
    -> [human selects a job] -> draft tailored cover letter
    -> [human reviews cover letter] -> open job URL for the human to apply

The actual application is always performed by the human (we open the posting).
No LinkedIn scraping or auto-apply is performed.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from career_agents.llm import build_llm
from career_agents.state import CareerState
from career_agents.tools.browser import open_platform
from career_agents.tools.job_boards import search_jobs


def _search(state: CareerState) -> dict:
    profile = state.get("profile", {})
    tech = profile.get("tech_stack", [])
    location = (profile.get("preferred_locations") or ["Remote"])[0]
    res = search_jobs(tech, location=location)
    jobs = [j.__dict__ for j in res.jobs]
    note = res.note + " | Search links: " + ", ".join(f"{k}: {v}" for k, v in res.search_urls.items())
    return {"jobs": jobs, "results": [note]}


def _select_job(state: CareerState) -> dict:
    jobs = state.get("jobs", [])
    choice = interrupt(
        {
            "action": "select_job",
            "message": "Select a job by index to generate a tailored cover letter.",
            "jobs": [{"index": i, "title": j["title"], "company": j["company"], "url": j["url"]}
                     for i, j in enumerate(jobs)],
        }
    )
    idx = int(choice.get("index", 0)) if isinstance(choice, dict) else int(str(choice) or 0)
    selected = jobs[idx] if 0 <= idx < len(jobs) else (jobs[0] if jobs else {})
    return {"selected_job": selected}


def _draft_cover_letter(state: CareerState) -> dict:
    job = state.get("selected_job", {})
    profile = state.get("profile", {})
    notes = state.get("revision_notes", "")
    llm = build_llm(temperature=0.5)
    prompt = (
        "Write a tailored, concise cover letter (max 250 words) for this job.\n"
        f"Job: {job.get('title')} at {job.get('company')}.\n"
        f"Job description: {job.get('description', '')}\n"
        f"Candidate profile: {profile}\n"
        "Be specific, reference the candidate's real skills, avoid clichés."
    )
    if notes:
        prompt += f"\nApply this reviewer feedback:\n{notes}"
    resp = llm.invoke([SystemMessage(content="You write excellent, honest cover letters."),
                       HumanMessage(content=prompt)])
    return {"cover_letter": str(resp.content).strip(), "revision_notes": ""}


def _review_cover_letter(state: CareerState) -> dict:
    decision = interrupt(
        {
            "action": "review_cover_letter",
            "message": "Approve to open the application page, or request changes.",
            "cover_letter": state.get("cover_letter", ""),
            "job": state.get("selected_job", {}),
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
    return "revise" if state.get("revision_notes") else "open_application"


def _open_application(state: CareerState) -> dict:
    job = state.get("selected_job", {})
    url = job.get("url", "")
    msg = f"Ready to apply. Cover letter is drafted above. Opening: {url}"
    # Open LinkedIn page helper if no direct URL.
    if url:
        import webbrowser

        try:
            webbrowser.open(url, new=2)
        except Exception:
            msg = f"Visit the posting manually to apply: {url}"
    else:
        msg = open_platform("linkedin")
    return {"results": [msg]}


def build_job_apply_graph() -> StateGraph:
    g = StateGraph(CareerState)
    g.add_node("search", _search)
    g.add_node("select_job", _select_job)
    g.add_node("draft_cover_letter", _draft_cover_letter)
    g.add_node("review_cover_letter", _review_cover_letter)
    g.add_node("revise", _draft_cover_letter)
    g.add_node("open_application", _open_application)

    g.add_edge(START, "search")
    g.add_edge("search", "select_job")
    g.add_edge("select_job", "draft_cover_letter")
    g.add_edge("draft_cover_letter", "review_cover_letter")
    g.add_conditional_edges("review_cover_letter", _route,
                            {"revise": "revise", "open_application": "open_application"})
    g.add_edge("revise", "review_cover_letter")
    g.add_edge("open_application", END)
    return g
