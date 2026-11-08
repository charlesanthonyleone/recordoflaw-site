import { g as useSearchParams, j as e, r as React, L as Link } from "./react-8qEOpjgC.js";
import {
  KIND_LABEL,
  DATE_LABEL,
  assembleDesk,
  classifyStateRow,
  federalCountLine,
  filterFederal,
  formatDay,
  formatStamp,
  httpsUrl,
  loadFederalFile,
  loadStateFile,
  loadStatusFiles,
} from "./ledger-status.js";

const CSS = `
.ledger .ledger-tabs{flex-wrap:wrap;row-gap:6px}
.desk-status{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;align-items:stretch;margin:12px 0 8px}
.desk-lane{border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:10px 12px;background:rgba(6,22,40,.55)}
.desk-lane h2{font-family:var(--font);font-size:15px;margin:6px 0 2px;letter-spacing:0;text-transform:none}
.desk-live{border-color:rgba(74,222,128,.45)}
.desk-stale{border-color:rgba(251,191,36,.75);background:rgba(120,80,10,.28)}
.desk-down{border-color:rgba(248,113,113,.85);background:rgba(90,16,16,.38)}
.desk-pill{display:inline-block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;padding:1px 7px;border-radius:999px;border:1px solid transparent}
.desk-live .desk-pill,.desk-pill.live{background:#14532d;color:#bbf7d0}
.desk-stale .desk-pill,.desk-pill.stale{background:#854d0e;color:#fde68a}
.desk-down .desk-pill,.desk-pill.down{background:#7f1d1d;color:#fecaca}
.desk-pill.skipped,.desk-pill.unconfigured{background:rgba(255,255,255,.08);color:var(--muted)}
.desk-actions{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin:0 0 8px}
.desk-actions button,.desk-textbtn{padding:6px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.18);background:transparent;color:inherit;cursor:pointer}
.desk-actions button:disabled{opacity:.6;cursor:progress}
.desk-alert{border-left:3px solid #f87171;background:#f871711c;padding:10px 14px;border-radius:8px;margin:8px 0}
.desk-alert.stale{border-left-color:#fbbf24;background:#fbbf2418}
.desk-split{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(260px,.85fr);gap:16px;align-items:start}
.desk-side{position:sticky;top:12px;border:1px solid rgba(231,198,117,.28);border-radius:12px;padding:12px 14px;background:rgba(6,22,40,.55)}
.desk-side h2{font-size:1.05rem;margin-top:0}
.desk-side ol{margin:8px 0 0;padding-left:1.15em}
.desk-side li{margin:0 0 10px}
.desk-filters{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.desk-filters button{padding:6px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.15);background:transparent;color:inherit;cursor:pointer}
.desk-filters button[aria-pressed="true"]{border-color:#e7c675;color:#f3e2b3;background:#e7c6751f}
.desk-src{width:100%;border-collapse:collapse;font-size:13px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:900px){.desk-status,.desk-split{grid-template-columns:1fr}.desk-side{position:static}.desk-actions{align-items:flex-start}}
`;

if (typeof document !== "undefined" && !document.getElementById("rol-ledger-desk-style")) {
  const style = document.createElement("style");
  style.id = "rol-ledger-desk-style";
  style.textContent = CSS;
  document.head.appendChild(style);
}

const FILTERS = [
  ["mix", "Recent mix"],
  ["legislative", "Congress"],
  ["rules", "Agency rules"],
  ["notices", "Notices"],
  ["presidential", "Presidential"],
  ["judicial", "Courts"],
];

const HEALTH_LABEL = { live: "Current", stale: "Stale", down: "Down", skipped: "Not configured", unconfigured: "Not covered" };

const listeners = new Set();
const mem = {
  meta: null,
  metaOk: null,
  states: null,
  statesOk: null,
  federal: null,
  federalOk: null,
  federalLoading: false,
  files: {},
  fileLoading: {},
  refreshing: false,
};
let statusPromise = null;
let federalPromise = null;
const filePromises = {};

function emit() {
  for (const fn of listeners) fn();
}

