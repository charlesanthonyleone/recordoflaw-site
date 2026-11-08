import assert from "node:assert/strict";
import test from "node:test";
import {
  FEDERAL_STALE_MS,
  STATE_INDEX_STALE_MS,
  assembleDesk,
  classifySource,
  classifyStateRow,
  filterFederal,
} from "../../assets/ledger-status.js";

const NOW = Date.parse("2026-11-08T12:00:00Z");

function source(partial) {
  return {
    id: "federal-register",
    label: "Federal Register API",
    ok: true,
    skipped: false,
    checked: "2026-11-08T10:00:00Z",
    upserted: 3,
    ...partial,
  };
}

test("a skipped key is not a down source", () => {
  assert.equal(classifySource(source({ id: "congress-gov", skipped: true, ok: true, upserted: 0 }), NOW), "skipped");
});

test("a failed source is down and a day-old success is stale", () => {
  assert.equal(classifySource(source({ ok: false, error: "HTTP 503" }), NOW), "down");
  assert.equal(classifySource(source({ checked: new Date(NOW - FEDERAL_STALE_MS - 1000).toISOString() }), NOW), "stale");
  assert.equal(classifySource(source(), NOW), "live");
});

test("federal lane fails visibly and does not call a skipped source a failure", () => {
  const down = assembleDesk({
    metaOk: true,
    meta: { federal: { lastChecked: "2026-11-08T10:00:00Z", recordCount: 4, sources: [source({ ok: false, error: "HTTP 503" }), source({ id: "congress-gov", label: "Congress.gov API", skipped: true })] } },
    statesOk: true,
    states: { updated: "2026-11-08T10:00:00Z", order: [], states: {}, recent: [] },
    now: NOW,
  });
  assert.equal(down.federal.status, "down");
  assert.match(down.federal.message, /Federal Register API/);
  assert.equal(down.federal.sources[1].health, "skipped");

  const stale = assembleDesk({
    metaOk: true,
    meta: { federal: { lastChecked: new Date(NOW - FEDERAL_STALE_MS - 5000).toISOString(), recordCount: 1, sources: [source({ checked: new Date(NOW - FEDERAL_STALE_MS - 5000).toISOString() })] } },
    statesOk: true,
    states: { updated: "2026-11-08T10:00:00Z", order: ["WA"], states: { WA: { adapter: "wa", recordCount: 2, lastChecked: "2026-11-08T10:00:00Z" } }, recent: [] },
    now: NOW,
  });
  assert.equal(stale.federal.status, "stale");
  assert.equal(stale.state.status, "live");
});

test("state index failure is down, and an old index is stale", () => {
  const missing = assembleDesk({ metaOk: true, meta: { federal: { lastChecked: "2026-11-08T10:00:00Z", sources: [source()] } }, statesOk: false, states: null, now: NOW });
  assert.equal(missing.state.status, "down");
  assert.match(missing.state.message, /could not be read/);

  const old = assembleDesk({
    metaOk: true,
    meta: { federal: { lastChecked: "2026-11-08T10:00:00Z", sources: [source()] } },
    statesOk: true,
    states: { updated: new Date(NOW - STATE_INDEX_STALE_MS - 1000).toISOString(), order: ["AL"], states: { AL: {} }, recent: [] },
    now: NOW,
  });
  assert.equal(old.state.status, "stale");
});

test("a state error beats an uncovered legislature", () => {
  const desk = assembleDesk({
    metaOk: true,
    meta: { federal: { lastChecked: "2026-11-08T10:00:00Z", sources: [source()] } },
    statesOk: true,
    states: {
      updated: "2026-11-08T10:00:00Z",
      order: ["WA", "AL"],
      states: {
        WA: { adapter: "wa", recordCount: 3, lastChecked: "2026-11-08T10:00:00Z", error: "timed out" },
        AL: { recordCount: 0 },
      },
      recent: [],
    },
    now: NOW,
  });
  assert.equal(desk.state.status, "down");
  assert.match(desk.state.message, /WA: timed out/);
  assert.equal(classifyStateRow(desk.state.states.AL, NOW), "unconfigured");
  assert.equal(desk.state.coverage.unconfigured, 1);
  assert.equal(desk.state.coverage.down, 1);
});

test("shared status stamp still speaks when the catalog is missing", () => {
  const desk = assembleDesk({
    metaOk: false,
    meta: null,
    statesOk: false,
    states: null,
    now: NOW,
  });
  assert.equal(desk.federal.status, "down");
  assert.equal(desk.state.status, "down");
});

test("federal search stays inside the loaded rows", () => {
  const records = [
    { id: "a", date: "2026-11-01", branch: "legislative", kind: "bill", title: "Farm bill" },
    { id: "b", date: "2026-11-02", branch: "judicial", kind: "slip-opinion", title: "Smith v. Jones" },
  ];
  const found = filterFederal(records, { filter: "mix", query: "smith", limit: 25 });
  assert.equal(found.matched, 1);
  assert.equal(found.shown[0].id, "b");
  const mix = filterFederal(records, { filter: "mix", query: "", limit: 25 });
  assert.equal(mix.shown.length, 2);
});
