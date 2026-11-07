"""Turn official payloads into ledger records. No dates or titles are invented."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9:._/-]{0,180}$")
PRESIDENT_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLAW_RE = re.compile(r"^PLAW-(\d+)(publ|pvtl)(\d+)$")
BILL_RE = re.compile(r"^BILLS-(\d+)([a-z]+?)(\d+)([a-z]+)$")

BILL_VERSIONS = {
    "ih": "Introduced in House",
    "rh": "Reported in House",
    "eh": "Engrossed House",
    "is": "Introduced in Senate",
    "rs": "Reported in Senate",
    "es": "Engrossed Senate",
    "enr": "Enrolled",
    "rds": "Received in Senate",
    "rfh": "Referred in House",
    "rfs": "Referred in Senate",
    "pcs": "Placed on Calendar Senate",
    "pch": "Placed on Calendar House",
    "ash": "Additional Sponsors House",
    "eas": "Engrossed Amendment Senate",
    "eah": "Engrossed Amendment House",
}

BILL_TYPE_LABEL = {
    "hr": "H.R.",
    "s": "S.",
    "hres": "H.Res.",
    "sres": "S.Res.",
    "hjres": "H.J.Res.",
    "sjres": "S.J.Res.",
    "hconres": "H.Con.Res.",
    "sconres": "S.Con.Res.",
}

CONGRESS_BILL_SLUG = {
    "HR": "house-bill",
    "S": "senate-bill",
    "HJRES": "house-joint-resolution",
    "SJRES": "senate-joint-resolution",
    "HCONRES": "house-concurrent-resolution",
    "SCONRES": "senate-concurrent-resolution",
    "HRES": "house-resolution",
    "SRES": "senate-resolution",
}

LAW_BILL_TYPES = {"HR", "S", "HJRES", "SJRES"}

FR_TYPES = {
    "Rule": "rule",
    "Proposed Rule": "proposed-rule",
    "Notice": "notice",
    "Presidential Document": "presidential-document",
}

PRESIDENTIAL_KINDS = {"executive-order", "proclamation", "presidential-document"}
DATE_KINDS = {"enacted", "signed", "published", "voted", "decided", "acted"}
BRANCHES = {"legislative", "executive", "judicial"}
SOURCES = {
    "federal-register",
    "govinfo",
    "congress-gov",
    "house-clerk",
    "supremecourt-gov",
    "courtlistener",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean_text(value: str | None, limit: int = 2000) -> str:
    if not value:
        return ""
    text = html.unescape(value).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return ""
    return text


def iso_date(value: str | None, today: date | None = None) -> str | None:
    if not value or not ISO_DATE.fullmatch(value.strip()):
        return None
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        return None
    today = today or datetime.now(timezone.utc).date()
    if parsed.year < 1789 or parsed > today + timedelta(days=2):
        return None
    return parsed.isoformat()


def parse_mdy(value: str, today: date | None = None) -> str | None:
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})", value.strip())
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    if year < 100:
        year += 2000 if year < 70 else 1900
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    return iso_date(parsed.isoformat(), today)


def parse_rfc822(value: str, today: date | None = None) -> str | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed is None:
        return None
    return iso_date(parsed.date().isoformat(), today)


def parse_clerk_date(value: str, today: date | None = None) -> str | None:
    try:
        parsed = datetime.strptime(value.strip(), "%d-%b-%Y").date()
    except ValueError:
        return None
    return iso_date(parsed.isoformat(), today)


def https_url(value: str | None) -> str | None:
    if not value:
        return None
    url = value.strip()
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    if not url.startswith("https://") or " " in url:
        return None
    return url


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def accept_record(record: dict) -> dict | None:
    required = ("id", "branch", "kind", "date", "dateKind", "title", "officialUrl", "officialId", "source")
    if any(not record.get(key) for key in required):
        return None
    if not ID_RE.fullmatch(record["id"]):
        return None
    if record["branch"] not in BRANCHES or record["dateKind"] not in DATE_KINDS:
        return None
    if record["source"] not in SOURCES:
        return None
    if iso_date(record["date"]) != record["date"]:
        return None
    url = https_url(record["officialUrl"])
    if not url:
        return None
    kept = {
        "id": record["id"],
        "branch": record["branch"],
        "kind": record["kind"],
        "date": record["date"],
        "dateKind": record["dateKind"],
        "title": clean_text(record["title"]),
        "officialUrl": url,
        "officialId": clean_text(str(record["officialId"]), 240),
        "source": record["source"],
    }
    if not kept["title"] or not kept["officialId"]:
        return None
    for optional in ("citation", "actor", "detail", "sourceText"):
        text = clean_text(record.get(optional), 2000 if optional == "sourceText" else 500)
        if text:
            kept[optional] = text
    return kept


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _children_text(item: ET.Element, name: str) -> str:
    for child in list(item):
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def parse_rss_items(xml_bytes: bytes) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.iter():
        if _local(item.tag) != "item":
            continue
        guid = _children_text(item, "guid")
        title = clean_text(_children_text(item, "title"))
        link = https_url(_children_text(item, "link"))
        published = parse_rfc822(_children_text(item, "pubDate"))
        if guid and title and link:
            items.append({"guid": guid, "title": title, "link": link, "published": published})
    return items


def parse_plaw_guid(guid: str) -> dict | None:
    match = PLAW_RE.fullmatch(guid.strip())
    if not match:
        return None
    congress, kind, number = match.groups()
    return {
        "packageId": guid.strip(),
        "congress": int(congress),
        "lawKind": "pub" if kind == "publ" else "priv",
        "number": int(number),
        "lawNumber": f"{congress}-{number}",
    }


def parse_bill_guid(guid: str) -> dict | None:
    match = BILL_RE.fullmatch(guid.strip())
    if not match:
        return None
    congress, bill_type, number, version = match.groups()
    if bill_type not in BILL_TYPE_LABEL:
        return None
    return {
        "packageId": guid.strip(),
        "congress": int(congress),
        "billType": bill_type,
        "number": number,
        "version": version,
    }


def bill_record(item: dict) -> dict | None:
    parsed = parse_bill_guid(item["guid"])
    if not parsed or not item.get("published"):
        return None
    label = BILL_TYPE_LABEL[parsed["billType"]]
    version = BILL_VERSIONS.get(parsed["version"], parsed["version"])
    return accept_record({
        "id": f"bill:{parsed['congress']}:{parsed['billType']}:{parsed['number']}:{parsed['version']}",
        "branch": "legislative",
        "kind": "bill",
        "date": item["published"],
        "dateKind": "published",
        "title": item["title"],
        "citation": f"{label} {parsed['number']} ({parsed['version']})",
        "actor": "United States Congress",
        "detail": f"GovInfo bill text, version: {version}",
        "officialUrl": item["link"],
        "officialId": parsed["packageId"],
        "source": "govinfo",
    })


def plaw_record_from_ledger(item: dict, row: list) -> dict | None:
    parsed = parse_plaw_guid(item["guid"])
    if not parsed or not row or not row[6]:
        return None
    kind = "public-law" if parsed["lawKind"] == "pub" else "private-law"
    label = "Public Law" if parsed["lawKind"] == "pub" else "Private Law"
    return accept_record({
        "id": f"{'plaw' if parsed['lawKind'] == 'pub' else 'pvtlaw'}:{parsed['lawNumber']}",
        "branch": "legislative",
        "kind": kind,
        "date": row[6],
        "dateKind": "enacted",
        "title": row[5] or item["title"],
        "citation": f"{label} {parsed['lawNumber']}",
        "actor": "United States Congress",
        "officialUrl": item["link"],
        "officialId": parsed["packageId"],
        "source": "govinfo",
    })


def parse_mods(xml_bytes: bytes) -> dict:
    root = ET.fromstring(xml_bytes)
    dates = []
    shorts = []
    titles = []
    bills = []
    for el in root.iter():
        name = _local(el.tag)
        text = (el.text or "").strip()
        if name == "dateIssued" and ISO_DATE.fullmatch(text):
            dates.append(text)
        elif name == "shortTitle" and text:
            shorts.append(clean_text(text))
        elif name == "title" and text:
            titles.append(clean_text(text))
        elif name == "bill" and el.attrib.get("type") and el.attrib.get("number"):
            bills.append(el.attrib)
    primary = next((bill for bill in bills if bill.get("priority") == "primary"), None)
    bill = primary or (bills[0] if bills else None)
    short = next((title for title in shorts if title), "")
    long_title = next((title for title in titles if title and not title.lower().startswith("public law")), "")
    return {
        "dateIssued": dates[0] if dates else None,
        "title": short or long_title,
        "billType": (bill or {}).get("type"),
        "billNumber": (bill or {}).get("number"),
        "billCongress": (bill or {}).get("congress"),
    }


def law_row_from_mods(package: dict, mods: dict) -> list | None:
    enacted = iso_date(mods.get("dateIssued"))
    title = clean_text(mods.get("title"))
    bill_type = (mods.get("billType") or "").upper()
    bill_number = (mods.get("billNumber") or "").strip()
    if not enacted or not title or bill_type not in LAW_BILL_TYPES or not bill_number.isdigit():
        return None
    if mods.get("billCongress") and str(mods["billCongress"]) != str(package["congress"]):
        return None
    return [
        package["congress"],
        package["lawKind"],
        package["lawNumber"],
        bill_type,
        bill_number,
        title,
        enacted,
    ]


def plaw_record_from_mods(item: dict, package: dict, mods: dict, row: list) -> dict | None:
    if not row:
        return None
    kind = "public-law" if package["lawKind"] == "pub" else "private-law"
    label = "Public Law" if package["lawKind"] == "pub" else "Private Law"
    return accept_record({
        "id": f"{'plaw' if package['lawKind'] == 'pub' else 'pvtlaw'}:{package['lawNumber']}",
        "branch": "legislative",
        "kind": kind,
        "date": row[6],
        "dateKind": "enacted",
        "title": row[5],
        "citation": f"{label} {package['lawNumber']}",
        "actor": "United States Congress",
        "officialUrl": item["link"],
        "officialId": package["packageId"],
        "source": "govinfo",
    })


def president_slug(president) -> str | None:
    if not isinstance(president, dict):
        return None
    ident = president.get("identifier")
    if isinstance(ident, str) and PRESIDENT_RE.fullmatch(ident):
        return ident
    return None


def _agency_names(doc: dict) -> str:
    names = []
    for agency in doc.get("agencies") or []:
        if isinstance(agency, dict):
            name = clean_text(agency.get("name"), 200)
            if name and name not in names:
                names.append(name)
    return "; ".join(names)


def federal_register_record(doc: dict) -> dict | None:
    if not isinstance(doc, dict):
        return None
    doc_type = doc.get("type")
    if doc_type not in FR_TYPES:
        return None
    document_number = clean_text(str(doc.get("document_number") or ""), 40)
    title = clean_text(doc.get("title"))
    url = https_url(doc.get("html_url"))
    if not document_number or not title or not url:
        return None
    subtype = clean_text(doc.get("subtype"), 80)
    publication = iso_date(doc.get("publication_date"))
    signing = iso_date(doc.get("signing_date"))
    kind = FR_TYPES[doc_type]
    if subtype == "Executive Order":
        kind = "executive-order"
    elif subtype == "Proclamation":
        kind = "proclamation"
    if kind in PRESIDENTIAL_KINDS and signing:
        when, date_kind = signing, "signed"
    elif publication:
        when, date_kind = publication, "published"
    else:
        return None
    agencies = _agency_names(doc)
    president_name = clean_text((doc.get("president") or {}).get("name") if isinstance(doc.get("president"), dict) else None, 120)
    # The Federal Register API stamps the sitting president on agency documents.
    # That name is the actor only for presidential documents.
    if kind in PRESIDENTIAL_KINDS:
        actor = president_name or agencies
    else:
        actor = agencies
    citation_parts = []
    if kind == "executive-order" and str(doc.get("executive_order_number") or "").isdigit():
        citation_parts.append(f"EO {doc['executive_order_number']}")
    if kind == "proclamation" and str(doc.get("proclamation_number") or "").isdigit():
        citation_parts.append(f"Proclamation {doc['proclamation_number']}")
    if isinstance(doc.get("citation"), str) and doc["citation"].strip():
        citation_parts.append(doc["citation"].strip())
    return accept_record({
        "id": f"fr:{document_number}",
        "branch": "executive",
        "kind": kind,
        "date": when,
        "dateKind": date_kind,
        "title": title,
        "citation": " · ".join(citation_parts),
        "actor": actor,
        "detail": subtype if subtype and kind == "presidential-document" else "",
        "sourceText": doc.get("abstract") if isinstance(doc.get("abstract"), str) else "",
        "officialUrl": url,
        "officialId": document_number,
        "source": "federal-register",
    })


def executive_order_update(doc: dict) -> dict | None:
    if not isinstance(doc, dict) or clean_text(doc.get("subtype"), 80) != "Executive Order":
        return None
    number = str(doc.get("executive_order_number") or "")
    signing = iso_date(doc.get("signing_date"))
    title = clean_text(doc.get("title"))
    url = https_url(doc.get("html_url"))
    if not number.isdigit() or not signing or not title or not url:
        return None
    citation = doc.get("citation") if isinstance(doc.get("citation"), str) else None
    return {
        "number": number,
        "signing_date": signing,
        "title": title,
        "president": president_slug(doc.get("president")),
        "citation": clean_text(citation, 80) or None,
        "url": url,
    }


def _xml_text(parent: ET.Element, name: str) -> str:
    el = None
    for child in list(parent):
        if _local(child.tag) == name:
            el = child
            break
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def parse_house_vote(xml_bytes: bytes, year: int) -> dict | None:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None
    meta = next((el for el in root.iter() if _local(el.tag) == "vote-metadata"), None)
    if meta is None:
        return None
    congress = _xml_text(meta, "congress")
    session = _xml_text(meta, "session")
    roll = _xml_text(meta, "rollcall-num")
    if not congress.isdigit() or not roll.isdigit():
        return None
    session_num = {"1st": "1", "2nd": "2"}.get(session)
    if not session_num:
        return None
    when = parse_clerk_date(_xml_text(meta, "action-date"))
    question = clean_text(_xml_text(meta, "vote-question"), 300)
    desc = clean_text(_xml_text(meta, "vote-desc"), 500)
    result = clean_text(_xml_text(meta, "vote-result"), 80)
    legis = clean_text(_xml_text(meta, "legis-num"), 40)
    if not when or not (question or desc):
        return None
    yea = nay = None
    for el in meta.iter():
        if _local(el.tag) != "totals-by-vote":
            continue
        yea = _xml_text(el, "yea-total")
        nay = _xml_text(el, "nay-total")
    tally = ""
    if yea.isdigit() and nay.isdigit():
        tally = f"Yeas {yea}, Nays {nay}"
    detail = " · ".join(part for part in (result, tally) if part)
    title = desc or question
    if legis and desc:
        title = f"{legis}: {desc}"
    elif legis and question:
        title = f"{legis}: {question}"
    return accept_record({
        "id": f"house-vote:{congress}:{session_num}:{int(roll)}",
        "branch": "legislative",
        "kind": "house-vote",
        "date": when,
        "dateKind": "voted",
        "title": title,
        "citation": f"House roll call {int(roll)}, {ordinal(int(congress))} Congress, {session} session",
        "actor": "U.S. House of Representatives",
        "detail": detail,
        "officialUrl": f"https://clerk.house.gov/Votes/{year}{int(roll)}",
        "officialId": f"{year}/roll{int(roll):03d}",
        "source": "house-clerk",
    })


def parse_slip_opinions(html_text: str, term_year: int) -> list[dict]:
    """Parse one supremecourt.gov slip-opinion table. term_year is the page requested."""
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.tables = []
            self._table = None
            self._row = None
            self._cell = None
            self._href = None
            self._title = None
            self._in_a = False

        def handle_starttag(self, tag, attrs):
            attr = {key.lower(): value for key, value in attrs}
            if tag == "table":
                self._table = []
            elif self._table is not None and tag == "tr":
                self._row = []
            elif self._row is not None and tag in {"td", "th"}:
                self._cell = {"text": "", "href": None, "summary": None}
            elif self._cell is not None and tag == "a":
                self._in_a = True
                self._href = attr.get("href")
                self._title = attr.get("title")

        def handle_data(self, data):
            if self._cell is not None:
                self._cell["text"] += data

        def handle_endtag(self, tag):
            if tag == "a" and self._cell is not None and self._in_a:
                self._cell["href"] = self._href
                self._cell["summary"] = self._title
                self._in_a = False
            elif tag in {"td", "th"} and self._row is not None and self._cell is not None:
                self._cell["text"] = re.sub(r"\s+", " ", self._cell["text"]).strip()
                self._row.append(self._cell)
                self._cell = None
            elif tag == "tr" and self._table is not None and self._row is not None:
                if any(cell["text"] for cell in self._row):
                    self._table.append(self._row)
                self._row = None
            elif tag == "table" and self._table is not None:
                self.tables.append(self._table)
                self._table = None

    parser = Parser()
    parser.feed(html_text)
    tables = []
    for candidate in parser.tables:
        header = " ".join(cell["text"] for cell in candidate[0]).lower() if candidate else ""
        if "docket" in header and "name" in header:
            tables.append(candidate)
    if not tables:
        return []
    records = []
    seen = set()
    for table in tables:
        records.extend(_slip_rows(table[1:], term_year, seen))
    return records


def _slip_rows(rows, term_year: int, seen: set) -> list[dict]:
    records = []
    for row in rows:
        if len(row) < 4:
            continue
        when = parse_mdy(row[1]["text"])
        docket = clean_text(row[2]["text"], 40)
        name = clean_text(row[3]["text"], 300)
        href = row[3].get("href") or ""
        if not when or not docket or not name or "/opinions/" not in href or not href.lower().endswith(".pdf"):
            continue
        if href.startswith("/"):
            url = "https://www.supremecourt.gov" + href
        else:
            url = https_url(href)
        if not url:
            continue
        citation = clean_text(row[5]["text"], 40) if len(row) > 5 else ""
        justice = clean_text(row[4]["text"], 20) if len(row) > 4 else ""
        summary = clean_text(row[3].get("summary"), 2000)
        slip_id = href.rstrip("/").split("/")[-1].lower()
        record_id = f"scotus-slip:{term_year}:{slip_id}"
        if record_id in seen:
            continue
        seen.add(record_id)
        records.append(accept_record({
            "id": record_id,
            "branch": "judicial",
            "kind": "slip-opinion",
            "date": when,
            "dateKind": "decided",
            "title": name,
            "citation": " ".join(part for part in (f"No. {docket}", citation) if part).strip(),
            "actor": "Supreme Court of the United States",
            "detail": f"Slip opinion listing, October Term {term_year}" + (f", {justice}" if justice else ""),
            "sourceText": summary,
            "officialUrl": url,
            "officialId": f"OT{term_year}:{docket}",
            "source": "supremecourt-gov",
        }))
    return [record for record in records if record]


def congress_bill_record(bill: dict) -> dict | None:
    if not isinstance(bill, dict):
        return None
    try:
        congress = int(bill.get("congress"))
        number = str(bill.get("number"))
    except (TypeError, ValueError):
        return None
    bill_type = str(bill.get("type") or "").upper()
    title = clean_text(bill.get("title"))
    action = bill.get("latestAction") if isinstance(bill.get("latestAction"), dict) else {}
    when = iso_date(action.get("actionDate"))
    action_text = clean_text(action.get("text"), 400)
    if bill_type not in CONGRESS_BILL_SLUG or not number.isdigit() or not title or not when:
        return None
    direct = https_url(bill.get("legislationUrl"))
    url = direct or f"https://www.congress.gov/bill/{ordinal(congress)}-congress/{CONGRESS_BILL_SLUG[bill_type]}/{int(number)}"
    return accept_record({
        "id": f"congress-bill:{congress}:{bill_type.lower()}:{int(number)}",
        "branch": "legislative",
        "kind": "bill",
        "date": when,
        "dateKind": "acted",
        "title": title,
        "citation": f"{BILL_TYPE_LABEL.get(bill_type.lower(), bill_type)} {int(number)}",
        "actor": clean_text(bill.get("originChamber"), 80) or "United States Congress",
        "detail": action_text,
        "officialUrl": url,
        "officialId": f"{congress}/{bill_type}/{int(number)}",
        "source": "congress-gov",
    })


def congress_vote_record(vote: dict, chamber: str) -> dict | None:
    """Accept a Congress.gov vote only when the payload itself carries an https URL."""
    if not isinstance(vote, dict) or chamber not in {"house", "senate"}:
        return None
    url = https_url(vote.get("url") if str(vote.get("url", "")).startswith("https://www.congress.gov/") else vote.get("legislationUrl"))
    # Congress.gov vote objects link to the API. Prefer an explicit public URL field when present.
    for key in ("congressGovUrl", "legislationUrl", "sourceUrl"):
        candidate = https_url(vote.get(key))
        if candidate and "api.congress.gov" not in candidate:
            url = candidate
            break
    if not url or "api.congress.gov" in url:
        return None
    roll = vote.get("rollCall") or vote.get("number") or vote.get("roll")
    try:
        roll_num = int(roll)
        congress = int(vote.get("congress"))
        session = int(vote.get("session"))
    except (TypeError, ValueError):
        return None
    when = iso_date(vote.get("date") or vote.get("actionDate") or (vote.get("startDate")))
    question = clean_text(vote.get("question") or vote.get("voteQuestion") or vote.get("description"))
    if not when or not question:
        return None
    result = clean_text(vote.get("result"), 80)
    kind = "house-vote" if chamber == "house" else "senate-vote"
    prefix = "house" if chamber == "house" else "senate"
    return accept_record({
        "id": f"{prefix}-vote:{congress}:{session}:{roll_num}",
        "branch": "legislative",
        "kind": kind,
        "date": when,
        "dateKind": "voted",
        "title": question,
        "citation": f"{chamber.title()} vote {roll_num}",
        "actor": "U.S. House of Representatives" if chamber == "house" else "U.S. Senate",
        "detail": result,
        "officialUrl": url,
        "officialId": f"{congress}/{session}/{roll_num}",
        "source": "congress-gov",
    })


def courtlistener_record(result: dict) -> dict | None:
    if not isinstance(result, dict):
        return None
    court = str(result.get("court_id") or result.get("court") or "").lower()
    if not court or court == "scotus":
        return None
    title = clean_text(result.get("caseName") or result.get("caseNameFull"))
    when = iso_date((result.get("dateFiled") or "")[:10])
    raw_url = result.get("absolute_url") or ""
    if isinstance(raw_url, str) and raw_url.startswith("/"):
        raw_url = "https://www.courtlistener.com" + raw_url
    url = https_url(raw_url)
    ident = result.get("cluster_id") or result.get("id")
    if not title or not when or not url or ident in (None, ""):
        return None
    ident_s = str(ident)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", ident_s):
        return None
    citation = ""
    cites = result.get("citation")
    if isinstance(cites, list) and cites:
        citation = clean_text(str(cites[0]), 120)
    elif isinstance(cites, str):
        citation = clean_text(cites, 120)
    docket = clean_text(str(result.get("docketNumber") or ""), 40)
    return accept_record({
        "id": f"courtlistener:{ident_s.lower()}",
        "branch": "judicial",
        "kind": "opinion",
        "date": when,
        "dateKind": "decided",
        "title": title,
        "citation": " ".join(part for part in (docket, citation) if part),
        "actor": clean_text(result.get("court") if isinstance(result.get("court"), str) and result.get("court") != court else court, 80),
        "officialUrl": url,
        "officialId": ident_s,
        "source": "courtlistener",
    })


def scotus_term_years(today: date) -> list[int]:
    """October Term label used by supremecourt.gov/opinions/slipopinion/{yy}."""
    current = today.year if today.month >= 10 else today.year - 1
    return [current, current - 1]
