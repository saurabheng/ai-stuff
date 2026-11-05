"""Smoke tests that don't require any API keys or network access."""
from career_agents.graph import AGENT_BUILDERS, compile_agent
from career_agents.state import CareerState
from career_agents.tools.job_boards import search_jobs
from career_agents.tools.linkedin_api import publish_post


def test_all_agents_compile():
    for name in AGENT_BUILDERS:
        graph = compile_agent(name)
        assert graph is not None


def test_state_is_typeddict():
    # Minimal construction should not raise.
    s: CareerState = {"agent": "linkedin_post", "profile": {}}
    assert s["agent"] == "linkedin_post"


def test_linkedin_publish_dry_run_without_credentials():
    result = publish_post("hello world")
    # Without credentials we must NOT post for real.
    assert result.ok is False
    assert "DRY RUN" in result.detail


def test_job_search_returns_links_even_offline():
    res = search_jobs(["python", "langchain"], location="Remote")
    assert "linkedin" in res.search_urls
    assert res.search_urls["linkedin"].startswith("https://www.linkedin.com/jobs/search/")