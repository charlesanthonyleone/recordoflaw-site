/**
 * One read path for the federal and state ledgers.
 *
 * readLedgerDesk() loads ledger/meta.json (shared status) and
 * ledger/states-meta.json (state catalog) together. Federal rows and a
 * single state's file are loaded from here too, only when a tab asks.
 * Both tabs render whatever this module returns. Nothing else fetches
 * these files.
 *
 * Freshness is judged at read time. A source that answered the last ingest
 * is still stale once the file is older than the ingest window.
 */

export const FEDERAL_STALE_MS = 36 * 60 * 60 * 1000;
export const STATE_INDEX_STALE_MS = 48 * 60 * 60 * 1000;
export const STATE_ROW_STALE_MS = 4 * 24 * 60 * 60 * 1000;

export const FEDERAL_WORKFLOW =
  "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/federal-sync.yml";
export const STATE_WORKFLOW =
  "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/state-ledger.yml";

export const KIND_LABEL = {
  "public-law": "Public law",
  "private-law": "Private law",
  bill: "Bill",
  "house-vote": "House vote",
  "senate-vote": "Senate vote",
  rule: "Final rule",
  "proposed-rule": "Proposed rule",
  notice: "Notice",
  "presidential-document": "Presidential document",
  "executive-order": "Executive order",
  proclamation: "Proclamation",
  "slip-opinion": "Slip opinion",
  opinion: "Opinion",
};

export const DATE_LABEL = {
  enacted: "enacted",
  signed: "signed",
  published: "published",
  voted: "voted",
  decided: "decided",
  acted: "latest action",
  approved: "approved",
  effective: "effective",
  presentment: "presented",
  "last-action": "last action",
  status: "status date",
  action: "action",
};

export function ageMs(iso, now) {
  if (!iso) return null;
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) return null;
  return now - parsed;
}

export function httpsUrl(value) {
  if (typeof value !== "string" || !value.startsWith("https://")) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

export function formatStamp(iso) {
  if (!iso) return "not yet checked";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "unreadable timestamp";
  return parsed.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";
}

export function formatDay(iso) {
  if (!iso) return "date not stated";
  const day = String(iso).slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) return String(iso);
  const parsed = new Date(`${day}T00:00:00Z`);
  return parsed.toLocaleDateString("en-US", { timeZone: "UTC", year: "numeric", month: "short", day: "numeric" });
}

export function classifySource(source, now) {
  if (!source || typeof source !== "object") return "down";
  if (source.skipped) return "skipped";
  if (!source.ok) return "down";
  const age = ageMs(source.checked, now);
  if (age == null || age > FEDERAL_STALE_MS) return "stale";
  return "live";
}

export function classifyStateRow(row, now) {
  if (!row || typeof row !== "object") return "unconfigured";
  if (row.error) return "down";
  const count = Number(row.recordCount) || 0;
  const checked = row.lastChecked || row.lastSynced || null;
  if (!row.adapter && count === 0) return "unconfigured";
  const age = ageMs(checked, now);
  if (age == null) return count ? "stale" : "unconfigured";
  if (age > STATE_ROW_STALE_MS) return "stale";
  return "live";
}

export function coverageCounts(statesMap, order, now) {
  const counts = { live: 0, stale: 0, down: 0, unconfigured: 0, total: 0, withRecords: 0, records: 0 };
  const codes = Array.isArray(order) && order.length ? order : Object.keys(statesMap || {});
  counts.total = codes.length;
  for (const code of codes) {
    const row = (statesMap || {})[code];
    counts[classifyStateRow(row, now)] += 1;
    const count = Number(row && row.recordCount) || 0;
    if (count > 0) counts.withRecords += 1;
    counts.records += count;
  }
  return counts;
}

