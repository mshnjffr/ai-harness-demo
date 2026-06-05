"""Harness-managed recovery.

This is harness engineering in miniature: instead of telling the model "try
harder" to log in, the harness detects the login/vote redirect and handles auth
itself, then hands control back to the agent. The capability is moved out of the
model and into the environment, where it is reliable.

Credentials come from HN_USERNAME / HN_PASSWORD (use a throwaway account).
"""

import os
import re
from typing import Callable, Optional

from .browser import BrowserSession
from .part5_loop import ToolEvent

# A vote redirect carries the story the agent was trying to upvote: /vote?id=N
_PENDING_ID = re.compile(r"[?&]id=(\d+)")
# The HN front page -- where a cast vote redirects back to (goto=news).
_FRONT_PAGE = re.compile(r"news\.ycombinator\.com/(news)?$")


def create_login_handler(
    session: BrowserSession,
    on_upvote_recovered: Optional[Callable[[str], None]] = None,
) -> Callable[[], Optional[ToolEvent]]:
    def handle() -> Optional[ToolEvent]:
        current_url = session.get_url()
        is_login_page = "login" in current_url or "vote" in current_url
        if not is_login_page:
            return None

        print("\n[harness] Login redirect detected - handling automatically...")

        username = os.environ.get("HN_USERNAME", "")
        password = os.environ.get("HN_PASSWORD", "")

        try:
            session.fill("input[name='acct']", username)
            session.fill("input[name='pw']", password)
            session.click("input[type='submit']")
            print("[harness] Login completed - agent can continue\n")

            # If the redirect that sent us here was a vote attempt, the agent's
            # in-flight intent (upvote story N) is encoded in the URL. Finish it
            # here, deterministically, instead of handing a vague "try again"
            # back to the model -- the model loses the target across recovery.
            pending_id = _pending_upvote_id(current_url)
            if pending_id is not None:
                completion = _complete_upvote(session, current_url, pending_id)
                if completion is not None:
                    if on_upvote_recovered is not None:
                        on_upvote_recovered(pending_id)
                    return completion

            return ToolEvent(
                tool="harness_auto_login",
                args={},
                result=(
                    f"Harness automatically handled login at {current_url}. "
                    f"You are now authenticated and back at {session.get_url()}."
                ),
            )
        except Exception as err:  # noqa: BLE001
            print(f"[harness] Login failed: {err}\n")
            return ToolEvent(
                tool="harness_auto_login",
                args={},
                result=f"Harness failed to handle login at {current_url}: {err}",
            )

    return handle


def _pending_upvote_id(url: str) -> Optional[str]:
    match = _PENDING_ID.search(url)
    return match.group(1) if match else None


def _complete_upvote(
    session: BrowserSession, login_url: str, story_id: str
) -> Optional[ToolEvent]:
    """Now that we're authenticated, re-issue the exact vote the agent was
    attempting when it hit the login wall. Returns a ToolEvent only if the vote
    landed back on the front page (i.e. it actually went through)."""
    session.navigate(f"https://news.ycombinator.com/vote?id={story_id}&how=up&goto=news")
    landed = session.get_url()
    if not _FRONT_PAGE.search(landed):
        return None

    print(f"[harness] Completed in-flight upvote for story ID {story_id}\n")
    return ToolEvent(
        tool="harness_auto_login",
        args={},
        result=(
            f"Harness handled login at {login_url} and completed your upvote "
            f"of story {story_id} -- now at {landed}"
        ),
    )
