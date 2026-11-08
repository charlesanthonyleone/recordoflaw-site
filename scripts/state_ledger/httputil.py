"""Small HTTP helper. Standard library only, so the GitHub Action needs no install."""

import json
import time
import urllib.error
import urllib.request

UA = "RecordOfLaw-state-ledger/1.0 (+https://recordoflaw.com)"


class SourceError(RuntimeError):
    pass


def get_bytes(url, timeout=45, headers=None, retries=3, data=None, method=None):
    hdrs = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    body = data
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if len(raw) > 25_000_000:
                    raise SourceError(f"response too large: {url}")
                return resp.status, resp.headers, raw
        except urllib.error.HTTPError as err:
            last = err
            if err.code == 404:
                raise
            if err.code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            detail = ""
            try:
                detail = err.read(240).decode("utf-8", "replace")
            except Exception:
                pass
            raise SourceError(f"HTTP {err.code} for {url} {detail}") from err
        except urllib.error.URLError as err:
            last = err
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise SourceError(f"request failed for {url}: {err}") from err
    raise SourceError(f"request failed for {url}: {last}")


def decode(headers, raw):
    charset = "utf-8"
    ctype = headers.get("content-type") or ""
    marker = "charset="
    if marker in ctype.lower():
        charset = ctype.lower().split(marker, 1)[1].split(";", 1)[0].strip() or charset
    try:
        return raw.decode(charset, "replace")
    except LookupError:
        return raw.decode("utf-8", "replace")


def get_text(url, timeout=45, headers=None, optional=False):
    try:
        status, hdrs, raw = get_bytes(url, timeout=timeout, headers=headers)
    except urllib.error.HTTPError as err:
        if optional and err.code == 404:
            return None
        raise
    if status != 200:
        raise SourceError(f"HTTP {status} for {url}")
    return decode(hdrs, raw)


def get_json(url, timeout=45, headers=None, data=None):
    status, hdrs, raw = get_bytes(url, timeout=timeout, headers=headers, data=data)
    if status != 200:
        raise SourceError(f"HTTP {status} for {url}")
    try:
        return json.loads(decode(hdrs, raw))
    except json.JSONDecodeError as err:
        raise SourceError(f"invalid JSON from {url}") from err