export function matchesFederal(record, filter) {
  if (!record) return false;
  if (filter === "legislative") return record.branch === "legislative";
  if (filter === "judicial") return record.branch === "judicial";
  if (filter === "rules") return record.kind === "rule" || record.kind === "proposed-rule";
  if (filter === "notices") return record.kind === "notice";
  if (filter === "presidential") {
    return record.kind === "executive-order" || record.kind === "proclamation" || record.kind === "presidential-document";
  }
  return true;
}

export function byDate(records) {
  return records.slice().sort((a, b) => {
    const ad = a.date || "";
    const bd = b.date || "";
    if (ad === bd) return String(a.id) < String(b.id) ? -1 : String(a.id) > String(b.id) ? 1 : 0;
    return ad < bd ? 1 : -1;
  });
}

export function balanced(records) {
  const sorted = byDate(records);
  const groups = [
    sorted.filter((record) => record.branch === "legislative").slice(0, 8),
    sorted.filter((record) => record.kind === "rule" || record.kind === "proposed-rule").slice(0, 8),
    sorted.filter((record) => record.kind === "notice").slice(0, 4),
    sorted.filter((record) => matchesFederal(record, "presidential")).slice(0, 6),
    sorted.filter((record) => record.branch === "judicial").slice(0, 8),
  ];
  const seen = new Set();
  const picked = [];
  for (const group of groups) {
    for (const record of group) {
      if (!seen.has(record.id)) {
        seen.add(record.id);
        picked.push(record);
      }
    }
  }
  return byDate(picked);
}

export function filterFederal(records, { filter = "mix", query = "", limit = 25 } = {}) {
  const needle = String(query || "").trim().toLowerCase();
  let rows = Array.isArray(records) ? records : [];
  if (needle) {
    rows = rows.filter((record) =>
      [record.title, record.citation, record.officialId, record.actor, record.detail, record.id]
        .filter(Boolean)
        .some((part) => String(part).toLowerCase().includes(needle))
    );
  }
  if ((filter === "mix" || !filter) && !needle) {
    const shown = balanced(rows);
    return { shown, matched: rows.length, capped: false };
  }
  const matchedRows = byDate(rows.filter((record) => matchesFederal(record, filter === "mix" ? "all" : filter)));
  return { shown: matchedRows.slice(0, limit), matched: matchedRows.length, capped: matchedRows.length > limit };
}

export function federalCountLine(records) {
  const counts = { Congress: 0, "Agency rules": 0, Notices: 0, Presidential: 0, Courts: 0 };
  for (const record of records || []) {
    if (record.branch === "legislative") counts.Congress += 1;
    else if (record.branch === "judicial") counts.Courts += 1;
    else if (record.kind === "notice") counts.Notices += 1;
    else if (matchesFederal(record, "presidential")) counts.Presidential += 1;
    else if (record.kind === "rule" || record.kind === "proposed-rule") counts["Agency rules"] += 1;
  }
  return Object.entries(counts)
    .map(([label, count]) => `${count.toLocaleString("en-US")} ${label}`)
    .join(" · ");
}

