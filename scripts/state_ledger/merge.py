"""Merge state ledger records by official id. A refresh never deletes history."""

import re
from html import unescape

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def clean(text):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", unescape(str(text))).strip()


def record_id(state, session, identifier):
    return f"{state}:{clean(session)}:{clean(identifier)}"


def iso_date(value):
    """Return YYYY-MM-DD when the source states a calendar date, else None."""
    if not value:
        return None
    text = clean(value)
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    if match:
        month, day, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
        return None
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s+(\d{4})",
        text,
        re.I,
    )
    if match:
        month = MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        year = int(match.group(3))
        if 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def make_record(**fields):
    record = {
        "id": record_id(fields["state"], fields["session"], fields["identifier"]),
        "state": fields["state"],
        "identifier": clean(fields["identifier"]),
        "session": clean(fields["session"]),
        "title": clean(fields.get("title")) or None,
        "status": fields["status"],
        "statusLabel": clean(fields["statusLabel"]),
        "date": fields.get("date"),
        "dateKind": fields.get("dateKind"),
        "chapter": clean(fields.get("chapter")) or None,
        "officialUrl": fields["officialUrl"],
        "sources": fields["sources"],
    }
    return {key: value for key, value in record.items() if value not in (None, "", [])}


def sort_records(records):
    def key(record):
        return (record.get("date") or "", record["id"])

    return sorted(records, key=key, reverse=True)


def merge_records(existing, incoming):
    """Upsert incoming rows. Records absent from this pull are kept."""
    merged = {record["id"]: record for record in existing or []}
    for record in incoming or []:
        merged[record["id"]] = record
    return sort_records(merged.values())


def bill_spaced(token):
    """SF1552 -> SF 1552. Leading zeros on the number are not significant."""
    token = clean(token)
    match = re.fullmatch(r"([A-Za-z]+)\s*(\d+)([A-Za-z]*)", token)
    if not match:
        return token
    return f"{match.group(1).upper()} {int(match.group(2))}{match.group(3)}"
