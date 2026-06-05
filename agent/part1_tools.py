"""Tool registry.

Tools are bound to the BrowserSession the harness provides -- they do not reach
into a global. Each tool is an OpenAI function-tool definition plus a callable.

`hooks` lets the harness observe meaningful events (an upvote landing, the story
list loading) without the tools knowing what the harness does with them.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .browser import BrowserSession


@dataclass
class Tool:
    definition: dict
    execute: Callable[[dict], str]


@dataclass
class ToolRegistry:
    definitions: list = field(default_factory=list)
    by_name: dict = field(default_factory=dict)


@dataclass
class ToolHooks:
    on_upvote_success: Optional[Callable[[str], None]] = None
    on_stories_loaded: Optional[Callable[[list], None]] = None


def create_tools(session: BrowserSession, hooks: Optional[ToolHooks] = None) -> ToolRegistry:
    def _click(args: dict) -> str:
        selector = args["selector"]
        result = session.click(selector)
        # Detect a successful upvote: an up_<id> selector that lands back on the
        # HN front page (the vote redirect resolved without a login wall).
        if (
            hooks is not None
            and hooks.on_upvote_success is not None
            and "up_" in json.dumps(selector)
            and re.search(r"news\.ycombinator\.com/(news)?$", result.split("now at ")[-1].strip())
        ):
            match = re.search(r"up_(\d+)", selector)
            if match:
                hooks.on_upvote_success(match.group(1))
        return result

    def _get_stories(_args: dict) -> str:
        result = session.get_stories()
        if hooks is not None and hooks.on_stories_loaded is not None:
            try:
                hooks.on_stories_loaded(json.loads(result))
            except Exception:
                pass
        return result

    tools = [
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_navigate",
                    "description": "Navigate the browser to a URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                    },
                },
            },
            execute=lambda args: session.navigate(args["url"]),
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_url",
                    "description": "Get the URL of the current page. Use this to detect redirects (e.g. being sent to a login page).",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            execute=lambda _args: session.get_url(),
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_get_text",
                    "description": "Get the visible text content of the current page.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            execute=lambda _args: session.get_text(),
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_fill",
                    "description": "Fill in an input field on the current page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the input, e.g. \"input[name='acct']\"",
                            },
                            "value": {"type": "string", "description": "The value to type into the field."},
                        },
                        "required": ["selector", "value"],
                    },
                },
            },
            execute=lambda args: session.fill(args["selector"], args["value"]),
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click an element on the current page. Also waits for any navigation that results from the click.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector, e.g. \"input[type='submit']\"",
                            }
                        },
                        "required": ["selector"],
                    },
                },
            },
            execute=_click,
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_get_stories",
                    "description": "Get a structured list of Hacker News stories on the current page -- rank, story ID, title, and whether you've already voted. Use this instead of browser_get_text to accurately identify which story to upvote.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            },
            execute=_get_stories,
        ),
        Tool(
            definition={
                "type": "function",
                "function": {
                    "name": "browser_has_class",
                    "description": "Check whether the first element matching a selector has a specific CSS class. Use this to verify upvote state: check if a[id='up_12345'] has class 'nosee' before and after clicking.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector for the element to check."},
                            "className": {"type": "string", "description": "The CSS class name to look for."},
                        },
                        "required": ["selector", "className"],
                    },
                },
            },
            execute=lambda args: session.has_class(args["selector"], args["className"]),
        ),
    ]

    return ToolRegistry(
        definitions=[t.definition for t in tools],
        by_name={t.definition["function"]["name"]: t for t in tools},
    )
