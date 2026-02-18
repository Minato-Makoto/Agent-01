"""
AgentForge — Browser tools using Playwright.

Tools: browser_navigate, browser_click, browser_type, browser_screenshot,
       browser_get_content, browser_evaluate, browser_wait, browser_scroll,
       browser_select, browser_close

Uses a persistent browser context per session.
"""

import os
import json
import base64
import logging
from typing import Any, Dict, Optional

from agentforge.tools import Tool, ToolRegistry, ToolResult
from agentforge.runtime_config import load_tool_timeout_config

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages a persistent Playwright browser instance."""
    _playwright = None
    _browser = None
    _page = None

    @staticmethod
    def _headless_from_env() -> bool:
        value = os.environ.get("AGENTFORGE_BROWSER_HEADLESS", "0").strip().lower()
        return value in {"1", "true", "yes", "on"}

    @classmethod
    def get_page(cls):
        """Get or create the browser page."""
        if cls._page is None:
            try:
                from playwright.sync_api import sync_playwright
                cls._playwright = sync_playwright().start()
                # Default to visible browser so users can see interaction.
                cls._browser = cls._playwright.chromium.launch(
                    headless=cls._headless_from_env()
                )
                cls._page = cls._browser.new_page()
            except ImportError:
                raise ImportError(
                    "Playwright is not installed. Run: pip install playwright && playwright install chromium"
                )
        return cls._page

    @classmethod
    def close(cls):
        """Close the browser and clean up."""
        if cls._page:
            cls._page.close()
            cls._page = None
        if cls._browser:
            cls._browser.close()
            cls._browser = None
        if cls._playwright:
            cls._playwright.stop()
            cls._playwright = None


def _workspace_root() -> str:
    raw = str(os.environ.get("AGENTFORGE_WORKSPACE", "")).strip()
    if raw:
        return os.path.abspath(raw)
    return os.path.abspath(os.path.join(os.getcwd(), "workspace"))


def _tool_timeouts():
    return load_tool_timeout_config()


def register(registry: ToolRegistry, skill_name: str = "Browser") -> None:
    """Register all browser tools."""
    tools = [
        Tool(name="browser_navigate", description="Navigate to a URL.",
             input_schema={"type": "object", "properties": {
                 "url": {"type": "string", "description": "URL to navigate to."}
             }, "required": ["url"]}, execute_fn=_navigate),
        Tool(name="browser_click", description="Click an element on the page.",
             input_schema={"type": "object", "properties": {
                 "selector": {"type": "string", "description": "CSS selector."},
                 "text": {"type": "string", "description": "Click element containing this text."}
             }}, execute_fn=_click),
        Tool(name="browser_type", description="Type text into an input field.",
             input_schema={"type": "object", "properties": {
                 "selector": {"type": "string", "description": "CSS selector of input."},
                 "text": {"type": "string", "description": "Text to type."}
             }, "required": ["selector", "text"]}, execute_fn=_type),
        Tool(name="browser_screenshot", description="Take a screenshot of the page.",
             input_schema={"type": "object", "properties": {
                 "full_page": {"type": "boolean", "description": "Capture full page.", "default": False}
             }}, execute_fn=_screenshot),
        Tool(name="browser_get_content", description="Get page text or accessibility tree.",
             input_schema={"type": "object", "properties": {
                 "selector": {"type": "string", "description": "CSS selector for specific element."},
                 "mode": {"type": "string", "description": "'text' or 'accessibility'.", "default": "text"}
             }}, execute_fn=_get_content),
        Tool(name="browser_evaluate", description="Execute JavaScript on the page.",
             input_schema={"type": "object", "properties": {
                 "js_code": {"type": "string", "description": "JavaScript code to execute."}
             }, "required": ["js_code"]}, execute_fn=_evaluate),
        Tool(name="browser_wait", description="Wait for an element to appear.",
             input_schema={"type": "object", "properties": {
                 "selector": {"type": "string", "description": "CSS selector."},
                 "timeout": {"type": "integer", "description": "Timeout in ms.", "default": 10000}
             }, "required": ["selector"]}, execute_fn=_wait),
        Tool(name="browser_scroll", description="Scroll the page.",
             input_schema={"type": "object", "properties": {
                 "direction": {"type": "string", "description": "'up' or 'down'."},
                 "amount": {"type": "integer", "description": "Pixels to scroll.", "default": 500}
             }, "required": ["direction"]}, execute_fn=_scroll),
        Tool(name="browser_select", description="Select a value from a dropdown.",
             input_schema={"type": "object", "properties": {
                 "selector": {"type": "string", "description": "CSS selector of select element."},
                 "value": {"type": "string", "description": "Value to select."}
             }, "required": ["selector", "value"]}, execute_fn=_select),
        Tool(name="browser_close", description="Close the browser instance.",
             input_schema={"type": "object", "properties": {}}, execute_fn=_close),
    ]
    registry.register_skill(skill_name, tools)


def _navigate(args: Dict[str, Any]) -> ToolResult:
    url = args.get("url", "")
    if not url:
        return ToolResult(success=False, output=None, error="Missing 'url'")
    try:
        page = BrowserManager.get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=_tool_timeouts().browser_nav_ms)
        return ToolResult(success=True, output={"title": page.title(), "url": page.url})
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_navigate failed", logger=logger)


def _click(args: Dict[str, Any]) -> ToolResult:
    selector = args.get("selector", "")
    text = args.get("text", "")
    try:
        page = BrowserManager.get_page()
        action_timeout = _tool_timeouts().browser_action_ms
        if text:
            page.get_by_text(text).first.click(timeout=action_timeout)
        elif selector:
            page.click(selector, timeout=action_timeout)
        else:
            return ToolResult(success=False, output=None, error="Provide 'selector' or 'text'")
        return ToolResult(success=True, output="Clicked successfully")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_click failed", logger=logger)


def _type(args: Dict[str, Any]) -> ToolResult:
    selector = args.get("selector", "")
    text = args.get("text", "")
    try:
        page = BrowserManager.get_page()
        page.fill(selector, text, timeout=_tool_timeouts().browser_action_ms)
        return ToolResult(success=True, output=f"Typed '{text}' into {selector}")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_type failed", logger=logger)


def _screenshot(args: Dict[str, Any]) -> ToolResult:
    full_page = args.get("full_page", False)
    try:
        page = BrowserManager.get_page()
        screenshot_bytes = page.screenshot(full_page=full_page)
        # Save to file and return path
        screenshot_dir = os.path.join(_workspace_root(), "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        import time
        filename = f"screenshot_{int(time.time())}.png"
        filepath = os.path.join(screenshot_dir, filename)
        with open(filepath, "wb") as f:
            f.write(screenshot_bytes)
        return ToolResult(success=True, output={
            "path": filepath,
            "size": len(screenshot_bytes),
            "url": page.url,
        })
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_screenshot failed", logger=logger)


def _get_content(args: Dict[str, Any]) -> ToolResult:
    selector = args.get("selector", "")
    mode = args.get("mode", "text")
    try:
        page = BrowserManager.get_page()
        action_timeout = _tool_timeouts().browser_action_ms
        if mode == "accessibility":
            # Get accessibility tree snapshot
            snapshot = page.accessibility.snapshot()
            return ToolResult(success=True, output=snapshot)
        else:
            if selector:
                content = page.locator(selector).inner_text(timeout=action_timeout)
            else:
                content = page.locator("body").inner_text(timeout=action_timeout)
            # Limit content size
            return ToolResult(success=True, output=content[:10000])
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_get_content failed", logger=logger)


def _evaluate(args: Dict[str, Any]) -> ToolResult:
    js_code = args.get("js_code", "")
    if not js_code:
        return ToolResult(success=False, output=None, error="Missing 'js_code'")
    try:
        page = BrowserManager.get_page()
        result = page.evaluate(js_code)
        return ToolResult(success=True, output=result)
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_evaluate failed", logger=logger)


def _wait(args: Dict[str, Any]) -> ToolResult:
    selector = args.get("selector", "")
    default_timeout = _tool_timeouts().browser_wait_ms
    try:
        timeout = int(args.get("timeout", default_timeout))
    except (TypeError, ValueError):
        timeout = default_timeout
    try:
        page = BrowserManager.get_page()
        page.wait_for_selector(selector, timeout=timeout)
        return ToolResult(success=True, output=f"Element '{selector}' found")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_wait failed", logger=logger)


def _scroll(args: Dict[str, Any]) -> ToolResult:
    direction = args.get("direction", "down")
    amount = args.get("amount", 500)
    try:
        page = BrowserManager.get_page()
        delta = amount if direction == "down" else -amount
        page.mouse.wheel(0, delta)
        return ToolResult(success=True, output=f"Scrolled {direction} by {amount}px")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_scroll failed", logger=logger)


def _select(args: Dict[str, Any]) -> ToolResult:
    selector = args.get("selector", "")
    value = args.get("value", "")
    try:
        page = BrowserManager.get_page()
        page.select_option(selector, value, timeout=_tool_timeouts().browser_action_ms)
        return ToolResult(success=True, output=f"Selected '{value}' in {selector}")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_select failed", logger=logger)


def _close(args: Dict[str, Any]) -> ToolResult:
    try:
        BrowserManager.close()
        return ToolResult(success=True, output="Browser closed")
    except Exception as e:
        return ToolResult.from_exception(e, context="browser_close failed", logger=logger)
