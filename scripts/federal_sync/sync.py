#!/usr/bin/env python3
"""Sync present-tense federal ledger records from official sources.

Merges by official id. Historical rows in ledger/laws.json and ledger/eos.json
are kept. Records already in ledger/federal-live.json are kept when a later
run does not see them.

Optional environment:
  CONGRESS_API_KEY       Congress.gov API (bills and votes). GovInfo and the
                         House Clerk are used whether or not this is set.
  COURTLISTENER_TOKEN    CourtListener token for federal appellate opinions.
                         Supreme Court slip opinions always come from
                         supremecourt.gov.
  FEDERAL_SYNC_FR_DAYS   Federal Register publication window (default 21).
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch import FetchError, get
from merge_files import (
    dump_compact,
    dump_pretty,
    generated_day,
    law_index,
    load_json,
    material_signature,
    merge_records,
    upsert_executive_orders,
    upsert_laws,
)
from normalize import (
    accept_record,
    bill_record,
    congress_bill_record,
    congress_vote_record,
    courtlistener_record,
    executive_order_update,
    federal_register_record,
    law_row_from_mods,
    parse_bill_guid,
    parse_house_vote,
    parse_mods,
    parse_plaw_guid,
    parse_rss_items,
    parse_slip_opinions,
    plaw_record_from_ledger,
    plaw_record_from_mods,
    scotus_term_years,
    utc_now,
)

LEDGER = ROOT / "ledger"
LIVE_PATH = LEDGER / "federal-live.json"
META_PATH = LEDGER / "meta.json"
LAWS_PATH = LEDGER / "laws.json"
EOS_PATH = LEDGER / "eos.json"
WORKFLOW_URL = "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/federal-sync.yml"

FR_FIELDS = [
    "title",
    "type",
    "subtype",
    "document_number",
    "executive_order_number",
    "proclamation_number",
    "publication_date",
    "signing_date",
    "president",
    "citation",
    "html_url",
    "pdf_url",
    "agencies",
    "abstract",
]


def log(message: str) -> None:
    print(message, flush=True)


def congress_of(today: date) -> tuple[int, int]:
    congress = ((today.year - 1789) // 2) + 1
    session = ((today.year - 1789) % 2) + 1
    return congress, session


def _json_bytes(body: bytes):
    return json.loads(body.decode("utf-8"))


def fetch_federal_register(since: str, extra: list[tuple[str, str]] | None = None, page_cap: int = 30) -> tuple[list[dict], bool]:
    params: list[tuple[str, str]] = [("order", "newest"), ("conditions[publication_date][gte]", since)]
    for field in FR_FIELDS:
        params.append(("fields[]", field))
    if extra:
        params.extend(extra)
    documents = []
    truncated = False
    for page in range(1, page_cap + 1):
        query = params + [("per_page", "100"), ("page", str(page))]
        url = "https://www.federalregister.gov/api/v1/documents.json?" + urlencode(query)
        status, body = get(url)
        if status != 200:
            raise FetchError(f"Federal Register HTTP {status}")
        payload = _json_bytes(body)
        batch = payload.get("results") or []
        if not isinstance(batch, list):
            raise FetchError("Federal Register response had no results list")
        documents.extend(item for item in batch if isinstance(item, dict))
        time.sleep(0.12)
        if len(batch) < 100:
            return documents, False
    return documents, True


def source_federal_register(today: date) -> dict:
    window = int(os.environ.get("FEDERAL_SYNC_FR_DAYS") or "21")
    since = (today - timedelta(days=window)).isoformat()
    eo_since = (today - timedelta(days=180)).isoformat()
    info = {
        "id": "federal-register",
        "label": "Federal Register API",
        "url": "https://www.federalregister.gov/developers/documentation/api/v1",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": (
            f"Rules, proposed rules, notices, and presidential documents published "
            f"on or after {since}. Executive orders published on or after {eo_since} "
            f"are also merged into ledger/eos.json by EO number."
        ),
        "records": [],
        "eoUpdates": [],
    }
    try:
        type_params = [
            ("conditions[type][]", "RULE"),
            ("conditions[type][]", "PRORULE"),
            ("conditions[type][]", "NOTICE"),
            ("conditions[type][]", "PRESDOCU"),
        ]
        documents, truncated = fetch_federal_register(since, type_params)
        eo_docs, _ = fetch_federal_register(eo_since, [
            ("conditions[type][]", "PRESDOCU"),
            ("conditions[presidential_document_type][]", "executive_order"),
        ], page_cap=10)
        seen = set()
        combined = []
        for doc in documents + eo_docs:
            number = str(doc.get("document_number") or "")
            if number and number in seen:
                continue
            if number:
                seen.add(number)
            combined.append(doc)
        records = []
        updates = []
        for doc in combined:
            record = federal_register_record(doc)
            if record:
                records.append(record)
            update = executive_order_update(doc)
            if update:
                updates.append(update)
        info.update(ok=True, fetched=len(combined), upserted=len(records), records=records, eoUpdates=updates)
        if truncated:
            info["note"] += " The Federal Register window hit the page cap; older pages in the window were not added on this run."
    except (FetchError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        info["error"] = str(exc)
    return info


def source_public_laws(laws: dict) -> dict:
    info = {
        "id": "govinfo-plaw",
        "label": "GovInfo public and private laws",
        "url": "https://www.govinfo.gov/rss/plaw.xml",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": "Newest slip laws on the GovInfo public-and-private-law RSS. Enactment dates come from the existing ledger or from GovInfo MODS dateIssued. RSS publication time is not used as the enactment date.",
        "records": [],
        "lawRows": [],
        "datesFilled": 0,
    }
    try:
        status, body = get("https://www.govinfo.gov/rss/plaw.xml")
        if status != 200:
            raise FetchError(f"GovInfo PLAW RSS HTTP {status}")
        items = parse_rss_items(body)
        indexed = law_index(laws)
        records = []
        new_rows = []
        for item in items:
            package = parse_plaw_guid(item["guid"])
            if not package:
                continue
            key = (package["congress"], package["lawKind"], package["lawNumber"])
            existing = indexed.get(key)
            if existing and existing[6]:
                record = plaw_record_from_ledger(item, existing)
                if record:
                    records.append(record)
                continue
            status, mods_body = get(f"https://www.govinfo.gov/metadata/pkg/{package['packageId']}/mods.xml")
            time.sleep(0.15)
            if status != 200:
                log(f"  skipped {package['packageId']}: MODS HTTP {status}")
                continue
            try:
                mods = parse_mods(mods_body)
            except Exception as exc:  # noqa: BLE001 — one bad package should not stop the feed
                log(f"  skipped {package['packageId']}: {exc}")
                continue
            row = law_row_from_mods(package, mods)
            if existing and not existing[6] and row:
                # Fill a missing enactment date only. Title and bill fields stay as stored.
                existing[6] = row[6]
                info["datesFilled"] += 1
                record = plaw_record_from_ledger(item, existing)
            elif row:
                new_rows.append(row)
                indexed[key] = row
                record = plaw_record_from_mods(item, package, mods, row)
            else:
                record = None
                log(f"  skipped {package['packageId']}: MODS had no verified enactment date, title, and bill")
            if record:
                records.append(record)
        info.update(ok=True, fetched=len(items), upserted=len(records), records=records, lawRows=new_rows)
    except (FetchError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        info["error"] = str(exc)
    return info


def source_bills_govinfo() -> dict:
    info = {
        "id": "govinfo-bills",
        "label": "GovInfo congressional bills",
        "url": "https://www.govinfo.gov/rss/bills.xml",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": "Newest bill versions posted to GovInfo. The date is when GovInfo published that version, not the date of introduction.",
        "records": [],
    }
    try:
        status, body = get("https://www.govinfo.gov/rss/bills.xml")
        if status != 200:
            raise FetchError(f"GovInfo bills RSS HTTP {status}")
        items = parse_rss_items(body)
        records = []
        for item in items:
            if not parse_bill_guid(item["guid"]):
                continue
            record = bill_record(item)
            if record:
                records.append(record)
        info.update(ok=True, fetched=len(items), upserted=len(records), records=records)
    except (FetchError, KeyError, TypeError, ValueError) as exc:
        info["error"] = str(exc)
    return info


def _congress_get(path: str, key: str, params: dict) -> dict:
    query = dict(params)
    query["api_key"] = key
    query["format"] = "json"
    url = "https://api.congress.gov/v3" + path + "?" + urlencode(query)
    try:
        status, body = get(url)
    except FetchError as exc:
        raise FetchError(str(exc).replace(key, "[redacted]")) from exc
    if status != 200:
        raise FetchError(f"Congress.gov {path} HTTP {status}")
    return _json_bytes(body)


def source_congress_api(today: date) -> dict:
    key = (os.environ.get("CONGRESS_API_KEY") or "").strip()
    info = {
        "id": "congress-gov",
        "label": "Congress.gov API",
        "url": "https://api.congress.gov/",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": "",
        "records": [],
        "skipped": False,
    }
    if not key:
        info.update(ok=True, skipped=True, note="CONGRESS_API_KEY is not set. Bills come from GovInfo and House votes come from the Clerk. Senate roll calls are not fetched without this key.")
        return info
    congress, session = congress_of(today)
    try:
        records = []
        fetched = 0
        try:
            payload = _congress_get(f"/bill/{congress}", key, {"limit": "50", "sort": "updateDate+desc"})
        except FetchError:
            payload = _congress_get(f"/bill/{congress}", key, {"limit": "50"})
        bills = payload.get("bills") if isinstance(payload, dict) else None
        if not isinstance(bills, list):
            raise FetchError("Congress.gov bill list had no bills array")
        fetched += len(bills)
        cutoff = (today - timedelta(days=60)).isoformat()
        for bill in bills:
            record = congress_bill_record(bill)
            if record and record["date"] >= cutoff:
                records.append(record)
        for chamber in ("house", "senate"):
            try:
                vote_payload = _congress_get(f"/{chamber}-vote/{congress}/{session}", key, {"limit": "20"})
            except FetchError as exc:
                log(f"  Congress.gov {chamber} votes: {exc}")
                continue
            vote_list = None
            if isinstance(vote_payload, dict):
                for candidate in ("votes", "houseVotes", "senateVotes", "results"):
                    if isinstance(vote_payload.get(candidate), list):
                        vote_list = vote_payload[candidate]
                        break
            if not vote_list:
                continue
            fetched += len(vote_list)
            for vote in vote_list:
                record = congress_vote_record(vote, chamber)
                if record:
                    records.append(record)
        note = (
            f"Latest bills of the {congress}th Congress with a Congress.gov latest-action date on or after {cutoff}. "
            "Votes are included only when the API payload carries a public https URL."
        )
        info.update(ok=True, fetched=fetched, upserted=len(records), records=records, note=note)
    except (FetchError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        message = str(exc).replace(key, "[redacted]")
        info["error"] = message
        info["note"] = "Congress.gov request failed. GovInfo bills and House Clerk votes are still used."
    return info


def _roll_exists(year: int, number: int) -> bool:
    status, body = get(f"https://clerk.house.gov/evs/{year}/roll{number:03d}.xml")
    return status == 200 and b"<rollcall-vote>" in body


def latest_roll(year: int, cap: int = 4000) -> int:
    if not _roll_exists(year, 1):
        return 0
    lo = 1
    hi = 1
    while hi < cap and _roll_exists(year, hi):
        lo = hi
        hi = min(cap, hi * 2)
        if hi == lo:
            break
    if not _roll_exists(year, hi):
        right = hi - 1
    else:
        return hi
    left = lo
    while left < right:
        mid = (left + right + 1) // 2
        if _roll_exists(year, mid):
            left = mid
        else:
            right = mid - 1
    return left


def source_house_votes(today: date) -> dict:
    info = {
        "id": "house-clerk",
        "label": "Office of the Clerk, U.S. House of Representatives",
        "url": "https://clerk.house.gov/Votes",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": "Latest House roll calls from the Clerk's roll-call XML. Totals are the Clerk's yea/nay totals.",
        "records": [],
    }
    try:
        year = today.year
        latest = latest_roll(year)
        if latest == 0:
            year -= 1
            latest = latest_roll(year)
        if latest == 0:
            info.update(ok=True, note=info["note"] + " No roll calls were published for this year or the previous year.")
            return info
        records = []
        start = max(1, latest - 39)
        for number in range(latest, start - 1, -1):
            status, body = get(f"https://clerk.house.gov/evs/{year}/roll{number:03d}.xml")
            time.sleep(0.05)
            if status != 200 or b"<rollcall-vote>" not in body:
                continue
            record = parse_house_vote(body, year)
            if record:
                records.append(record)
        info.update(
            ok=True,
            fetched=latest,
            upserted=len(records),
            records=records,
            note=info["note"] + f" Checked calendar year {year}; latest roll call was {latest}.",
        )
    except (FetchError, TypeError, ValueError) as exc:
        info["error"] = str(exc)
    return info


def source_scotus(today: date) -> dict:
    years = scotus_term_years(today)
    info = {
        "id": "supremecourt-gov",
        "label": "Supreme Court slip opinions",
        "url": "https://www.supremecourt.gov/opinions/opinions.aspx",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": f"Official slip-opinion tables for October Terms {years[0]} and {years[1]}. The summary text is the Court's own listing, stored only when the page provides it.",
        "records": [],
    }
    errors = []
    records = []
    fetched = 0
    ok_pages = 0
    for year in years:
        slug = str(year % 100)
        url = f"https://www.supremecourt.gov/opinions/slipopinion/{slug}"
        try:
            status, body = get(url)
            if status != 200:
                errors.append(f"OT {year} HTTP {status}")
                continue
            page_records = parse_slip_opinions(body.decode("utf-8", "replace"), year)
            fetched += len(page_records)
            records.extend(record for record in page_records if record)
            ok_pages += 1
        except (FetchError, TypeError, ValueError) as exc:
            errors.append(f"OT {year}: {exc}")
    if ok_pages:
        info.update(ok=True, fetched=fetched, upserted=len(records), records=records)
        if errors:
            info["note"] += " Partial: " + "; ".join(errors)
    else:
        info["error"] = "; ".join(errors) or "Supreme Court slip opinions could not be read"
    return info


def source_courtlistener(today: date) -> dict:
    token = (os.environ.get("COURTLISTENER_TOKEN") or "").strip()
    since = (today - timedelta(days=45)).isoformat()
    info = {
        "id": "courtlistener",
        "label": "CourtListener",
        "url": "https://www.courtlistener.com/help/api/rest/",
        "ok": False,
        "fetched": 0,
        "upserted": 0,
        "error": None,
        "note": "",
        "records": [],
        "skipped": False,
    }
    if not token:
        info.update(
            ok=True,
            skipped=True,
            note="COURTLISTENER_TOKEN is not set. Supreme Court slip opinions still sync from supremecourt.gov. Set the token to add federal appellate opinions.",
        )
        return info
    try:
        query = urlencode({
            "type": "o",
            "order_by": "dateFiled desc",
            "stat_Precedential": "on",
            "filed_after": since,
        })
        status, body = get(
            "https://www.courtlistener.com/api/rest/v4/search/?" + query,
            headers={"Authorization": f"Token {token}"},
        )
        if status != 200:
            raise FetchError(f"CourtListener HTTP {status}")
        payload = _json_bytes(body)
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise FetchError("CourtListener response had no results list")
        records = []
        for result in results[:80]:
            record = courtlistener_record(result)
            if record and record["date"] >= since:
                records.append(record)
        info.update(
            ok=True,
            fetched=len(results),
            upserted=len(records),
            records=records,
            note=f"Precedential federal opinions filed on or after {since}, excluding the Supreme Court (those come from supremecourt.gov).",
        )
    except (FetchError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        info["error"] = str(exc).replace(token, "[redacted]")
    return info


def empty_live() -> dict:
    return {"schema": 1, "jurisdiction": "federal", "updated": None, "records": []}


def write_outputs(checked: str, sources: list[dict], laws_added: int, eos_changed: int, live_existed: bool) -> None:
    existing_records = []
    previous_changed = None
    if LIVE_PATH.exists():
        current = load_json(LIVE_PATH)
        existing_records = current.get("records") or []
        previous_changed = (load_json(META_PATH).get("federal") or {}).get("lastChanged") if META_PATH.exists() else None
    incoming = []
    for source in sources:
        incoming.extend(source.get("records") or [])
    merged, inserted, updated = merge_records(existing_records, incoming, checked)
    signature_changed = material_signature(existing_records) != material_signature(merged) or not live_existed
    live = {
        "schema": 1,
        "jurisdiction": "federal",
        "updated": checked,
        "description": "Present federal activity merged by official id from Congress, the Federal Register, and the courts. Historical ledger files are not replaced by this file.",
        "records": merged,
    }
    by_branch = {"legislative": 0, "executive": 0, "judicial": 0}
    by_kind: dict[str, int] = {}
    for record in merged:
        branch = record.get("branch")
        if branch in by_branch:
            by_branch[branch] += 1
        by_kind[record.get("kind") or "unknown"] = by_kind.get(record.get("kind") or "unknown", 0) + 1
    public_meta = []
    for source in sources:
        public_meta.append({
            "id": source["id"],
            "label": source["label"],
            "url": source["url"],
            "ok": bool(source["ok"]),
            "skipped": bool(source.get("skipped")),
            "checked": checked,
            "fetched": source.get("fetched") or 0,
            "upserted": source.get("upserted") or 0,
            "error": source.get("error"),
            "note": source.get("note") or "",
        })
    meta = {
        "federal": {
            "lastChecked": checked,
            "lastChanged": checked if signature_changed or laws_added or eos_changed else previous_changed or checked,
            "recordCount": len(merged),
            "inserted": inserted,
            "updated": updated,
            "lawsAdded": laws_added,
            "executiveOrdersChanged": eos_changed,
            "byBranch": by_branch,
            "byKind": by_kind,
            "workflow": WORKFLOW_URL,
            "sources": public_meta,
        }
    }
    dump_pretty(LIVE_PATH, live)
    dump_pretty(META_PATH, meta)
    log(f"federal-live.json records={len(merged)} inserted={inserted} updated={updated}")
    log(f"laws added={laws_added} executive orders changed={eos_changed}")


def required_ok(sources: list[dict]) -> bool:
    by_id = {source["id"]: source for source in sources}
    needed = ["federal-register", "govinfo-plaw", "house-clerk", "supremecourt-gov"]
    if not all(by_id.get(item, {}).get("ok") for item in needed):
        return False
    bills_ok = by_id.get("govinfo-bills", {}).get("ok") or (
        by_id.get("congress-gov", {}).get("ok") and not by_id.get("congress-gov", {}).get("skipped") and (by_id.get("congress-gov", {}).get("upserted") or 0) > 0
    )
    # GovInfo bills are always attempted unless Congress.gov returned bills.
    return bool(bills_ok or by_id.get("govinfo-bills", {}).get("ok"))


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    today = datetime.now(timezone.utc).date()
    checked = utc_now()
    log(f"Federal sync {checked}")
    laws = load_json(LAWS_PATH)
    eos = load_json(EOS_PATH)
    law_rows_before = len(laws.get("rows") or [])
    eo_rows_before = len(eos.get("rows") or [])

    sources = [source_federal_register(today)]
    log(f"federal-register ok={sources[-1]['ok']} fetched={sources[-1]['fetched']} records={sources[-1]['upserted']} error={sources[-1]['error']}")

    congress = source_congress_api(today)
    sources.append(congress)
    log(f"congress-gov ok={congress['ok']} skipped={congress.get('skipped')} records={congress['upserted']} error={congress['error']}")

    if congress.get("ok") and not congress.get("skipped") and congress.get("upserted"):
        bills = {
            "id": "govinfo-bills",
            "label": "GovInfo congressional bills",
            "url": "https://www.govinfo.gov/rss/bills.xml",
            "ok": True,
            "skipped": True,
            "fetched": 0,
            "upserted": 0,
            "error": None,
            "note": "Skipped this run because Congress.gov returned bill records.",
            "records": [],
        }
    else:
        bills = source_bills_govinfo()
    sources.append(bills)
    log(f"govinfo-bills ok={bills['ok']} records={bills['upserted']} error={bills['error']}")

    plaw = source_public_laws(laws)
    sources.append(plaw)
    log(f"govinfo-plaw ok={plaw['ok']} records={plaw['upserted']} newLaws={len(plaw.get('lawRows') or [])} error={plaw['error']}")

    house = source_house_votes(today)
    sources.append(house)
    log(f"house-clerk ok={house['ok']} records={house['upserted']} error={house['error']}")

    scotus = source_scotus(today)
    sources.append(scotus)
    log(f"supremecourt ok={scotus['ok']} records={scotus['upserted']} error={scotus['error']}")

    opinions = source_courtlistener(today)
    sources.append(opinions)
    log(f"courtlistener ok={opinions['ok']} skipped={opinions.get('skipped')} records={opinions['upserted']} error={opinions['error']}")

    day = generated_day(today)
    laws_added = upsert_laws(laws, plaw.get("lawRows") or [], day) if plaw.get("ok") else 0
    dates_filled = plaw.get("datesFilled") or 0
    if dates_filled and not laws_added:
        laws["generated"] = day
    eo_updates = sources[0].get("eoUpdates") or []
    # One row per EO number; the Federal Register list is newest first.
    deduped = []
    seen_numbers = set()
    for update in eo_updates:
        if update["number"] in seen_numbers:
            continue
        seen_numbers.add(update["number"])
        deduped.append(update)
    eos_changed = upsert_executive_orders(eos, deduped, day) if sources[0].get("ok") else 0

    if len(laws.get("rows") or []) < law_rows_before or len(eos.get("rows") or []) < eo_rows_before:
        log("Refusing to write: a sync would have dropped historical rows")
        return 2

    if dry_run:
        log("Dry run; files not written")
        return 0 if required_ok(sources) else 2

    if laws_added or dates_filled:
        dump_compact(LAWS_PATH, laws)
    if eos_changed:
        dump_compact(EOS_PATH, eos)

    # House Clerk records are merged last so a verified Clerk URL wins on the same vote id.
    reordered = [source for source in sources if source["id"] != "house-clerk"] + [house]
    write_outputs(checked, reordered, laws_added, eos_changed, LIVE_PATH.exists())
    return 0 if required_ok(sources) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
