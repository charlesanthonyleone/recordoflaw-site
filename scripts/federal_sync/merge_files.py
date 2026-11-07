"""Upsert federal records. Historical rows are kept; nothing is deleted."""

from __future__ import annotations

import json
from datetime import date


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def dump_compact(path: str, payload: dict) -> None:
    text = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def dump_pretty(path: str, payload: dict) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def merge_records(existing: list[dict], incoming: list[dict], checked: str) -> tuple[list[dict], int, int]:
    """Insert or update by id. Records absent from this batch stay."""
    by_id: dict[str, dict] = {}
    for record in existing:
        if isinstance(record, dict) and record.get("id"):
            by_id[record["id"]] = record
    inserted = updated = 0
    for record in incoming:
        if not record or not record.get("id"):
            continue
        stamped = dict(record)
        stamped["checked"] = checked
        previous = by_id.get(record["id"])
        if previous is None:
            by_id[record["id"]] = stamped
            inserted += 1
            continue
        old_material = {key: value for key, value in previous.items() if key != "checked"}
        new_material = {key: value for key, value in stamped.items() if key != "checked"}
        if old_material != new_material:
            updated += 1
        by_id[record["id"]] = stamped
    records = list(by_id.values())
    records.sort(key=lambda record: (record.get("date") or "", record.get("id") or ""), reverse=True)
    # date descending, id ascending inside the same date
    records.sort(key=lambda record: record.get("id") or "")
    records.sort(key=lambda record: record.get("date") or "", reverse=True)
    return records, inserted, updated


def material_signature(records: list[dict]) -> list[tuple]:
    signature = []
    for record in records:
        signature.append(tuple(sorted((key, _freeze(value)) for key, value in record.items() if key != "checked")))
    return signature


def _freeze(value):
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _law_sort_key(row: list):
    number = int(str(row[2]).split("-")[1])
    return (-int(row[0]), 0 if row[1] == "priv" else 1, -number)


def upsert_laws(laws: dict, new_rows: list[list], generated: str) -> int:
    """Append enacted laws that are not already present. Never edits an existing row."""
    rows = laws.setdefault("rows", [])
    seen = {(row[0], row[1], row[2]) for row in rows}
    added = 0
    for row in new_rows:
        key = (row[0], row[1], row[2])
        if key in seen:
            continue
        rows.append(row)
        seen.add(key)
        congress_key = str(row[0])
        laws.setdefault("congresses", {})
        laws["congresses"][congress_key] = int(laws["congresses"].get(congress_key, 0)) + 1
        added += 1
    if added:
        rows.sort(key=_law_sort_key)
        laws["generated"] = generated
    return added


def upsert_executive_orders(eos: dict, updates: list[dict], generated: str) -> int:
    """Update an order in place by EO number, or insert a new numbered order. Never drops rows."""
    rows = eos.setdefault("rows", [])
    index = {}
    for position, row in enumerate(rows):
        if row and row[0]:
            index[str(row[0])] = position
    changed = 0
    fresh = []
    for update in updates:
        number = str(update["number"])
        if number in index:
            current = list(rows[index[number]])
            while len(current) < 7:
                current.append(None)
            if update.get("signing_date"):
                current[1] = update["signing_date"]
            if update.get("title"):
                current[2] = update["title"]
            if update.get("president"):
                current[3] = update["president"]
            if update.get("citation"):
                current[4] = update["citation"]
            if update.get("url"):
                current[5] = update["url"]
            if current != list(rows[index[number]]) + [None] * (7 - len(rows[index[number]])):
                # Compare against the original padded only when the stored row is shorter.
                original = list(rows[index[number]])
                candidate = current[: len(original)] if len(original) >= 7 else current
                if candidate != original:
                    rows[index[number]] = candidate if len(original) >= 7 else current
                    changed += 1
            continue
        if not update.get("signing_date") or not update.get("title") or not update.get("url"):
            continue
        fresh.append([
            number,
            update["signing_date"],
            update["title"],
            update.get("president"),
            update.get("citation"),
            update["url"],
            None,
        ])
    for row in sorted(fresh, key=lambda item: int(item[0])):
        placed = False
        for position, existing in enumerate(rows):
            if existing and existing[0] and str(existing[0]).isdigit() and int(existing[0]) < int(row[0]):
                rows.insert(position, row)
                placed = True
                break
        if not placed:
            rows.insert(0, row)
        changed += 1
    if changed:
        eos["generated"] = generated
    return changed


def law_index(laws: dict) -> dict[tuple, list]:
    indexed = {}
    for row in laws.get("rows") or []:
        indexed[(row[0], row[1], row[2])] = row
    return indexed


def generated_day(today: date | None = None) -> str:
    return (today or date.today()).isoformat()
