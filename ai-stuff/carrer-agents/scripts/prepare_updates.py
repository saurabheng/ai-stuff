"""Headless helper used by the scheduled GitHub Action.

Generates updated profile headline/summary drafts WITHOUT any human prompt and
prints them as Markdown. It never opens browsers or submits anything - the human
reviews the issue created by the workflow and applies updates manually.
"""
from __future__ import annotations

from career_agents.agents.profile_update_agent import _draft_updates  # noqa: PLC2701
from career_agents.config import get_settings


def main() -> None:
    settings = get_settings()
    profile = settings.load_profile()
    try:
        out = _draft_updates({"profile": profile})
    except Exception as exc:  # no key configured in CI, etc.
        print(f"Could not generate drafts: {exc}")
        return

    print("## Suggested profile update\n")
    drafts = out.get("profile_drafts", {})
    if drafts:
        print(next(iter(drafts.values())))
    print("\n### Platforms to update\n")
    for p in out.get("platforms", []):
        print(f"- {p}")


if __name__ == "__main__":
    main()