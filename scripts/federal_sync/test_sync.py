"""Unit tests for federal ledger sync. No network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from merge_files import merge_records, upsert_executive_orders, upsert_laws
from normalize import (
    accept_record,
    bill_record,
    congress_bill_record,
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
)


SLIP_HTML = """
<table class="table table-bordered">
<tr><th>R-</th><th>Date</th><th>Docket</th><th>Name</th><th>J.</th><th>Citation</th></tr>
<tr>
<td>1</td>
<td>10/14/2026</td>
<td>26A476</td>
<td><a href="/opinions/26pdf/26a476_k537.pdf" title="The order is stayed.">FCC v. Brown</a></td>
<td>PC</td>
<td>610/1</td>
</tr>
<tr>
<td>2</td>
<td>9/25/26</td>
<td></td>
<td><a href="/opinions/26pdf/missing.pdf">No docket</a></td>
<td></td>
<td></td>
</tr>
</table>
"""

HOUSE_XML = """<?xml version="1.0"?>
<rollcall-vote>
  <vote-metadata>
    <congress>119</congress>
    <session>2nd</session>
    <rollcall-num>314</rollcall-num>
    <legis-num>S 2403</legis-num>
    <vote-question>On Motion to Suspend the Rules and Pass</vote-question>
    <vote-result>Passed</vote-result>
    <action-date>16-Sep-2026</action-date>
    <vote-desc>Retire through Ownership Act</vote-desc>
    <vote-totals>
      <totals-by-vote>
        <yea-total>401</yea-total>
        <nay-total>14</nay-total>
      </totals-by-vote>
    </vote-totals>
  </vote-metadata>
  <vote-data><recorded-vote><legislator>Example</legislator></recorded-vote></vote-data>
</rollcall-vote>
"""

BILL_RSS = """<?xml version="1.0"?>
<rss><channel>
<item>
  <guid>BILLS-119hr10890ih</guid>
  <title>H.R.&amp;nbsp;10890&amp;nbsp;(IH) - To amend the Internal Revenue Code.</title>
  <link>https://www.govinfo.gov/app/details/BILLS-119hr10890ih</link>
  <pubDate>Thu, 29 Oct 2026 03:39:03 +0000</pubDate>
</item>
<item>
  <guid>NOT-A-BILL</guid>
  <title>Ignore</title>
  <link>https://www.govinfo.gov/app/details/NOT-A-BILL</link>
  <pubDate>Thu, 29 Oct 2026 03:39:03 +0000</pubDate>
</item>
</channel></rss>
"""

MODS = """<?xml version="1.0"?>
<mods xmlns="http://www.loc.gov/mods/v3">
  <titleInfo><title>An act to provide for emergency alerts.</title></titleInfo>
  <extension>
    <dateIssued encoding="w3cdtf">2026-10-22</dateIssued>
    <shortTitle>Mystic Alerts Act</shortTitle>
    <bill congress="119" number="7022" type="HR" priority="primary"></bill>
  </extension>
