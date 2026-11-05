"""Human-driven browser helper.

These agents assist with profile creation/updates on platforms (Toptal, Arc.dev,
Wellfound, etc.) whose Terms of Service forbid automated account creation and
automated submissions. To stay compliant, this helper only *opens* the relevant
page in the user's real browser so the human can review and submit personally.
It never fills credentials or clicks "submit" on the user's behalf.
"""
from __future__ import annotations

import webbrowser

# Signup / profile URLs for the supported platforms.
PLATFORM_URLS: dict[str, str] = {
    "toptal": "https://www.toptal.com/talent/apply",
    "turing": "https://www.turing.com/developers",
    "crossover": "https://www.crossover.com/",
    "arc.dev": "https://arc.dev/remote-developer-jobs",
    "braintrust": "https://www.usebraintrust.com/talent",
    "instahyre": "https://www.instahyre.com/candidate/",
    "hirist": "https://www.hirist.tech/",
    "wellfound": "https://wellfound.com/jobs",
    "cutshort": "https://www.cutshort.io/",
    "gulftalent": "https://www.gulftalent.com/",
    "bayt": "https://www.bayt.com/",
    "remoteleaf": "https://remoteleaf.com/",
    "naukri": "https://www.naukri.com/mnuser/profile",
    "linkedin": "https://www.linkedin.com/in/",
}


def open_platform(platform: str) -> str:
    """Open a platform page in the default browser for the human to act on."""
    key = platform.lower().strip()
    url = PLATFORM_URLS.get(key)
    if not url:
        return f"Unknown platform '{platform}'. Known: {', '.join(sorted(PLATFORM_URLS))}"
    try:
        webbrowser.open(url, new=2)
        return f"Opened {platform} ({url}) in your browser. Review and submit manually."
    except Exception as exc:  # environment without a browser (e.g. headless CI)
        return f"Could not open a browser ({exc}). Visit {url} manually."
