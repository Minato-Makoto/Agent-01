from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Iterator


class HttpTransport:
    """Raw HTTP transport + SSE event streaming with request rate limiting."""

    def __init__(self):
        self._base_url = ""
        self._api_key = ""
        self._request_timeout_s = 300
        self._http_error_body_chars = 1200
        self._max_requests_per_minute = 60
        self._request_timestamps: list[float] = []

    def configure(
        self,
        *,
        base_url: str,
        api_key: str,
        request_timeout_s: int,
        http_error_body_chars: int,
        max_requests_per_minute: int,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or ""
        self._request_timeout_s = int(request_timeout_s)
        self._http_error_body_chars = int(http_error_body_chars)
        self._max_requests_per_minute = int(max_requests_per_minute)

    def consume_rate_limit_slot(self) -> None:
        limit = int(self._max_requests_per_minute)
        if limit <= 0:
            return

        now = time.monotonic()
        cutoff = now - 60.0
        self._request_timestamps = [t for t in self._request_timestamps if t >= cutoff]
        if len(self._request_timestamps) >= limit:
            raise RuntimeError(
                f"Rate limit exceeded: more than {limit} LLM requests within 60 seconds."
            )
        self._request_timestamps.append(now)

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.consume_rate_limit_slot()
        url = f"{self._base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._request_timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSON response: {body[:300]}") from exc
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:self._http_error_body_chars]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc}")

    def stream_events(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        *,
        sse_data_prefix: str,
        sse_done_marker: str,
    ) -> Iterator[Dict[str, Any]]:
        self.consume_rate_limit_slot()
        url = f"{self._base_url}{endpoint}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._request_timeout_s) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line or not line.startswith(sse_data_prefix):
                        continue
                    data_str = line[len(sse_data_prefix) :]
                    if data_str == sse_done_marker:
                        break
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(chunk, dict):
                        yield chunk
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body[:self._http_error_body_chars]}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc}")

