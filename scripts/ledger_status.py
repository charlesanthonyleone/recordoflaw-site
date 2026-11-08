"""Shared ledger/meta.json contract for the federal and state ingests.

Federal sync and state ingest both write this file. Each run replaces only
its own section and leaves the other section in place, so the site can read
one status document for both ledgers.
"""

from __future__ import annotations


def merge_meta(existing, *, federal=None, state=None) -> dict:
    """Keep whichever section this run is not replacing."""
    meta: dict = {"schema": 1}
    if isinstance(existing, dict):
        if isinstance(existing.get("federal"), dict):
            meta["federal"] = existing["federal"]
        if isinstance(existing.get("state"), dict):
            meta["state"] = existing["state"]
    if federal is not None:
        meta["federal"] = federal
    if state is not None:
        meta["state"] = state
    return meta


def state_section(state_meta: dict) -> dict:
    """Compact state stamp stored beside the federal section."""
    states = state_meta.get("states") if isinstance(state_meta.get("states"), dict) else {}
    failed = sorted(
        code
        for code, row in states.items()
        if isinstance(row, dict) and row.get("error")
    )
    covered = sorted(
        code
        for code, row in states.items()
        if isinstance(row, dict) and int(row.get("recordCount") or 0) > 0
    )
    order = state_meta.get("order") if isinstance(state_meta.get("order"), list) else []
    record_count = 0
    for row in states.values():
        if isinstance(row, dict):
            record_count += int(row.get("recordCount") or 0)
    return {
        "lastChecked": state_meta.get("updated"),
        "recordCount": record_count,
        "coveredCount": len(covered),
        "failed": failed,
        "unconfiguredCount": len([code for code in order if code not in covered and code not in failed]),
        "workflow": state_meta.get("workflow"),
        "index": "/ledger/states-meta.json",
        "health": "down" if failed else "ok",
        "openStates": state_meta.get("openStates") if isinstance(state_meta.get("openStates"), dict) else {},
    }