function loadStatus(force) {
  if (!force && mem.metaOk != null && mem.statesOk != null) return Promise.resolve();
  if (statusPromise) return force ? statusPromise.then(() => loadStatus(true)) : statusPromise;
  statusPromise = (async () => {
    const result = await loadStatusFiles();
    mem.meta = result.meta;
    mem.metaOk = result.metaOk;
    mem.states = result.states;
    mem.statesOk = result.statesOk;
    emit();
  })().finally(() => {
    statusPromise = null;
  });
  return statusPromise;
}

function loadFederal(force) {
  if (!force && mem.federalOk != null) return Promise.resolve();
  if (federalPromise) return force ? federalPromise.then(() => loadFederal(true)) : federalPromise;
  mem.federalLoading = true;
  emit();
  federalPromise = (async () => {
    const result = await loadFederalFile();
    mem.federal = result.data;
    mem.federalOk = !!(result.ok && result.data && Array.isArray(result.data.records));
  })().finally(() => {
    mem.federalLoading = false;
    federalPromise = null;
    emit();
  });
  return federalPromise;
}

function loadFile(code, force) {
  if (!force && mem.files[code]) return Promise.resolve();
  if (filePromises[code]) return force ? filePromises[code].then(() => loadFile(code, true)) : filePromises[code];
  mem.fileLoading[code] = true;
  emit();
  filePromises[code] = (async () => {
    const result = await loadStateFile(code);
    mem.files[code] = result.ok && result.data ? { ok: true, data: result.data } : { ok: false, data: null };
  })().finally(() => {
    mem.fileLoading[code] = false;
    delete filePromises[code];
    emit();
  });
  return filePromises[code];
}

function shouldSkipState(code) {
  if (!code || !mem.statesOk) return false;
  const row = mem.states?.states?.[code];
  return classifyStateRow(row, Date.now()) === "unconfigured";
}

export function useLedgerDesk({ federalRecords = false, stateCode = "" } = {}) {
  const [, setTick] = React.useState(0);
  React.useEffect(() => {
    const fn = () => setTick((n) => n + 1);
    listeners.add(fn);
    let cancel = false;
    void (async () => {
      await loadStatus(false);
      if (cancel) return;
      if (federalRecords) await loadFederal(false);
      if (stateCode && !shouldSkipState(stateCode)) await loadFile(stateCode, false);
    })();
    return () => {
      cancel = true;
      listeners.delete(fn);
    };
  }, [federalRecords, stateCode]);

  const desk = mem.metaOk == null && mem.statesOk == null
    ? null
    : assembleDesk({
        meta: mem.meta,
        metaOk: !!mem.metaOk,
        states: mem.states,
        statesOk: !!mem.statesOk,
        now: Date.now(),
      });
  const file = mem.files[stateCode];

  async function refresh() {
    mem.refreshing = true;
    emit();
    await loadStatus(true);
    const jobs = [];
    if (mem.federalOk != null || federalRecords) jobs.push(loadFederal(true));
    const codes = new Set(Object.keys(mem.files));
    if (stateCode) codes.add(stateCode);
    for (const code of codes) {
      if (!shouldSkipState(code)) jobs.push(loadFile(code, true));
    }
    await Promise.all(jobs);
    mem.refreshing = false;
    emit();
  }

  return {
    loading: mem.metaOk == null || mem.statesOk == null,
    refreshing: mem.refreshing,
    desk,
    records: mem.federalOk ? mem.federal.records : null,
    recordsLoading: mem.federalLoading,
    recordsError: mem.federalOk === false,
    stateFile: file && file.ok ? file.data : null,
    stateFileError: !!(file && !file.ok),
    stateFileLoading: !!mem.fileLoading[stateCode],
    refresh,
  };
}

function Ext({ href, children }) {
  const safe = httpsUrl(href);
  if (!safe) return e.jsx("span", { children });
  return e.jsx("a", { href: safe, target: "_blank", rel: "noreferrer", children });
}

function Alert({ status, message }) {
  if (!message || status === "live") return null;
  return e.jsx("div", { className: `desk-alert${status === "stale" ? " stale" : ""}`, role: "alert", children: message });
}

