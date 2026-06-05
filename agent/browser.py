"""The environment the harness owns: one isolated browser page per run.

Tools (part1_tools.py) are bound to a BrowserSession instance. They never
manage the browser lifecycle themselves -- the harness opens and closes it.
"""

import json

from playwright.sync_api import sync_playwright


class BrowserSession:
    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._page = None

    def open(self) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=False)
        context = self._browser.new_context()
        self._page = context.new_page()

    def navigate(self, url: str) -> str:
        self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Navigated to {url}"

    def get_url(self) -> str:
        return self._page.url

    def get_text(self) -> str:
        return self._page.inner_text("body")[:4000]

    def fill(self, selector: str, value: str) -> str:
        self._page.fill(selector, value)
        return f'Filled "{selector}"'

    def click(self, selector: str) -> str:
        # Capture the id before clicking; navigation may replace the page.
        element_id = self._page.locator(selector).first.get_attribute("id")

        self._page.click(selector, timeout=10000)
        self._page.wait_for_load_state("domcontentloaded", timeout=10000)

        clicked = f'element id="{element_id}"' if element_id else f'"{selector}"'
        return f"Clicked {clicked} -- now at {self._page.url}"

    def get_stories(self) -> str:
        """Structured HN front-page stories so the agent can correlate IDs,
        titles, ranks, and voted status precisely (instead of scraping text)."""
        stories = self._page.evaluate(
            """
            () => Array.from(document.querySelectorAll('.athing')).map((row, i) => {
              const id = row.id;
              const title = row.querySelector('.titleline a')?.textContent?.trim() ?? '(no title)';
              const upvoteEl = document.querySelector(`#up_${id}`);
              const alreadyVoted = upvoteEl?.classList.contains('nosee') ?? true;
              return { rank: i + 1, id, title, alreadyVoted };
            })
            """
        )
        return json.dumps(stories, indent=2)

    def has_class(self, selector: str, class_name: str) -> str:
        el = self._page.locator(selector).first
        classes = el.get_attribute("class") or ""
        has = class_name in classes.split(" ")
        if has:
            return f'"{selector}" has class "{class_name}"'
        return f'"{selector}" does not have class "{class_name}"'

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._pw is not None:
            self._pw.stop()
        self._browser = None
        self._page = None
        self._pw = None
