"""The federal and state ingests must not erase each other's status."""

import unittest

from ledger_status import merge_meta, state_section


class MergeMetaTests(unittest.TestCase):
    def test_federal_write_keeps_state(self):
        existing = {"schema": 1, "federal": {"lastChecked": "old"}, "state": {"lastChecked": "state-old", "health": "ok"}}
        merged = merge_meta(existing, federal={"lastChecked": "new", "health": "ok"})
        self.assertEqual(merged["federal"]["lastChecked"], "new")
        self.assertEqual(merged["state"]["lastChecked"], "state-old")
        self.assertEqual(merged["schema"], 1)

    def test_state_write_keeps_federal(self):
        existing = {"federal": {"lastChecked": "fed"}, "state": {"lastChecked": "old"}}
        merged = merge_meta(existing, state={"lastChecked": "new", "health": "down", "failed": ["WA"]})
        self.assertEqual(merged["federal"]["lastChecked"], "fed")
        self.assertEqual(merged["state"]["failed"], ["WA"])

    def test_ignores_non_dicts(self):
        self.assertEqual(merge_meta(None), {"schema": 1})
        self.assertEqual(merge_meta({"federal": "nope", "state": []}), {"schema": 1})


class StateSectionTests(unittest.TestCase):
    def test_counts_and_failure(self):
        section = state_section({
            "updated": "2026-11-07T04:34:29Z",
            "workflow": "https://example.test/state",
            "order": ["WA", "TX", "AL"],
            "openStates": {"used": False},
            "states": {
                "WA": {"recordCount": 10, "error": None},
                "TX": {"recordCount": 0, "error": "timed out"},
                "AL": {"recordCount": 0, "error": None},
            },
        })
        self.assertEqual(section["lastChecked"], "2026-11-07T04:34:29Z")
        self.assertEqual(section["recordCount"], 10)
        self.assertEqual(section["coveredCount"], 1)
        self.assertEqual(section["failed"], ["TX"])
        self.assertEqual(section["unconfiguredCount"], 1)
        self.assertEqual(section["health"], "down")
        self.assertEqual(section["index"], "/ledger/states-meta.json")

    def test_ok_when_nothing_failed(self):
        section = state_section({"updated": "2026-11-07T00:00:00Z", "order": ["WA"], "states": {"WA": {"recordCount": 2}}})
        self.assertEqual(section["health"], "ok")
        self.assertEqual(section["failed"], [])


if __name__ == "__main__":
    unittest.main()