export function LedgerStatus() {
  const model = useLedgerDesk();
  const { desk, loading, refreshing, refresh } = model;
  if (loading || !desk) {
    return e.jsx("p", { className: "muted", children: "Reading ledger status…" });
  }
  return e.jsxs(e.Fragment, {
    children: [
      e.jsxs("section", {
        "aria-label": "Ledger freshness",
        children: [
          e.jsxs("div", {
            className: "desk-status",
            "aria-live": "polite",
            children: [
              Lane({
                title: "Federal ledger",
                status: desk.federal.status,
                checked: desk.federal.lastChecked,
                detail: federalDetail(desk.federal),
                href: "/wiki/ledger?tab=live",
              }),
              Lane({
                title: "State ledger",
                status: desk.state.status,
                checked: desk.state.lastChecked,
                detail: stateDetail(desk.state),
                href: "/wiki/ledger?tab=state",
              }),
            ],
          }),
          e.jsxs("div", {
            className: "desk-actions",
            children: [
              e.jsx("button", { type: "button", onClick: () => void refresh(), disabled: refreshing, children: refreshing ? "Re-reading…" : "Re-read ledgers" }),
              e.jsx("span", { className: "muted small", children: "Re-read loads the files on this site. Official sources are checked by the scheduled ingest." }),
            ],
          }),
        ],
      }),
      e.jsx(Alert, { status: desk.federal.status, message: desk.federal.message }),
      e.jsx(Alert, { status: desk.state.status, message: desk.state.message }),
    ],
  });
}

function Lane({ title, status, checked, detail, href }) {
  const current = typeof location === "undefined" ? "" : (new URLSearchParams(location.search).get("tab") || "laws");
  const target = new URLSearchParams((href.split("?")[1] || "")).get("tab") || "laws";
  return e.jsxs("div", {
    className: `desk-lane desk-${status}`,
    children: [
      e.jsx("span", { className: "desk-pill", children: HEALTH_LABEL[status] || status }),
      e.jsx("h2", { children: title }),
      e.jsxs("p", { className: "small", style: { margin: "2px 0" }, children: ["Last checked ", e.jsx("time", { dateTime: checked || undefined, children: formatStamp(checked) }), "."] }),
      e.jsx("p", { className: "muted small", style: { margin: "2px 0 6px" }, children: detail }),
      current === target ? null : e.jsx(Link, { to: href, children: "Open" }),
    ],
  });
}

function federalDetail(federal) {
  const reached = federal.sources.filter((source) => source.health === "live" || source.health === "stale").length;
  const skipped = federal.sources.filter((source) => source.health === "skipped").length;
  const down = federal.sources.filter((source) => source.health === "down").length;
  const bits = [];
  if (federal.recordCount != null) bits.push(`${Number(federal.recordCount).toLocaleString("en-US")} records`);
  if (federal.sources.length) bits.push(`${reached} sources reached`);
  if (down) bits.push(`${down} down`);
  if (skipped) bits.push(`${skipped} not configured`);
  return bits.join(" · ") || "No source report in the status file.";
}

function stateDetail(state) {
  if (!state.catalog && state.recordCount == null) return "State catalog unavailable.";
  const covered = state.coveredCount ?? 0;
  const records = state.recordCount ?? 0;
  const unconfigured = state.coverage?.unconfigured;
  const bits = [`${covered} states with enacted laws`, `${Number(records).toLocaleString("en-US")} records`];
  if (unconfigured) bits.push(`${unconfigured} legislatures not in the direct-source batch`);
  return bits.join(" · ");
}

function laneName(record) {
  if (record.branch === "judicial") return "Court";
  if (record.branch === "legislative") return "Congress";
  if (record.kind === "executive-order" || record.kind === "proclamation" || record.kind === "presidential-document") return "Presidential";
  return "Agency";
}

