"""Entry point (main branch): wire the pieces together by hand.

    python -m agent.part7_index

Notice this file opens and closes the browser itself. The
`harness-owns-environment` branch moves that responsibility into the harness,
where it belongs.
"""

from .browser import BrowserSession
from .part1_tools import create_tools
from .part2_model import MODEL
from .part3_context import create_context
from .part5_loop import run_loop

TASK = """
Upvote a story on Hacker News.

Go to https://news.ycombinator.com.
Call browser_get_stories to see ranked stories with their IDs, titles, and voted status.
Find the highest-ranked story where alreadyVoted is false.
Click its upvote arrow using the exact selector: a[id="up_STORYID"] (replace STORYID with the actual id).
When you are done, report which story you upvoted by both its title and its ID.
""".strip()


def main() -> None:
    print(f"Model: {MODEL}")
    print("Task:  upvote on Hacker News\n")

    session = BrowserSession()
    try:
        session.open()

        tools = create_tools(session)
        messages = create_context(TASK)
        result = run_loop(MODEL, messages, tools)

        print(f"\nAnswer: {result.answer}")
        print(f"Stopped by: {result.stopped_by}")
        print(f"Iterations: {result.iterations}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
