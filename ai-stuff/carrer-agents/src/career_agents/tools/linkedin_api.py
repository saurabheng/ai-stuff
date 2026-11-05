"""LinkedIn integration - OFFICIAL REST API ONLY.

This module deliberately uses only LinkedIn's approved REST API with an OAuth
access token that *you* generate for *your own* account. It does NOT scrape,
automate the website, or bypass any access control. Posting still happens only
after a human approves the content elsewhere in the graph.

Docs: https://learn.microsoft.com/linkedin/marketing/community-management/shares/posts-api
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from career_agents.config import get_settings

_POSTS_URL = "https://api.linkedin.com/rest/posts"
_LINKEDIN_VERSION = "202411"  # yyyymm, bump periodically


@dataclass
class PostResult:
    ok: bool
    detail: str
    post_id: str | None = None


def publish_post(text: str) -> PostResult:
    """Publish a text post to the authenticated member's feed via the official API.

    Requires LINKEDIN_ACCESS_TOKEN (w_member_social scope) and LINKEDIN_AUTHOR_URN.
    If credentials are missing we return a dry-run result instead of failing hard,
    so the rest of the pipeline stays testable without live posting.
    """
    settings = get_settings()
    token = settings.linkedin_access_token
    author = settings.linkedin_author_urn

    if not token or not author or author.endswith("xxxxxxxx"):
        return PostResult(
            ok=False,
            detail=(
                "DRY RUN: LinkedIn credentials not configured. "
                "Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN in .env to post for real. "
                "No automated posting was performed."
            ),
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": _LINKEDIN_VERSION,
    }
    payload = {
        "author": author,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    try:
        resp = requests.post(_POSTS_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:  # network boundary
        return PostResult(ok=False, detail=f"Network error contacting LinkedIn: {exc}")

    if resp.status_code in (200, 201):
        return PostResult(ok=True, detail="Published to LinkedIn.", post_id=resp.headers.get("x-restli-id"))
    return PostResult(ok=False, detail=f"LinkedIn API error {resp.status_code}: {resp.text[:400]}")