export function FederalTab({ tabs }) {
  const [params, setParams] = useSearchParams();
  const model = useLedgerDesk({ federalRecords: true });
  const filter = params.get("ff") || "mix";
  const query = params.get("fq") || "";
  const [limit, setLimit] = React.useState(25);
  React.useEffect(() => setLimit(25), [filter, query]);
  const rows = model.records || [];
  const slice = filterFederal(rows, { filter, query, limit });

  function setParam(key, value) {
    const next = new URLSearchParams(params);
    next.set("tab", "live");
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  function openState(code) {
    const next = new URLSearchParams();
    next.set("tab", "state");
    if (code) next.set("st", code);
    setParams(next);
  }

  return e.jsxs("div", {
    className: "page ledger",
    children: [
      e.jsx("p", { className: "eyebrow", children: "Law ledger" }),
      e.jsx("h1", { children: "Federal activity" }),
      e.jsx("p", {
        className: "lede",
        children: "Public laws, bills, House votes, Federal Register documents, and Supreme Court slip opinions, merged by official identifier. Each row links to the document it was taken from. The statute and executive-order tabs keep the historical record; this list is what the sync has checked.",
      }),
      tabs,
      e.jsx(LedgerStatus, {}),
      model.recordsError && e.jsx("div", { className: "desk-alert", role: "alert", children: "The federal activity file could not be read. Source status above is from the last status file that did load." }),
      e.jsxs("div", {
        className: "desk-split",
        children: [
          e.jsxs("div", {
            children: [
              e.jsxs("div", {
                className: "ledger-ctl glass",
                children: [
                  e.jsx("input", {
                    type: "search",
                    placeholder: "Search title, citation, or identifier…",
                    value: query,
                    "aria-label": "Search federal activity",
                    onChange: (event) => setParam("fq", event.target.value),
                  }),
                  e.jsx("a", { href: model.desk?.federal.workflow, target: "_blank", rel: "noreferrer", children: "Check federal sources" }),
                ],
              }),
              e.jsx("div", {
                className: "desk-filters",
                role: "toolbar",
                "aria-label": "Federal activity",
                children: FILTERS.map(([id, label]) =>
                  e.jsx("button", {
                    type: "button",
                    "aria-pressed": filter === id,
                    onClick: () => setParam("ff", id === "mix" ? "" : id),
                    children: label,
                  }, id)
                ),
              }),
              e.jsx("p", {
                className: "muted small",
                children: model.recordsLoading
                  ? "Loading federal rows…"
                  : rows.length
                    ? `${federalCountLine(rows)}. ${rows.length.toLocaleString("en-US")} records in the live file.`
                    : model.recordsError
                      ? "Federal rows are unavailable."
                      : "No federal rows have been synced yet.",
              }),
              FederalTable({ shown: slice.shown, empty: query || filter !== "mix" ? "Nothing in this slice." : "No federal rows to show." }),
              slice.capped && e.jsx("div", {
                className: "pager",
                children: e.jsx("button", { type: "button", onClick: () => setLimit((n) => n + 25), children: `Show more (${slice.shown.length} of ${slice.matched})` }),
              }),
            ],
          }),
          e.jsx(StateFeed, { desk: model.desk, onOpen: openState }),
        ],
      }),
      e.jsx(SourceTable, { sources: model.desk?.federal.sources || [] }),
      (model.desk?.federal.skipped || []).length > 0 && e.jsxs("div", {
        className: "gap-note",
        role: "note",
        children: [
          e.jsx("b", { children: "Not configured. " }),
          "These sources are skipped, not reported as down. ",
          model.desk.federal.skipped.map((source) => source.note || source.label).filter(Boolean).join(" "),
        ],
      }),
      e.jsx("p", {
        className: "small",
        children: e.jsxs(e.Fragment, {
          children: [
            "Court roster: ",
            e.jsx(Link, { to: "/wiki/court", children: "Federal courts" }),
            ". How a bill moves: ",
            e.jsx(Link, { to: "/wiki/congress", children: "Congress" }),
            ".",
          ],
        }),
      }),
    ],
  });
}

function StateFeed({ desk, onOpen }) {
  const recent = (desk?.state.recent || []).slice(0, 8);
  return e.jsxs("aside", {
    className: "desk-side",
    "aria-label": "State enactments",
    children: [
      e.jsx("h2", { children: "State enactments" }),
      e.jsx("p", {
        className: "muted small",
        children: desk
          ? `State index last checked ${formatStamp(desk.state.lastChecked)}.`
          : "State index not loaded yet.",
      }),
      !recent.length && e.jsx("p", { className: "empty", children: desk?.state.catalog ? "No dated state records are in the index yet." : "The state feed cannot be shown until the index loads." }),
      recent.length > 0 && e.jsx("ol", {
        children: recent.map((record) => e.jsxs("li", {
          children: [
            e.jsxs("div", { className: "small", children: [record.state || "", record.identifier ? ` · ${record.identifier}` : ""] }),
            e.jsx(Ext, { href: record.officialUrl, children: record.title || "Untitled" }),
            e.jsx("div", { className: "muted small", children: formatDay(record.date) }),
            record.state && e.jsx("button", { type: "button", className: "linkish", onClick: () => onOpen(record.state), children: `Open ${record.state}` }),
          ],
        }, record.id || `${record.state}-${record.identifier}`)),
      }),
      e.jsx("p", { children: e.jsx("button", { type: "button", className: "desk-textbtn", onClick: () => onOpen(""), children: "All states" }) }),
    ],
  });
}

function FederalTable({ shown, empty }) {
  return e.jsx("div", {
    className: "table-wrap",
    children: e.jsxs("table", {
      className: "ledger-table",
      children: [
        e.jsx("caption", { className: "sr-only", children: "Recent federal activity with official source links" }),
        e.jsx("thead", {
          children: e.jsxs("tr", {
            children: ["Date", "Where", "Kind", "Record", "Official source"].map((label) => e.jsx("th", { children: label }, label)),
          }),
        }),
        e.jsx("tbody", {
          children: shown.length
            ? shown.map((record) => {
                const href = httpsUrl(record.officialUrl);
                return e.jsxs("tr", {
                  children: [
                    e.jsxs("td", { className: "nowrap", children: [formatDay(record.date), e.jsx("div", { className: "muted small", children: DATE_LABEL[record.dateKind] || record.dateKind || "" })] }),
                    e.jsx("td", { className: "nowrap", children: laneName(record) }),
                    e.jsx("td", { className: "nowrap", children: KIND_LABEL[record.kind] || record.kind || "" }),
                    e.jsxs("td", {
                      children: [
                        href ? e.jsx("a", { href, target: "_blank", rel: "noreferrer", children: record.title || record.officialId || "Official record" }) : (record.title || "Untitled"),
                        e.jsx("div", { className: "muted small", children: [record.citation, record.actor, record.detail].filter(Boolean).join(" · ") }),
                      ],
                    }),
                    e.jsx("td", { className: "nowrap", children: href ? e.jsx("a", { href, target: "_blank", rel: "noreferrer", children: "Verify" }) : "—" }),
                  ],
                }, record.id);
              })
            : e.jsx("tr", { children: e.jsx("td", { colSpan: 5, children: e.jsx("p", { className: "empty", children: empty }) }) }),
        }),
      ],
    }),
  });
}

function SourceTable({ sources }) {
  if (!sources.length) return null;
  return e.jsxs(e.Fragment, {
    children: [
      e.jsx("h2", { children: "Sources checked" }),
      e.jsx("div", {
        className: "table-wrap",
        children: e.jsxs("table", {
          className: "ledger-table desk-src",
          children: [
            e.jsx("caption", { className: "sr-only", children: "Official sources and whether the last check reached them" }),
            e.jsx("thead", {
              children: e.jsxs("tr", {
                children: ["Source", "Status", "Records", "Note"].map((label) => e.jsx("th", { children: label }, label)),
              }),
            }),
            e.jsx("tbody", {
              children: sources.map((source) => e.jsxs("tr", {
                children: [
                  e.jsx("td", { children: e.jsx(Ext, { href: source.url, children: source.label || source.id }) }),
                  e.jsx("td", { className: "nowrap", children: e.jsx("span", { className: `desk-pill ${source.health}`, children: HEALTH_LABEL[source.health] || source.health }) }),
                  e.jsx("td", { className: "nowrap", children: source.skipped ? "—" : Number(source.upserted || 0).toLocaleString("en-US") }),
                  e.jsxs("td", { children: [source.error ? e.jsx("span", { className: "warn", children: source.error }) : null, source.error && source.note ? " " : null, source.note || ""] }),
                ],
              }, source.id)),
            }),
          ],
        }),
      }),
    ],
  });
}

export function StateTab({ tabs }) {
  const [params, setParams] = useSearchParams();
  const code = (params.get("st") || "").toUpperCase();
  const query = params.get("q") || "";
  const page = Math.max(1, Number(params.get("sp") || 1) || 1);
  const model = useLedgerDesk({ stateCode: /^[A-Z]{2}$/.test(code) ? code : "" });
  const desk = model.desk;
  const info = desk && code ? desk.state.states[code] : null;
  const health = info ? classifyStateRow(info, Date.now()) : "";

  function setParam(key, value) {
    const next = new URLSearchParams(params);
    next.set("tab", "state");
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "sp") next.delete("sp");
    setParams(next, { replace: true });
  }

  const states = desk
    ? (desk.state.order.length ? desk.state.order : Object.keys(desk.state.states)).map((postal) => ({
        postal,
        ...(desk.state.states[postal] || {}),
        health: classifyStateRow(desk.state.states[postal], Date.now()),
      }))
    : [];
  const records = model.stateFile?.records || [];
  const needle = query.trim().toLowerCase();
  const filtered = React.useMemo(() => {
    if (!needle) return records;
    const compact = (value) => String(value || "").toLowerCase().replace(/\s+/g, "");
    const billQuery = /^[a-z]{1,5}\s*\d+[a-z]?$/.test(needle);
    return records.filter((record) => {
      const identifier = String(record.identifier || "");
      if (billQuery) return compact(identifier) === compact(needle);
      return [identifier, record.title, record.chapter, record.session, record.statusLabel].filter(Boolean).some((part) => String(part).toLowerCase().includes(needle));
    });
  }, [records, needle]);
  const pageSize = 50;
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const shown = filtered.slice((page - 1) * pageSize, page * pageSize);

  return e.jsxs("div", {
    className: "page ledger",
    children: [
      e.jsx("p", { className: "eyebrow", children: "Law ledger" }),
      e.jsx("h1", { children: "State laws" }),
      e.jsx("p", {
        className: "lede",
        children: "Enacted and signed laws from state legislatures that publish a machine-readable list. Each row links to the official bill or session law. States without a direct source are marked not covered. They are not shown as zero bills.",
      }),
      tabs,
      e.jsx(LedgerStatus, {}),
      desk && e.jsxs(e.Fragment, {
        children: [
          e.jsxs("div", {
            className: "ledger-ctl glass",
            children: [
              e.jsxs("select", {
                "aria-label": "State",
                value: code,
                onChange: (event) => setParam("st", event.target.value),
                children: [
                  e.jsx("option", { value: "", children: "All states" }),
                  states.map((state) => e.jsx("option", { value: state.postal, children: state.name || state.postal }, state.postal)),
                ],
              }),
              code && health !== "unconfigured" && e.jsx("input", {
                type: "search",
                placeholder: "Search titles, bill numbers, chapters…",
                value: query,
                "aria-label": "Search this state's laws",
                onChange: (event) => setParam("q", event.target.value),
              }),
              e.jsx("a", { href: desk.state.workflow, target: "_blank", rel: "noreferrer", children: "Check state sources" }),
            ],
          }),
          e.jsx("p", {
            className: "muted small",
            children: code
              ? `${info?.name || code} · ${HEALTH_LABEL[health] || "Unknown"} · last checked ${formatStamp(info?.lastChecked || info?.lastSynced)}.`
              : `${states.length} states in the index. Open one to read its enacted laws.`,
          }),
          (info?.note || (!code && desk.state.description)) && e.jsx("div", { className: "gap-note", role: "note", children: code ? info.note : desk.state.description }),
          !code && desk.state.openStates?.note && e.jsx("div", { className: "gap-note", role: "note", children: desk.state.openStates.note }),
          code && health === "unconfigured" && e.jsx("p", {
            className: "empty",
            children: "No direct legislature parser is configured for this state, so this page does not invent an empty statute book. Use the official legislature site, or wait until the ingest learns that source.",
          }),
          !code && e.jsx(StateIndex, { states, onOpen: (postal) => setParam("st", postal) }),
          !code && (desk.state.recent || []).length > 0 && e.jsxs(e.Fragment, {
            children: [
              e.jsx("h2", { children: "Recently dated records" }),
              e.jsx(StateRecords, { rows: desk.state.recent.slice(0, 40) }),
            ],
          }),
          code && health !== "unconfigured" && model.stateFileError && e.jsx("div", { className: "desk-alert", role: "alert", children: "This state's ledger file could not be loaded." }),
          code && health !== "unconfigured" && model.stateFileLoading && e.jsx("p", { className: "muted", children: "Loading this state…" }),
          code && model.stateFile && e.jsxs(e.Fragment, {
            children: [
              e.jsxs("p", {
                className: "muted small",
                children: [
                  filtered.length.toLocaleString("en-US"),
                  " records match",
                  model.stateFile.officialUrl ? e.jsxs(e.Fragment, { children: [" · ", e.jsx(Ext, { href: model.stateFile.officialUrl, children: "Legislature" })] }) : null,
                ],
              }),
              filtered.length ? e.jsx(StateRecords, { rows: shown }) : e.jsx("p", { className: "empty", role: "status", children: "No records match this search." }),
              pages > 1 && filtered.length > 0 && e.jsxs("div", {
                className: "pager",
                children: [
                  e.jsx("button", { type: "button", disabled: page <= 1, onClick: () => setParam("sp", String(page - 1)), children: "‹ Prev" }),
                  e.jsxs("span", { children: ["Page ", page, " of ", pages] }),
                  e.jsx("button", { type: "button", disabled: page >= pages, onClick: () => setParam("sp", String(page + 1)), children: "Next ›" }),
                ],
              }),
            ],
          }),
        ],
      }),
    ],
  });
}

