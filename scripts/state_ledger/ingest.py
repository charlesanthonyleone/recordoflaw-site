#!/usr/bin/env python3
"""Refresh per-state enacted and signed laws.

Records are stored under ledger/states/{postal}.json and indexed by
ledger/states-meta.json. The same run stamps ledger/meta.json["state"]
and leaves the federal section of that file in place.

A pull upserts by state + session + official identifier and leaves every
older row in place. An empty or failed pull does not replace a state file.

    python3 scripts/state_ledger/ingest.py --adapters
    python3 scripts/state_ledger/ingest.py --state WA
    python3 scripts/state_ledger/ingest.py            # next incremental batch
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))

from adapters import ADAPTERS, fetch_openstates  # noqa: E402
from ledger_status import merge_meta, state_section  # noqa: E402
from catalog import BY_CODE, STATES, UNCONFIGURED_NOTE  # noqa: E402
from httputil import SourceError  # noqa: E402
from merge import make_record, merge_records  # noqa: E402

LEDGER = ROOT / "ledger"
STATE_DIR = LEDGER / "states"
META_PATH = LEDGER / "states-meta.json"
WORKFLOW = "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/state-ledger.yml"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path, default):
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def blank_meta():
    return {
        "kind": "state-ledger",
        "description": (
            "Enacted and signed state legislation, one file per state. "
            "Federal laws, executive orders, and amendments stay in their own files."
        ),
        "updated": None,
        "cursor": 0,
        "batchSize": 8,
        "order": [code for code, _name, _url, _adapter in STATES],
        "workflow": WORKFLOW,
        "openStates": {
            "used": False,
            "note": (
                "Set the OPENSTATES_API_KEY repository secret to refresh states "
                "that do not yet have a direct legislature parser. Each kept bill "
                "still links to the official source URL Open States recorded."
            ),
        },
        "recent": [],
        "states": {},
    }


def state_path(code):
    return STATE_DIR / f"{code.lower()}.json"


def select_codes(args, meta):
    order = meta["order"]
    if args.state:
        code = args.state.strip().upper()
        if code == "ALL":
            return list(order)
        if code not in BY_CODE:
            raise SystemExit(f"Unknown state code: {code}")
        return [code]
    if args.adapters:
        return [code for code, info in BY_CODE.items() if info["adapter"]]
    batch = args.batch or meta.get("batchSize") or 8
    start = int(meta.get("cursor") or 0) % len(order)
    return [order[(start + offset) % len(order)] for offset in range(batch)]


def apply_openstates(info, api_key, previous):
    updated_since = (previous or {}).get("openStatesSince")
    rows, pages = fetch_openstates(info["name"], api_key, updated_since=updated_since)
    records = []
    for row in rows:
        records.append(
            make_record(
                state=info["code"],
                session=row["session"],
                identifier=row["identifier"],
                title=row["title"],
                status=row["status"],
                statusLabel=row["statusLabel"],
                date=row["date"],
                dateKind=row["dateKind"],
                officialUrl=row["officialUrl"],
                sources=row["sources"],
            )
        )
    note = (
        f"Enacted or signed bills in the Open States feed for {info['name']} "
        f"(up to {pages} pages of recently updated bills"
        + (f" since {updated_since}" if updated_since else "")
        + "). A bill is kept only when Open States classifies an action as became-law "
        "or executive-signature and the bill has an official source URL."
    )
    return {
        "records": records,
        "sessions": [],
        "note": note,
        "adapter": "openstates",
        "coverage": "enacted",
        "openStatesSince": now_iso(),
    }


def sync_one(info, api_key, previous):
    if info["adapter"]:
        result = ADAPTERS[info["adapter"]]()
        result["adapter"] = info["adapter"]
        result["coverage"] = "enacted"
        return result
    if api_key:
        return apply_openstates(info, api_key, previous)
    return {
        "records": None,
        "sessions": [],
        "note": UNCONFIGURED_NOTE,
        "adapter": None,
        "coverage": "unconfigured",
        "checked": False,
    }


def rebuild_recent(limit=40):
    rows = []
    today = datetime.now(timezone.utc).date().isoformat()
    if not STATE_DIR.exists():
        return rows
    for path in STATE_DIR.glob("*.json"):
        payload = load_json(path, {})
        for record in payload.get("records") or []:
            # Delayed effective dates are real, but they are not "recent activity".
            if not record.get("date") or record["date"] > today:
                continue
            rows.append(
                {
                    "id": record["id"],
                    "state": record["state"],
                    "identifier": record.get("identifier"),
                    "title": record.get("title"),
                    "date": record.get("date"),
                    "dateKind": record.get("dateKind"),
                    "session": record.get("session"),
                    "officialUrl": record.get("officialUrl"),
                    "statusLabel": record.get("statusLabel"),
                }
            )
    rows.sort(key=lambda row: (row["date"], row["id"]), reverse=True)
    return rows[:limit]


def entry_for(info, previous):
    entry = {
        "name": info["name"],
        "officialUrl": info["officialUrl"],
        "adapter": info["adapter"],
        "coverage": "unconfigured" if not info["adapter"] else "enacted",
        "lastChecked": None,
        "lastSynced": None,
        "recordCount": 0,
        "sessions": [],
        "error": None,
        "note": UNCONFIGURED_NOTE if not info["adapter"] else None,
    }
    if previous:
        entry.update(previous)
    entry["name"] = info["name"]
    entry["officialUrl"] = info["officialUrl"]
    return entry


def main():
    parser = argparse.ArgumentParser(description="Refresh the per-state law ledger")
    parser.add_argument("--state", help="Postal code, or ALL")
    parser.add_argument("--adapters", action="store_true", help="Refresh every state that has a direct parser")
    parser.add_argument("--batch", type=int, help="Incremental batch size")
    args = parser.parse_args()

    meta = load_json(META_PATH, blank_meta())
    for key, value in blank_meta().items():
        meta.setdefault(key, value)
    meta["order"] = [code for code, _name, _url, _adapter in STATES]
    meta["workflow"] = WORKFLOW
    codes = select_codes(args, meta)
    api_key = (os.environ.get("OPENSTATES_API_KEY") or "").strip()
    meta["openStates"]["used"] = bool(api_key)
    print(f"refreshing {', '.join(codes)}")

    for code in codes:
        info = BY_CODE[code]
        previous = meta["states"].get(code) or {}
        entry = entry_for(info, previous)
        try:
            result = sync_one(info, api_key, previous)
        except (SourceError, OSError, ValueError) as err:
            entry["error"] = str(err)
            entry["lastChecked"] = now_iso()
            meta["states"][code] = entry
            print(f"  {code} ERROR {err}")
            continue
        entry["note"] = result.get("note") or entry.get("note")
        entry["adapter"] = result.get("adapter")
        entry["coverage"] = result.get("coverage") or entry["coverage"]
        entry["error"] = None
        if result.get("openStatesSince"):
            entry["openStatesSince"] = result["openStatesSince"]
        if result.get("records") is None:
            entry["recordCount"] = len((load_json(state_path(code), {}) or {}).get("records") or [])
            meta["states"][code] = entry
            print(f"  {code} unconfigured")
            continue
        existing = load_json(state_path(code), {}).get("records") or []
        merged = merge_records(existing, result["records"])
        payload = {
            "state": code,
            "name": info["name"],
            "officialUrl": info["officialUrl"],
            "adapter": result.get("adapter"),
            "sessions": result.get("sessions") or [],
            "records": merged,
        }
        write_json(state_path(code), payload)
        stamp = now_iso()
        entry["lastChecked"] = stamp
        entry["lastSynced"] = stamp
        entry["recordCount"] = len(merged)
        entry["sessions"] = [session["id"] for session in payload["sessions"]]
        meta["states"][code] = entry
        print(f"  {code} {len(result['records'])} incoming, {len(merged)} stored")

    if not args.state and not args.adapters:
        meta["cursor"] = (int(meta.get("cursor") or 0) + len(codes)) % len(meta["order"])
    elif args.batch and not args.state and not args.adapters:
        pass
    meta["batchSize"] = args.batch or meta.get("batchSize") or 8
    meta["recent"] = rebuild_recent()
    meta["updated"] = now_iso()
    # Keep a stable shell for states not visited in this run.
    for code, _name, _url, _adapter in STATES:
        meta["states"].setdefault(code, entry_for(BY_CODE[code], None))
    write_json(META_PATH, meta)
    shared_path = LEDGER / "meta.json"
    shared = merge_meta(load_json(shared_path, {}), state=state_section(meta))
    write_json(shared_path, shared)
    print(f"wrote {META_PATH.relative_to(ROOT)} recent={len(meta['recent'])}")
    print(f"wrote {shared_path.relative_to(ROOT)} state health={shared['state']['health']}")


if __name__ == "__main__":
    main()
