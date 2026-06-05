"""Entry point (branch 2): the harness owns everything now.

    python -m agent.part7_index

Compare this to branch 0/1, where this file opened and closed the browser by
hand. That responsibility now lives inside run_harness().
"""

from .part2_model import MODEL
from .part6_harness import print_harness_result, run_harness

TASK = """
Upvote a story on Hacker News.

Go to https://news.ycombinator.com.
Call browser_get_stories to see ranked stories with their IDs and voted status.
Find the highest-ranked story where alreadyVoted is false.
Click its upvote arrow using the exact selector: a[id="up_STORYID"] (replace STORYID with the actual id).
""".strip()


def main() -> None:
    print(f"Model: {MODEL}")
    print("Task:  upvote on Hacker News\n")

    result = run_harness(TASK, MODEL)
    print_harness_result(result)


if __name__ == "__main__":
    main()
