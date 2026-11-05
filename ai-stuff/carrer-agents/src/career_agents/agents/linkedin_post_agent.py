"""Agent 1 - LinkedIn Post / Article agent.

Flow:
    suggest_topics -> [human picks topic] -> write_draft -> [human reviews]
    -> (approve) -> publish
    -> (request changes) -> revise -> back to review

All human steps use LangGraph `interrupt()`, which is what makes this a true
human-in-the-loop graph. Publishing uses the official LinkedIn API only.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from career_agents.llm import build_llm
from career_agents.state import CareerState
from career_agents.tools.linkedin_api import publish_post


def _suggest_topics(state: CareerState) -> dict:
    profile = state.get("profile", {})
    llm = build_llm()
    prompt = (
        "You are a LinkedIn content strategist. Based on this professional "
        f"profile, suggest 5 engaging, specific LinkedIn topic ideas.\n\n"
        f"Profile: {profile}\n\n"
        "Return exactly 5 ideas, one per line, numbered 1-5. No extra text."
    )
    resp = llm.invoke([SystemMessage(content="You suggest LinkedIn content topics."),
                       HumanMessage(content=prompt)])
    lines = [ln.strip(".-0123456789") for ln in str(resp.content).splitlines() if ln.strip()]
    topics = [ln for ln in lines if ln][:5]
    return {"topics": topics, "results": [f"Suggested {len(topics)} topics."]}


def _choose_topic(state: CareerState) -> dict:
    topics = state.get("topics", [])
    choice = interrupt(
        {
            "action": "choose_topic",
            "message": "Pick a topic by number, or type your own topic.",
            "topics": topics,
            "content_kind_options": ["post", "article"],
        }
    )
    # `choice` is whatever the human sends on resume.
    if isinstance(choice, dict):
        chosen = choice.get("topic", "")
        kind = choice.get("content_kind", "post")
    else:
        chosen, kind = str(choice), "post"

    # Allow picking by index.
    if chosen.isdigit() and topics:
        idx = int(chosen) - 1
        if 0 <= idx < len(topics):
            chosen = topics[idx]
            
    return {"chosen_topic": chosen, "content_kind": kind if kind in ("post", "article") else "post"}


def _write_draft(state: CareerState) -> dict:
    kind = state.get("content_kind", "post")
    topic = state.get("chosen_topic", "")
    profile = state.get("profile", {})
    notes = state.get("revision_notes", "")
    llm = build_llm(temperature=0.6)

    style = (
        "a concise, punchy LinkedIn POST (120-220 words) with a strong hook, "
        "short paragraphs, and 3-5 relevant hashtags"
        if kind == "post"
        else "a structured LinkedIn ARTICLE (500-800 words) with a title, intro, "
        "2-4 subheadings, and a closing call-to-action"
    )
    prompt = (
        f"Write {style} about: '{topic}'.\n"
        f"Write in first person, matching this profile: {profile}.\n"
    )
    if notes:
        prompt += f"\nIncorporate this reviewer feedback and rewrite accordingly:\n{notes}\n"

    resp = llm.invoke([SystemMessage(content="You are an expert LinkedIn ghostwriter."),
                       HumanMessage(content=prompt)])
    return {"draft": str(resp.content).strip(), "revision_notes": ""}


def _review(state: CareerState) -> dict:
    decision = interrupt(
        {
            "action": "review_draft",
            "message": "Approve to publish, or provide change requests.",
            "draft": state.get("draft", ""),
            "options": ["approve", "revise"],
        }
    )
    if isinstance(decision, dict):
        verdict = decision.get("decision", "revise")
        notes = decision.get("notes", "")
    else:
        text = str(decision).strip().lower()
        verdict = "approve" if text in ("approve", "approved", "yes", "ok") else "revise"
        notes = "" if verdict == "approve" else str(decision)
    return {"revision_notes": notes, "results": [f"Review decision: {verdict}"]}


def _route_after_review(state: CareerState) -> str:
    # If there are revision notes, the human asked for changes.
    return "revise" if state.get("revision_notes") else "publish"


def _revise(state: CareerState) -> dict:
    # Re-draft using the stored revision notes, then loop back to review.
    return _write_draft(state)


def _publish(state: CareerState) -> dict:
    result = publish_post(state.get("draft", ""))
    return {"results": [result.detail]}


def build_linkedin_post_graph() -> StateGraph:
    g = StateGraph(CareerState)
    g.add_node("suggest_topics", _suggest_topics)
    g.add_node("choose_topic", _choose_topic)
    g.add_node("write_draft", _write_draft)
    g.add_node("review", _review)
    g.add_node("revise", _revise)
    g.add_node("publish", _publish)

    g.add_edge(START, "suggest_topics")
    g.add_edge("suggest_topics", "choose_topic")
    g.add_edge("choose_topic", "write_draft")
    g.add_edge("write_draft", "review")
    g.add_conditional_edges("review", _route_after_review, {"revise": "revise", "publish": "publish"})
    g.add_edge("revise", "review")
    g.add_edge("publish", END)
    return g
