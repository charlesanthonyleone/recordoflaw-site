"""Direct parsers for official state legislature enacted-bill sources.

Each adapter returns only rows the source itself marks as chaptered, signed,
or otherwise enacted. Titles and dates are copied from that source.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urljoin
from xml.etree import ElementTree as ET

from httputil import SourceError, get_bytes, get_json, get_text
from merge import bill_spaced, clean, iso_date, make_record

WA_NS = {"w": "http://WSLWebServices.leg.wa.gov/"}


def _src(label, url, publisher):
    return {"label": label, "url": url, "publisher": publisher}


def ordinal(number):
    value = int(number)
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def fetch_alaska():
    records = []
    sessions = []
    for legislature in (32, 33, 34):
        url = f"https://www.akleg.gov/basis/Bill/Range/{legislature}"
        html = get_text(url, optional=True)
        if not html or "Short Title" not in html:
            continue
        found = 0
        for row in re.findall(r'<tr[^>]*class="(?:House|Senate)"[^>]*>(.*?)</tr>', html, re.S):
            link = re.search(r'<a href="([^"]+)">([^<]+)</a>', row)
            title = re.search(r'<td class="col02">([^<]*)</td>', row)
            status = re.search(r'<td class="col04">([^<]*)</td>', row)
            dated = re.search(r'<td class="col05">([^<]*)</td>', row)
            if not (link and title and status):
                continue
            status_text = clean(status.group(1))
            upper = status_text.upper()
            if "VETO" in upper and "OVERRIDE" not in upper:
                continue
            if "CHAPTER" not in upper and "SIGNED" not in upper:
                continue
            identifier = clean(link.group(2))
            href = urljoin("https://www.akleg.gov/", link.group(1).replace(" ", "%20"))
            kind = "chaptered" if "CHAPTER" in upper else "signed"
            chapter_no = re.search(r"CHAPTER\s+(\d+)", status_text, re.I)
            records.append(
                make_record(
                    state="AK",
                    session=str(legislature),
                    identifier=identifier,
                    title=clean(title.group(1)),
                    status=kind,
                    statusLabel=status_text,
                    date=iso_date(dated.group(1) if dated else None),
                    dateKind="status" if dated and iso_date(dated.group(1)) else None,
                    chapter=chapter_no.group(1) if chapter_no else None,
                    officialUrl=href,
                    sources=[_src("Alaska Legislature BASIS bill", href, "Alaska State Legislature")],
                )
            )
            found += 1
        if found:
            sessions.append(
                {
                    "id": str(legislature),
                    "name": f"{ordinal(legislature)} Legislature",
                    "source": url,
                }
            )
    if not records:
        raise SourceError("Alaska BASIS returned no chaptered or signed bills")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Chaptered or signed bills on Alaska Legislature BASIS bill-range pages for the 32nd, 33rd, and 34th legislatures.",
    }


def fetch_massachusetts():
    records = []
    sessions = []
    for year in (2023, 2024, 2025, 2026):
        url = f"https://malegislature.gov/Laws/SessionLaws/Acts/{year}"
        html = get_text(url, optional=True)
        if not html or "sessionLawsList" not in html:
            continue
        found = 0
        for item in re.findall(r"<li>\s*(.*?)</li>", html, re.S):
            chapter = re.search(
                r'href="(/Laws/SessionLaws/Acts/\d+/Chapter\d+)"[^>]*>\s*Chapter\s+(\d+)',
                item,
            )
            if not chapter:
                continue
            title = re.search(r'class="lawTitle"[^>]*>(.*?)</a>', item, re.S)
            bill = re.search(r'class="bill"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', item, re.S)
            governor = re.search(r'class="governor"[^>]*>(.*?)</span>', item, re.S)
            chapter_url = urljoin("https://malegislature.gov/", chapter.group(1))
            title_text = clean(title.group(1) if title else "")
            governor_text = clean(governor.group(1) if governor else "") or "Session law"
            bill_href = urljoin("https://malegislature.gov/", bill.group(1)) if bill else None
            bill_label = clean(bill.group(2) if bill else "")
            sources = [_src(f"{year} Acts, Chapter {chapter.group(2)}", chapter_url, "Massachusetts General Court")]
            if bill_href:
                sources.append(_src(bill_label or "Bill", bill_href, "Massachusetts General Court"))
            records.append(
                make_record(
                    state="MA",
                    session=str(year),
                    identifier=f"Chapter {chapter.group(2)}",
                    title=title_text,
                    status="enacted",
                    statusLabel=governor_text,
                    date=iso_date(governor_text),
                    dateKind="approved" if iso_date(governor_text) else None,
                    chapter=chapter.group(2),
                    officialUrl=chapter_url,
                    sources=sources,
                )
            )
            found += 1
        if found:
            sessions.append({"id": str(year), "name": f"{year} Acts", "source": url})
    if not records:
        raise SourceError("Massachusetts session-law list returned no chapters")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Chapters published on the Massachusetts General Court session-law acts pages.",
    }


def fetch_minnesota():
    records = []
    sessions = []
    for year in (2023, 2024, 2025, 2026):
        url = f"https://www.revisor.mn.gov/laws/{year}/0/"
        html = get_text(url, optional=True)
        if not html or "Presentment Date" not in html:
            continue
        found = 0
        for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
            chapter = re.search(
                r'href="(https://www\.revisor\.mn\.gov/laws/[^"]+)"[^>]*>Chapter(?:&nbsp;|\s+)(\d+)',
                row,
            )
            bill = re.search(r'href="([^"]+)"[^>]*>([A-Z]{1,4}\d+)</a>', row)
            if not (chapter and bill):
                continue
            plain_cells = [clean(cell) for cell in re.findall(r"<td>\s*([^<]*)\s*</td>", row)]
            presentment = next((cell for cell in plain_cells if iso_date(cell)), None)
            veto = next((cell for cell in plain_cells if cell and not iso_date(cell)), "")
            identifier = bill_spaced(bill.group(2))
            bill_url = urljoin("https://www.revisor.mn.gov/", bill.group(1))
            label = "Session law"
            if veto:
                label = f"Session law; veto column: {veto}"
            records.append(
                make_record(
                    state="MN",
                    session=str(year),
                    identifier=identifier,
                    title=f"Chapter {chapter.group(2)} — {identifier}",
                    status="chaptered",
                    statusLabel=label,
                    date=iso_date(presentment),
                    dateKind="presentment" if presentment else None,
                    chapter=chapter.group(2),
                    officialUrl=chapter.group(1),
                    sources=[
                        _src(f"{year} session law chapter {chapter.group(2)}", chapter.group(1), "Minnesota Revisor of Statutes"),
                        _src(identifier, bill_url, "Minnesota Revisor of Statutes"),
                    ],
                )
            )
            found += 1
        if found:
            sessions.append({"id": str(year), "name": f"{year} regular session laws", "source": url})
    if not records:
        raise SourceError("Minnesota session-law tables returned no chapters")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Chapters on the Minnesota Revisor session-law index. The date is the presentment date printed in that table. The index does not print a separate subject title; the row is named by chapter and bill number.",
    }


def fetch_wisconsin():
    records = []
    sessions = []
    pattern = re.compile(
        r'<a href="(/document/acts/(\d+)/(\d+))">(\d{4} Wisconsin Act \d+)</a>.*?</span>\s*-\s*(.*?)\s*</p>',
        re.S,
    )
    for year in (2023, 2024, 2025, 2026):
        url = f"https://docs.legis.wisconsin.gov/{year}/related/acts"
        html = get_text(url, optional=True)
        if not html:
            continue
        found = 0
        seen = set()
        for path, act_year, number, label, description in pattern.findall(html):
            key = (act_year, number)
            if key in seen:
                continue
            seen.add(key)
            official = urljoin("https://docs.legis.wisconsin.gov/", path)
            records.append(
                make_record(
                    state="WI",
                    session=act_year,
                    identifier=clean(label),
                    title=clean(description),
                    status="enacted",
                    statusLabel="Wisconsin Act",
                    chapter=number,
                    officialUrl=official,
                    sources=[_src(clean(label), official, "Wisconsin Legislative Reference Bureau")],
                )
            )
            found += 1
        if found:
            sessions.append({"id": str(year), "name": f"{year} acts", "source": url})
    if not records:
        raise SourceError("Wisconsin acts index returned no acts")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Acts listed on the Wisconsin Legislative Reference Bureau acts index. The index states the relating-to clause and does not state an approval date.",
    }


def fetch_texas():
    records = []
    sessions = []
    for session in ("87R", "88R", "89R"):
        url = f"https://capitol.texas.gov/Reports/Report.aspx?LegSess={session}&ID=signedbygov"
        html = get_text(url, optional=True)
        if not html or "Bills Signed by the Governor" not in html:
            continue
        found = 0
        for block in html.split('<div class="row">')[1:]:
            link = re.search(
                r'href="(https?://capitol\.texas\.gov/BillLookup/History\.aspx\?LegSess=([^"&]+)&(?:amp;)?Bill=([^"]+))"[^>]*>\s*([^<]+?)\s*</a>',
                block,
            )
            action = re.search(
                r"<b>Last Action:</b></div>\s*<div class=\"bill-search-result-data\">([^<]+)</div>",
                block,
            )
            caption = re.search(
                r"<b>Caption</b>:\s*</div>\s*<div class=\"bill-search-result-data\">([^<]+)</div>",
                block,
            )
            if not (link and caption):
                continue
            action_text = clean(action.group(1) if action else "")
            official = link.group(1).replace("&amp;", "&").replace("http://", "https://", 1)
            records.append(
                make_record(
                    state="TX",
                    session=session,
                    identifier=clean(link.group(4)),
                    title=clean(caption.group(1)),
                    status="signed",
                    statusLabel=("Signed by the governor. " + action_text).strip(),
                    date=iso_date(action_text),
                    dateKind="last-action" if iso_date(action_text) else None,
                    officialUrl=official,
                    sources=[
                        _src("Bill history", official, "Texas Legislature"),
                        _src("Bills Signed by the Governor", url, "Texas Legislature"),
                    ],
                )
            )
            found += 1
        if found == 0:
            raise SourceError(f"Texas signed-bill report for {session} had no parsable rows")
        sessions.append({"id": session, "name": f"{session} bills signed by the governor", "source": url})
    if not records:
        raise SourceError("Texas signed-bill reports were unavailable")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Bills on the Texas Legislature report titled Bills Signed by the Governor, for the 87th, 88th, and 89th regular sessions. The date is the last-action date printed on that report.",
    }


def _or_sessions():
    payload = get_json(
        "https://api.oregonlegislature.gov/odata/odataservice.svc/LegislativeSessions"
        "?$orderby=SessionKey%20desc&$top=40&$format=json"
    )
    chosen = []
    for row in payload.get("value") or []:
        name = row.get("SessionName") or ""
        begin = row.get("BeginDate") or ""
        if begin < "2023-01-01":
            continue
        if "Interim" in name:
            continue
        chosen.append(row)
    return chosen


def fetch_oregon():
    records = []
    sessions = []
    for session in _or_sessions():
        key = session["SessionKey"]
        skip = 0
        found = 0
        while True:
            url = (
                "https://api.oregonlegislature.gov/odata/odataservice.svc/Measures"
                f"?$filter=SessionKey%20eq%20%27{quote(key)}%27%20and%20ChapterNumber%20ne%20null"
                "&$select=SessionKey,MeasurePrefix,MeasureNumber,CatchLine,ChapterNumber,EffectiveDate,Vetoed,CurrentLocation"
                f"&$top=200&$skip={skip}&$format=json"
            )
            page = get_json(url).get("value") or []
            if not page:
                break
            for row in page:
                chapter = clean(row.get("ChapterNumber"))
                if not chapter or chapter == "9999":
                    continue
                if row.get("Vetoed") is True:
                    continue
                if row.get("CurrentLocation") != "Chapter Number Assigned":
                    continue
                prefix = clean(row.get("MeasurePrefix"))
                number = row.get("MeasureNumber")
                if not prefix or number is None:
                    continue
                identifier = f"{prefix} {number}"
                official = f"https://olis.oregonlegislature.gov/liz/{key}/Measures/Overview/{prefix}{number}"
                records.append(
                    make_record(
                        state="OR",
                        session=key,
                        identifier=identifier,
                        title=clean(row.get("CatchLine")),
                        status="chaptered",
                        statusLabel=f"Chapter {chapter} assigned",
                        date=iso_date(row.get("EffectiveDate")),
                        dateKind="effective" if iso_date(row.get("EffectiveDate")) else None,
                        chapter=str(int(chapter)) if chapter.isdigit() else chapter,
                        officialUrl=official,
                        sources=[_src(f"{identifier} overview", official, "Oregon Legislative Information System")],
                    )
                )
                found += 1
            if len(page) < 200:
                break
            skip += 200
        if found:
            sessions.append(
                {
                    "id": key,
                    "name": session.get("SessionName") or key,
                    "source": f"https://olis.oregonlegislature.gov/liz/{key}/Measures/Overview",
                }
            )
    if not records:
        raise SourceError("Oregon OLIS returned no chaptered measures")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Measures the Oregon Legislative Information System marks Chapter Number Assigned since 2023, excluding vetoed measures and the placeholder chapter 9999.",
    }


def fetch_wyoming():
    records = []
    sessions = []
    for year in (2023, 2024, 2025, 2026):
        url = (
            "https://lsoservice.wyoleg.gov/api/BillInformation?"
            f"$filter=Year%20eq%20{year}"
            "&$select=BillNum,ShortTitle,ChapterNo,SignedDate,EffectiveDate,Year,BillType,BillStatus,LastAction,LastActionDate"
        )
        try:
            rows = get_json(url)
        except SourceError:
            continue
        if not isinstance(rows, list):
            continue
        found = 0
        for row in rows:
            signed = row.get("signedDate")
            chapter = clean(row.get("chapterNo"))
            action = clean(row.get("lastAction"))
            governor_signed = action.lower().startswith("governor signed")
            if not signed and not chapter and not governor_signed:
                continue
            bill_num = clean(row.get("billNum"))
            if not bill_num:
                continue
            official = f"https://wyoleg.gov/Legislation/{year}/{bill_num}"
            if signed:
                date = iso_date(signed)
                date_kind = "signed"
                label = "Signed"
            elif governor_signed:
                date = iso_date(row.get("lastActionDate"))
                date_kind = "signed" if date else None
                label = action
            else:
                date = iso_date(row.get("effectiveDate"))
                date_kind = "effective" if date else None
                label = "Chapter assigned"
            records.append(
                make_record(
                    state="WY",
                    session=str(year),
                    identifier=bill_num,
                    title=clean(row.get("shortTitle")),
                    status="signed" if signed or governor_signed else "chaptered",
                    statusLabel=label,
                    date=date,
                    dateKind=date_kind,
                    chapter=str(int(chapter)) if chapter.isdigit() else (chapter or None),
                    officialUrl=official,
                    sources=[_src(bill_num, official, "Wyoming Legislature")],
                )
            )
            found += 1
        if found:
            sessions.append(
                {
                    "id": str(year),
                    "name": f"{year} bills",
                    "source": f"https://wyoleg.gov/Legislation/{year}",
                }
            )
    if not records:
        raise SourceError("Wyoming bill service returned no signed or chaptered bills")
    return {
        "records": records,
        "sessions": sessions,
        "note": "Wyoming Legislature bill records for 2023–2026 with a signature date, a governor-signed action, or a chapter number.",
    }


def _wa_signed_ids(biennium, agency):
    url = (
        "https://wslwebservices.leg.wa.gov/legislationservice.asmx/"
        f"GetLegislationGovernorSigned?biennium={quote(biennium)}&agency={quote(agency)}"
    )
    _status, _headers, raw = get_bytes(url, timeout=60)
    root = ET.fromstring(raw)
    rows = []
    for info in root.findall(".//w:LegislationInfo", WA_NS):
        bill_id = (info.findtext("w:BillId", default="", namespaces=WA_NS) or "").strip()
        number = (info.findtext("w:BillNumber", default="", namespaces=WA_NS) or "").strip()
        if bill_id and number:
            rows.append((bill_id, number))
    return rows


def _wa_chapter(biennium, bill_id):
    url = (
        "https://wslwebservices.leg.wa.gov/legislationservice.asmx/"
        f"GetSessionLawChapter?billId={quote(bill_id)}&biennium={quote(biennium)}"
    )
    _status, _headers, raw = get_bytes(url, timeout=40)
    root = ET.fromstring(raw)

    def val(name):
        return (root.findtext(f"w:{name}", default="", namespaces=WA_NS) or "").strip()

    if val("Veto").lower() == "true":
        return None
    title = val("BillTitle")
    if not title:
        return None
    return {
        "title": title,
        "chapter": val("ChapterNumber"),
        "effective": val("EffectiveDate"),
        "partial": val("PartialVeto").lower() == "true",
        "year": val("Year"),
    }


def fetch_washington():
    records = []
    sessions = []
    skipped = 0
    for biennium in ("2023-24", "2025-26"):
        jobs = []
        for agency in ("House", "Senate"):
            for bill_id, number in _wa_signed_ids(biennium, agency):
                jobs.append((bill_id, number))
        found = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_wa_chapter, biennium, bill_id): (bill_id, number) for bill_id, number in jobs}
            for future in as_completed(futures):
                bill_id, number = futures[future]
                try:
                    chapter = future.result()
                except Exception:
                    skipped += 1
                    continue
                if not chapter:
                    skipped += 1
                    continue
                year = chapter["year"] or biennium[:4]
                official = (
                    "https://app.leg.wa.gov/billsummary?BillNumber="
                    f"{quote(number)}&Initiative=false&Year={quote(year)}"
                )
                label = "Signed by the governor"
                if chapter["partial"]:
                    label += "; partial veto"
                chapter_no = chapter["chapter"]
                records.append(
                    make_record(
                        state="WA",
                        session=biennium,
                        identifier=bill_id,
                        title=chapter["title"],
                        status="signed",
                        statusLabel=label,
                        date=iso_date(chapter["effective"]),
                        dateKind="effective" if iso_date(chapter["effective"]) else None,
                        chapter=str(int(chapter_no)) if chapter_no.isdigit() else (chapter_no or None),
                        officialUrl=official,
                        sources=[_src(bill_id, official, "Washington State Legislature")],
                    )
                )
                found += 1
        if found:
            sessions.append(
                {
                    "id": biennium,
                    "name": f"{biennium} biennium",
                    "source": "https://app.leg.wa.gov/",
                }
            )
        elif jobs:
            raise SourceError(f"Washington signed bills for {biennium} could not be matched to session-law chapters")
    if not records:
        raise SourceError("Washington signed-bill service returned no chapters")
    note = (
        "Bills the Washington Legislative Web Service lists as signed by the governor "
        "for the 2023-24 and 2025-26 biennia, with the session-law title and effective date. "
        "Full vetoes are omitted."
    )
    if skipped:
        note += f" {skipped} signed-list rows were skipped because the session-law record had no title or was a full veto."
    return {"records": records, "sessions": sessions, "note": note}


def enacted_action(actions):
    """Open States action classifications that mean the bill became law."""
    chosen = None
    for action in actions or []:
        classes = {item for item in (action.get("classification") or []) if isinstance(item, str)}
        if "became-law" in classes:
            return action
        if "executive-signature" in classes and chosen is None:
            chosen = action
    return chosen


def official_source(bill):
    for source in bill.get("sources") or []:
        url = source.get("url") or ""
        if not url:
            continue
        host = url.lower()
        if "openstates.org" in host or "pluralpolicy.com" in host:
            continue
        return url
    return None


def fetch_openstates(state_name, api_key, updated_since=None):
    headers = {"X-API-KEY": api_key}
    pages = 8 if updated_since else 25
    records_by_state_code = []
    params_base = f"jurisdiction={quote(state_name)}&per_page=20&sort=updated_desc&include=actions,sources"
    if updated_since:
        params_base += f"&updated_since={quote(updated_since)}"
    for page in range(1, pages + 1):
        url = f"https://v3.openstates.org/bills?{params_base}&page={page}"
        payload = get_json(url, headers=headers)
        results = payload.get("results") or []
        if not results:
            break
        for bill in results:
            action = enacted_action(bill.get("actions"))
            official = official_source(bill)
            if not action or not official:
                continue
            identifier = clean(bill.get("identifier"))
            session = clean(bill.get("session"))
            if not identifier or not session:
                continue
            sources = [_src("Official bill page", official, state_name + " legislature")]
            openstates_url = bill.get("openstates_url")
            if openstates_url:
                sources.append(_src("Open States bill", openstates_url, "Open States"))
            records_by_state_code.append(
                {
                    "identifier": identifier,
                    "session": session,
                    "title": clean(bill.get("title")),
                    "status": "enacted",
                    "statusLabel": clean(action.get("description")) or "Became law",
                    "date": iso_date(action.get("date")),
                    "dateKind": "action" if iso_date(action.get("date")) else None,
                    "officialUrl": official,
                    "sources": sources,
                }
            )
        if len(results) < 20:
            break
    return records_by_state_code, pages


ADAPTERS = {
    "ak-basis": fetch_alaska,
    "ma-acts": fetch_massachusetts,
    "mn-session-laws": fetch_minnesota,
    "wi-acts": fetch_wisconsin,
    "tx-signed": fetch_texas,
    "or-odata": fetch_oregon,
    "wy-bills": fetch_wyoming,
    "wa-signed": fetch_washington,
}