export function assembleDesk({ meta, metaOk, states, statesOk, now }) {
  const federalMeta = metaOk && meta && typeof meta.federal === "object" ? meta.federal : null;
  const stateSummary = metaOk && meta && typeof meta.state === "object" ? meta.state : null;
  const sources = Array.isArray(federalMeta?.sources)
    ? federalMeta.sources.map((source) => ({ ...source, health: classifySource(source, now) }))
    : [];

  let federalStatus = "live";
  let federalMessage = "";
  if (!metaOk) {
    federalStatus = "down";
    federalMessage = "The shared ledger status file could not be read. Freshness of the federal sources is unknown.";
  } else if (!federalMeta) {
    federalStatus = "down";
    federalMessage = "Federal status is missing from the shared ledger status file.";
  } else if (sources.some((source) => source.health === "down")) {
    federalStatus = "down";
    const names = sources.filter((source) => source.health === "down").map((source) => source.label || source.id);
    federalMessage = `${names.join(", ")} ${names.length === 1 ? "was" : "were"} not reached on the last check. Rows below are the last copy on file.`;
  } else if ((ageMs(federalMeta.lastChecked, now) ?? Infinity) > FEDERAL_STALE_MS) {
    federalStatus = "stale";
    federalMessage = "Federal sources were last checked more than 36 hours ago. Rows below are the last copy on file, not a fresh read.";
  }

  const index = statesOk && states && typeof states === "object" ? states : null;
  const statesMap = index && typeof index.states === "object" ? index.states : {};
  const order = index && Array.isArray(index.order) ? index.order : [];
  const coverage = index ? coverageCounts(statesMap, order, now) : null;

  let stateStatus = "live";
  let stateMessage = "";
  let stateChecked = index?.updated || null;
  if (!index) {
    if (stateSummary && stateSummary.lastChecked) {
      stateChecked = stateSummary.lastChecked;
      stateStatus = stateSummary.health === "down" ? "down" : "stale";
      stateMessage = "The state catalog could not be read. The shared status file still has a state stamp, so this ledger is not treated as current.";
    } else {
      stateStatus = "down";
      stateMessage = "The state ledger index could not be read.";
    }
  } else {
    const stale = (ageMs(index.updated, now) ?? Infinity) > STATE_INDEX_STALE_MS;
    const failed = Object.entries(statesMap).filter(([, row]) => row && row.error);
    if (stale) {
      stateStatus = "stale";
      stateMessage = "The state index was last updated more than 48 hours ago. Bills may have been enacted since that check.";
    }
    if (failed.length) {
      stateStatus = "down";
      const detail = failed.map(([code, row]) => `${code}: ${row.error}`).join("; ");
      stateMessage = `A state source failed on the last ingest. ${detail}`;
      if (stale) stateMessage += " The index is also older than 48 hours.";
    }
  }

  return {
    now,
    federal: {
      status: federalStatus,
      message: federalMessage,
      lastChecked: federalMeta?.lastChecked || null,
      recordCount: federalMeta?.recordCount ?? null,
      workflow: httpsUrl(federalMeta?.workflow) || FEDERAL_WORKFLOW,
      sources,
      skipped: sources.filter((source) => source.health === "skipped"),
    },
    state: {
      status: stateStatus,
      message: stateMessage,
      lastChecked: stateChecked,
      recordCount: coverage ? coverage.records : stateSummary?.recordCount ?? null,
      coveredCount: coverage ? coverage.withRecords : stateSummary?.coveredCount ?? null,
      workflow: httpsUrl(index?.workflow) || httpsUrl(stateSummary?.workflow) || STATE_WORKFLOW,
      description: index?.description || "",
      openStates: index?.openStates || stateSummary?.openStates || null,
      order,
      states: statesMap,
      recent: index && Array.isArray(index.recent) ? index.recent : [],
      coverage,
      catalog: !!index,
    },
  };
}

export async function fetchJson(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, { cache: "no-store", signal: controller.signal });
    if (!response.ok) return { ok: false, data: null };
    try {
      return { ok: true, data: await response.json() };
    } catch {
      return { ok: false, data: null };
    }
  } catch {
    return { ok: false, data: null };
  } finally {
    clearTimeout(timer);
  }
}

export function loadStatusFiles(now = Date.now()) {
  return Promise.all([
    fetchJson(`/ledger/meta.json?t=${now}`),
    fetchJson(`/ledger/states-meta.json?t=${now}`),
  ]).then(([meta, states]) => ({
    meta: meta.data,
    metaOk: meta.ok,
    states: states.data,
    statesOk: states.ok,
  }));
}

export function loadFederalFile(now = Date.now()) {
  return fetchJson(`/ledger/federal-live.json?t=${now}`);
}

export function loadStateFile(code, now = Date.now()) {
  const safe = String(code || "").toLowerCase();
  if (!/^[a-z]{2}$/.test(safe)) return Promise.resolve({ ok: false, data: null });
  return fetchJson(`/ledger/states/${safe}.json?t=${now}`);
}
