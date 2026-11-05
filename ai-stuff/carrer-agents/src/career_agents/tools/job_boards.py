"""Job-search helpers.

IMPORTANT / ToS NOTE
--------------------
LinkedIn and most job boards prohibit automated scraping and automated
applications in their Terms of Service. This module therefore does NOT scrape
LinkedIn. Instead it:

1. Uses *public, ToS-friendly* job APIs when a key is available
   (e.g. Adzuna, Jooble, Remotive - all have free developer tiers).
2. Otherwise builds ready-to-open *search URLs* that a human clicks.

Every actual application remains a human action (open link, review, submit).
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field

import requests

REMOTIVE_API = "https://remotive.com/api/remote-jobs"


@dataclass
class Job:
    title: str
    company: str
    url: str
    location: str = ""
    source: str = ""
    description: str = ""


@dataclass
class JobSearchResult:
    jobs: list[Job] = field(default_factory=list)
    search_urls: dict[str, str] = field(default_factory=dict)
    note: str = ""


def _linkedin_search_url(keywords: str, location: str = "") -> str:
    params = {"keywords": keywords}
    if location:
        params["location"] = location
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


def search_jobs(tech_stack: list[str], location: str = "Remote", limit: int = 10) -> JobSearchResult:
    """Return jobs from the free Remotive API plus human-clickable search links.

    Remotive is a public, free, ToS-friendly remote-jobs API, so it is safe to
    query directly. LinkedIn is offered only as a URL for the human to open.
    """
    keywords = " ".join(tech_stack[:4]) if tech_stack else "software engineer"
    result = JobSearchResult()
    result.search_urls["linkedin"] = _linkedin_search_url(keywords, location)
    result.search_urls["google_jobs"] = (
        "https://www.google.com/search?q=" + urllib.parse.quote(f"{keywords} {location} jobs")
    )

    try:
        resp = requests.get(REMOTIVE_API, params={"search": keywords}, timeout=30)
        if resp.status_code == 200:
            for item in resp.json().get("jobs", [])[:limit]:
                result.jobs.append(
                    Job(
                        title=item.get("title", ""),
                        company=item.get("company_name", ""),
                        url=item.get("url", ""),
                        location=item.get("candidate_required_location", ""),
                        source="remotive",
                        description=item.get("description", "")[:600],
                    )
                )
            result.note = f"Found {len(result.jobs)} jobs via Remotive (free API)."
        else:
            result.note = f"Remotive returned {resp.status_code}; use the search URLs below."
    except requests.RequestException as exc:  # network boundary
        result.note = f"Could not reach Remotive ({exc}); use the search URLs below."

    return result