</mods>
"""


class NormalizeTests(unittest.TestCase):
    def test_slip_opinion_uses_only_complete_rows(self):
        records = parse_slip_opinions(SLIP_HTML, 2026)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["date"], "2026-10-14")
        self.assertEqual(record["dateKind"], "decided")
        self.assertEqual(record["branch"], "judicial")
        self.assertEqual(record["officialUrl"], "https://www.supremecourt.gov/opinions/26pdf/26a476_k537.pdf")
        self.assertEqual(record["sourceText"], "The order is stayed.")
        self.assertIn("FCC v. Brown", record["title"])

    def test_house_vote_keeps_clerk_totals_and_url(self):
        record = parse_house_vote(HOUSE_XML.encode(), 2026)
        self.assertEqual(record["id"], "house-vote:119:2:314")
        self.assertEqual(record["date"], "2026-09-16")
        self.assertEqual(record["dateKind"], "voted")
        self.assertEqual(record["officialUrl"], "https://clerk.house.gov/Votes/2026314")
        self.assertIn("Yeas 401, Nays 14", record["detail"])
        self.assertIn("Passed", record["detail"])
        self.assertNotIn("Example", record["title"])

    def test_bill_rss_date_is_publication(self):
        items = parse_rss_items(BILL_RSS.encode())
        self.assertEqual(len(items), 2)
        record = bill_record(items[0])
        self.assertEqual(record["id"], "bill:119:hr:10890:ih")
        self.assertEqual(record["date"], "2026-10-29")
        self.assertEqual(record["dateKind"], "published")
        self.assertIsNone(bill_record(items[1]))
        self.assertIsNotNone(parse_bill_guid("BILLS-119hres1640ih"))
        self.assertIsNone(parse_bill_guid("BILLS-119zz10890ih"))

    def test_mods_becomes_a_law_row_without_guessing(self):
        package = parse_plaw_guid("PLAW-119publ136")
        mods = parse_mods(MODS.encode())
        row = law_row_from_mods(package, mods)
        self.assertEqual(row, [119, "pub", "119-136", "HR", "7022", "Mystic Alerts Act", "2026-10-22"])
        broken = dict(mods)
        broken["dateIssued"] = None
        self.assertIsNone(law_row_from_mods(package, broken))

    def test_known_law_uses_ledger_enactment_date(self):
        item = {
            "guid": "PLAW-119publ136",
            "title": "RSS title that is not the enactment date",
            "link": "https://www.govinfo.gov/app/details/PLAW-119publ136",
            "published": "2026-11-05",
        }
        row = [119, "pub", "119-136", "HR", "7022", "Mystic Alerts Act", "2026-10-22"]
        record = plaw_record_from_ledger(item, row)
        self.assertEqual(record["date"], "2026-10-22")
        self.assertEqual(record["dateKind"], "enacted")
        self.assertEqual(record["title"], "Mystic Alerts Act")

    def test_federal_register_rule_and_order(self):
        rule = federal_register_record({
            "title": "Example capital rule",
            "type": "Rule",
            "document_number": "2026-22741",
            "publication_date": "2026-11-06",
            "html_url": "https://www.federalregister.gov/documents/2026/11/06/2026-22741/example",
            "agencies": [{"name": "Securities and Exchange Commission"}],
            "citation": "91 FR 1",
        })
        self.assertEqual(rule["kind"], "rule")
        self.assertEqual(rule["branch"], "executive")
        self.assertEqual(rule["actor"], "Securities and Exchange Commission")
        self.assertEqual(rule["dateKind"], "published")
        stamped = federal_register_record({
            "title": "Example capital rule",
            "type": "Rule",
            "document_number": "2026-22741",
            "publication_date": "2026-11-06",
            "html_url": "https://www.federalregister.gov/documents/2026/11/06/2026-22741/example",
            "agencies": [{"name": "Securities and Exchange Commission"}],
            "president": {"identifier": "donald-trump", "name": "Donald Trump"},
        })
        self.assertEqual(stamped["actor"], "Securities and Exchange Commission")
        self.assertFalse(any("Trump" in str(value) for value in stamped.values()))
        order = {
            "title": "Decreasing Housing Costs for the American People",
            "type": "Presidential Document",
            "subtype": "Executive Order",
            "document_number": "2026-22051",
            "executive_order_number": "14438",
            "publication_date": "2026-10-28",
            "signing_date": "2026-10-22",
            "president": {"identifier": "donald-trump", "name": "Donald Trump"},
            "citation": "91 FR 68007",
            "html_url": "https://www.federalregister.gov/documents/2026/10/28/2026-22051/decreasing-housing-costs-for-the-american-people",
        }
        record = federal_register_record(order)
        self.assertEqual(record["kind"], "executive-order")
        self.assertEqual(record["date"], "2026-10-22")
        self.assertEqual(record["dateKind"], "signed")
        update = executive_order_update(order)
        self.assertEqual(update["number"], "14438")
        unsigned = dict(order)
        unsigned["signing_date"] = None
        self.assertIsNone(executive_order_update(unsigned))

    def test_rejects_non_https_and_bad_dates(self):
        self.assertIsNone(accept_record({
            "id": "fr:1",
            "branch": "executive",
            "kind": "rule",
            "date": "2026-11-06",
            "dateKind": "published",
            "title": "Example",
            "officialUrl": "ftp://example.com/nope",
            "officialId": "1",
            "source": "federal-register",
        }))
        self.assertIsNone(federal_register_record({
            "title": "Undated",
            "type": "Notice",
            "document_number": "2026-1",
            "html_url": "https://www.federalregister.gov/documents/x",
        }))

    def test_congress_bill_uses_latest_action_date(self):
        record = congress_bill_record({
            "congress": 119,
            "type": "S",
            "number": "2403",
            "title": "Retire through Ownership Act",
            "originChamber": "Senate",
            "latestAction": {"actionDate": "2026-09-16", "text": "Passed House"},
        })
        self.assertEqual(record["dateKind"], "acted")
        self.assertEqual(record["date"], "2026-09-16")
        self.assertTrue(record["officialUrl"].startswith("https://www.congress.gov/bill/119th-congress/senate-bill/2403"))
        self.assertIsNone(congress_bill_record({"congress": 119, "type": "S", "number": "1", "title": "No action"}))


class MergeTests(unittest.TestCase):
    def test_merge_keeps_records_missing_from_the_new_batch(self):
        existing = [{
            "id": "plaw:100-1",
            "branch": "legislative",
            "kind": "public-law",
            "date": "1987-01-01",
            "dateKind": "enacted",
            "title": "Old law",
            "officialUrl": "https://www.govinfo.gov/app/details/PLAW-100publ1",
            "officialId": "PLAW-100publ1",
            "source": "govinfo",
            "checked": "2026-11-01T00:00:00Z",
        }]
        incoming = [{
            "id": "fr:2026-1",
            "branch": "executive",
            "kind": "rule",
            "date": "2026-11-06",
            "dateKind": "published",
            "title": "New rule",
            "officialUrl": "https://www.federalregister.gov/documents/2026/11/06/2026-1/new-rule",
            "officialId": "2026-1",
            "source": "federal-register",
        }]
        merged, inserted, updated = merge_records(existing, incoming, "2026-11-07T00:00:00Z")
        ids = [record["id"] for record in merged]
        self.assertEqual(ids, ["fr:2026-1", "plaw:100-1"])
        self.assertEqual(inserted, 1)
        self.assertEqual(updated, 0)
        self.assertEqual(merged[1]["checked"], "2026-11-01T00:00:00Z")

    def test_laws_upsert_does_not_drop_or_rewrite_history(self):
        laws = {
            "generated": "2026-11-02",
            "congresses": {"119": 1},
            "rows": [[119, "pub", "119-1", "HR", "1", "First", "2026-01-02"]],
        }
        added = upsert_laws(laws, [
            [119, "pub", "119-1", "S", "9", "Should not replace", "2026-02-02"],
            [119, "pub", "119-2", "HR", "2", "Second", "2026-03-03"],
            [119, "priv", "119-1", "HR", "3", "Private", "2026-03-04"],
        ], "2026-11-07")
        self.assertEqual(added, 2)
        self.assertEqual(laws["rows"][0][1], "priv")
        self.assertEqual(laws["rows"][1][5], "Second")
        self.assertEqual(laws["rows"][2][5], "First")
        self.assertEqual(laws["congresses"]["119"], 3)
        self.assertEqual(len(laws["rows"]), 3)

    def test_executive_order_upsert_keeps_older_orders(self):
        eos = {
            "generated": "2026-11-02",
            "rows": [
                ["14438", "2026-10-22", "Old title", "donald-trump", "91 FR 1", "https://www.federalregister.gov/a", None],
                ["100", "1937-01-01", "Historical", "franklin-d-roosevelt", None, "https://www.archives.gov/x", None],
            ],
            "sources": ["https://www.federalregister.gov/developers/documentation/api/v1"],
        }
        changed = upsert_executive_orders(eos, [
            {
                "number": "14438",
                "signing_date": "2026-10-22",
                "title": "Updated title",
                "president": "donald-trump",
                "citation": "91 FR 68007",
                "url": "https://www.federalregister.gov/documents/2026/10/28/2026-22051/example",
            },
            {
                "number": "14439",
                "signing_date": "2026-11-01",
                "title": "New order",
                "president": "donald-trump",
                "citation": "91 FR 2",
                "url": "https://www.federalregister.gov/documents/2026/11/04/2026-1/new-order",
            },
        ], "2026-11-07")
        self.assertGreaterEqual(changed, 2)
        numbers = [row[0] for row in eos["rows"]]
        self.assertEqual(numbers, ["14439", "14438", "100"])
        self.assertEqual(eos["rows"][1][2], "Updated title")
        self.assertEqual(eos["rows"][2][2], "Historical")
        self.assertEqual(len(eos["rows"]), 3)


if __name__ == "__main__":
    unittest.main()