function StateIndex({ states, onOpen }) {
  if (!states.length) return e.jsx("p", { className: "empty", children: "The state index has no rows." });
  return e.jsx("div", {
    className: "table-wrap",
    children: e.jsxs("table", {
      className: "ledger-table",
      children: [
        e.jsx("caption", { className: "sr-only", children: "States and whether their enacted-law feed has been checked" }),
        e.jsx("thead", {
          children: e.jsxs("tr", {
            children: ["State", "Status", "Records", "Last checked", "Legislature"].map((label) => e.jsx("th", { children: label }, label)),
          }),
        }),
        e.jsx("tbody", {
          children: states.map((state) => e.jsxs("tr", {
            children: [
              e.jsx("td", { children: e.jsx("button", { type: "button", className: "linkish", onClick: () => onOpen(state.postal), children: state.name || state.postal }) }),
              e.jsx("td", { children: e.jsx("span", { className: `desk-pill ${state.health}`, children: HEALTH_LABEL[state.health] || state.health }) }),
              e.jsx("td", { children: state.health === "unconfigured" ? "—" : (state.recordCount || 0).toLocaleString("en-US") }),
              e.jsx("td", { className: "nowrap", children: state.lastChecked || state.lastSynced ? formatStamp(state.lastChecked || state.lastSynced) : "—" }),
              e.jsx("td", { children: state.officialUrl ? e.jsx(Ext, { href: state.officialUrl, children: "Official site" }) : "—" }),
            ],
          }, state.postal)),
        }),
      ],
    }),
  });
}

