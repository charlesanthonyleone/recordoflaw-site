"""Small HTTP client for official federal sources. Standard library only."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

USER_AGENT = "RecordOfLaw-federal-sync/1.0 (+https://recordoflaw.com/wiki/ledger)"


class FetchError(Exception):
    pass


def get(url: str, headers: dict | None = None, timeout: int = 45, attempts: int = 4) -> tuple[int, bytes]:
    """GET a URL. Retries timeouts, 429s, and 5xx. Returns (status, body)."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json, application/xml, text/xml, text/html, */*"}
    if headers:
        hdrs.update(headers)
    last_error = "unknown error"
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read() if exc.fp else b""
            if exc.code == 429 or exc.code >= 500:
                last_error = f"HTTP {exc.code}"
                time.sleep(min(8, 2 ** attempt))
                continue
            return exc.code, body
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc.reason if isinstance(exc, urllib.error.URLError) else exc)
            time.sleep(min(8, 2 ** attempt))
    raise FetchError(f"{url.split('?', 1)[0]} failed after {attempts} attempts: {last_error}")
