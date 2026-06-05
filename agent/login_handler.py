"""Harness-managed recovery.

This is harness engineering in miniature: instead of telling the model "try
harder" to log in, the harness detects the login/vote redirect and handles auth
itself, then hands control back to the agent. The capability is moved out of the
model and into the environment, where it is reliable.

Credentials come from HN_USERNAME / HN_PASSWORD (use a throwaway account).
"""

import os
from typing import Callable, Optional

from .browser import BrowserSession
from .part5_loop import ToolEvent


def create_login_handler(session: BrowserSession) -> Callable[[], Optional[ToolEvent]]:
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