function StateRecords({ rows }) {
  return e.jsx("div", {
    className: "table-wrap",
    children: e.jsxs("table", {
      className: "ledger-table",
      children: [
        e.jsx("thead", {
          children: e.jsxs("tr", {
            children: ["Law", "Title", "Status", "Date"].map((label) => e.jsx("th", { children: label }, label)),
          }),
        }),
        e.jsx("tbody", {
          children: rows.map((record) => e.jsxs("tr", {
            children: [
              e.jsxs("td", {
                className: "nowrap",
                children: [
                  record.state ? `${record.state} ` : "",
                  record.officialUrl ? e.jsx(Ext, { href: record.officialUrl, children: record.identifier || "record" }) : (record.identifier || "—"),
                  record.chapter ? e.jsxs("div", { className: "muted small", children: ["Ch. ", record.chapter] }) : null,
                ],
              }),
              e.jsx("td", { children: record.title || e.jsx("span", { className: "muted", children: "title not stated" }) }),
              e.jsx("td", { children: record.statusLabel || record.status || "—" }),
              e.jsx("td", { className: "nowrap", children: record.date ? `${DATE_LABEL[record.dateKind] ? DATE_LABEL[record.dateKind] + " " : ""}${formatDay(record.date)}` : "date not stated" }),
            ],
          }, record.id)),
        }),
      ],
    }),
  });
}
