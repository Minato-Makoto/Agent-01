import threading
import urllib.request

from builtin_tools import browser_tools, photoshop_tools, sys_ops, web_ops, web_search


class _FakeResponse:
    def __init__(self, body: str, status: int = 200, headers=None):
        self._body = body.encode("utf-8")
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


def test_web_search_uses_env_timeout(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["timeout"] = timeout
        html = '<a class="result__a" href="https://example.com">Example</a>'
        return _FakeResponse(html)

    monkeypatch.setenv("TOOL_TIMEOUT_WEB_SEARCH_S", "9")
    monkeypatch.setattr(web_search.urllib.request, "urlopen", fake_urlopen)

    results = web_search._search_duckduckgo("example", 1)
    assert captured["timeout"] == 9
    assert len(results) == 1


def test_web_ops_uses_env_timeout(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=0):
        captured["timeout"] = timeout
        return _FakeResponse("ok", status=200, headers={"Content-Type": "text/plain"})

    monkeypatch.setenv("TOOL_TIMEOUT_WEB_REQUEST_S", "7")
    monkeypatch.setattr(web_ops, "_validate_url", lambda url, allow_private_network=False: (True, ""))
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    result = web_ops._http_request({"url": "https://example.com"})
    assert result.success is True
    assert captured["timeout"] == 7


def test_browser_wait_uses_env_timeout(monkeypatch):
    captured = {}

    class _Page:
        def wait_for_selector(self, selector, timeout=None):
            captured["timeout"] = timeout

    monkeypatch.setenv("TOOL_TIMEOUT_BROWSER_WAIT_MS", "4321")
    monkeypatch.setattr(browser_tools.BrowserManager, "get_page", staticmethod(lambda: _Page()))

    result = browser_tools._wait({"selector": "#app"})
    assert result.success is True
    assert captured["timeout"] == 4321


def test_browser_navigate_and_click_use_env_timeouts(monkeypatch):
    captured = {}

    class _ClickTarget:
        def click(self, timeout=None):
            captured["click_timeout"] = timeout

    class _TextQuery:
        first = _ClickTarget()

    class _Page:
        url = "https://example.com"

        def title(self):
            return "Example"

        def goto(self, url, wait_until=None, timeout=None):
            captured["nav_timeout"] = timeout

        def click(self, selector, timeout=None):
            captured["click_timeout"] = timeout

        def get_by_text(self, text):
            return _TextQuery()

    monkeypatch.setenv("TOOL_TIMEOUT_BROWSER_NAV_MS", "21000")
    monkeypatch.setenv("TOOL_TIMEOUT_BROWSER_ACTION_MS", "3300")
    monkeypatch.setattr(browser_tools.BrowserManager, "get_page", staticmethod(lambda: _Page()))

    nav_result = browser_tools._navigate({"url": "https://example.com"})
    click_result = browser_tools._click({"selector": "#btn"})
    assert nav_result.success is True
    assert click_result.success is True
    assert captured["nav_timeout"] == 21000
    assert captured["click_timeout"] == 3300


def test_photoshop_client_uses_env_timeout(monkeypatch):
    captured = {}

    class _FakeEvent:
        def set(self):
            return None

        def wait(self, timeout=None):
            captured["timeout"] = timeout
            return False

    class _FakeClient:
        def emit(self, event, payload):
            return None

        def on(self, event, handler):
            return None

    monkeypatch.setenv("TOOL_TIMEOUT_PHOTOSHOP_S", "12")
    monkeypatch.setattr(threading, "Event", _FakeEvent)
    monkeypatch.setattr(photoshop_tools.PhotoshopClient, "_connected", True)
    monkeypatch.setattr(photoshop_tools.PhotoshopClient, "_client", _FakeClient())

    result = photoshop_tools.PhotoshopClient.send("ping", {})
    assert result.success is False
    assert "12s" in result.error
    assert captured["timeout"] == 12


def test_process_list_uses_env_timeout(monkeypatch):
    captured = {}

    class _RunResult:
        stdout = '"python.exe","123","Console","1","10 K"\n'

    def fake_run(*args, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        return _RunResult()

    monkeypatch.setenv("TOOL_TIMEOUT_PROCESS_LIST_S", "7")
    monkeypatch.setattr(sys_ops.sys, "platform", "win32")
    monkeypatch.setattr(sys_ops.subprocess, "run", fake_run)

    result = sys_ops._process_list({})
    assert result.success is True
    assert captured["timeout"] == 7
