"""Offline checks for merge behavior and source-classification rules."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adapters import enacted_action, official_source  # noqa: E402
from merge import bill_spaced, iso_date, make_record, merge_records, record_id  # noqa: E402


def sample(identifier, title, date="2024-01-02"):
    return make_record(
        state="TX",
        session="88R",
        identifier=identifier,
        title=title,
        status="signed",
        statusLabel="Signed by the governor",
        date=date,
        dateKind="last-action",
        officialUrl="https://capitol.texas.gov/BillLookup/History.aspx?LegSess=88R&Bill=HB1",
        sources=[{"label": "Bill history", "url": "https://capitol.texas.gov/", "publisher": "Texas Legislature"}],
    )


class MergeTests(unittest.TestCase):
    def test_keeps_history_missing_from_the_new_pull(self):
        older = sample("HB 1", "Older law", "2020-05-01")
        newer = sample("HB 2", "New law", "2025-06-01")
        merged = merge_records([older], [newer])
        ids = {row["id"] for row in merged}
        self.assertEqual(ids, {record_id("TX", "88R", "HB 1"), record_id("TX", "88R", "HB 2")})

    def test_upserts_same_official_id(self):
        original = sample("HB 1", "Short title")
        revised = sample("HB 1", "Corrected title from the legislature")
        merged = merge_records([original], [revised])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["title"], "Corrected title from the legislature")

    def test_empty_pull_does_not_delete(self):
        original = sample("HB 1", "Still on the books")
        self.assertEqual(merge_records([original], []), [original])

    def test_dates_only_when_the_source_states_one(self):
        self.assertEqual(iso_date("06/20/2025 E Effective immediately"), "2025-06-20")
        self.assertEqual(iso_date("Approved by the Governor, February 28, 2025"), "2025-02-28")
        self.assertEqual(iso_date("2026-03-05T00:00:00"), "2026-03-05")
        self.assertIsNone(iso_date("Effective immediately"))
        self.assertIsNone(iso_date(""))

    def test_bill_number_spacing(self):
        self.assertEqual(bill_spaced("SF1552"), "SF 1552")
        self.assertEqual(bill_spaced("HB 6"), "HB 6")


class OpenStatesFilterTests(unittest.TestCase):
    def test_requires_became_law_or_signature_classification(self):
        actions = [
            {"description": "Referred to committee", "classification": ["referral-committee"], "date": "2025-01-01"},
            {"description": "Signed by Governor", "classification": ["executive-signature"], "date": "2025-05-02"},
        ]
        self.assertEqual(enacted_action(actions)["date"], "2025-05-02")
        self.assertIsNone(enacted_action([{"description": "Sent to governor", "classification": ["executive-receipt"]}]))

    def test_prefers_became_law_over_signature(self):
        actions = [
            {"description": "Signed", "classification": ["executive-signature"], "date": "2025-05-01"},
            {"description": "Chaptered", "classification": ["became-law"], "date": "2025-05-02"},
        ]
        self.assertEqual(enacted_action(actions)["description"], "Chaptered")

    def test_skips_bills_without_an_official_url(self):
        bill = {"sources": [{"url": "https://openstates.org/tx/bills/hb1/"}]}
        self.assertIsNone(official_source(bill))
        bill["sources"].append({"url": "https://capitol.texas.gov/BillLookup/History.aspx?LegSess=89R&Bill=HB1"})
        self.assertIn("capitol.texas.gov", official_source(bill))


if __name__ == "__main__":
    unittest.main()
