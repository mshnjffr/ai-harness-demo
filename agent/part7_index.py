"""Entry point (`verify-and-retry` branch): hand the harness a verify step and an attempt budget.

    python -m agent.part7_index

The harness runs the task, verifies the upvote actually happened, and retries
up to max_attempts if it did not (unless the failure is fatal).
"""

from .part2_model import MODEL
from .part6_harness import HarnessOptions, print_harness_result, run_harness, verify_successful_upvote

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

    result = run_harness(
        TASK,
        MODEL,
        HarnessOptions(verify=verify_successful_upvote, max_attempts=3),
    )
    print_harness_result(result)


if __name__ == "__main__":
    main()
