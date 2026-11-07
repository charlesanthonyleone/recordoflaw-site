/**
 * Living federal ledger panel for /wiki/ledger.
 * Additive: reads ledger/meta.json and ledger/federal-live.json.
 * A state-ledger control can mount in [data-state-ledger-slot].
 */
const PANEL_ID = "rol-federal-live";
const WORKFLOW_FALLBACK = "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/federal-sync.yml";

const KIND_LABEL = {
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

const DATE_LABEL = {
  enacted: "enacted",
  signed: "signed",
  published: "published",
  voted: "voted",
  decided: "decided",
  acted: "latest action",
};

const FILTERS = [
  ["mix", "Recent mix"],
  ["legislative", "Congress"],
  ["rules", "Agency rules"],
  ["notices", "Notices"],
  ["presidential", "Presidential"],
  ["judicial", "Courts"],
];

const state = {
  filter: "mix",
  limit: 25,
  meta: null,
  live: null,
  readAt: null,
  error: "",
  loading: false,
};

function onLedger() {
  return /^\/wiki\/ledger\/?$/.test(location.pathname);
}

function el(tag, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  return node;
}

function safeUrl(value) {
  try {
    const url = new URL(value, location.origin);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function lane(record) {
  if (record.branch === "judicial") return "Court";
  if (record.branch === "legislative") return "Congress";
  if (record.kind === "executive-order" || record.kind === "proclamation" || record.kind === "presidential-document") return "Presidential";
  return "Agency";
}

function matches(record, filter) {
  if (filter === "legislative") return record.branch === "legislative";
  if (filter === "judicial") return record.branch === "judicial";
  if (filter === "rules") return record.kind === "rule" || record.kind === "proposed-rule";
  if (filter === "notices") return record.kind === "notice";
  if (filter === "presidential") {
    return record.kind === "executive-order" || record.kind === "proclamation" || record.kind === "presidential-document";
  }
  return true;
}

function byDate(records) {
  return records.slice().sort((a, b) => {
    if (a.date === b.date) return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    return a.date < b.date ? 1 : -1;
  });
}

function balanced(records) {
  const sorted = byDate(records);
  const groups = [
    sorted.filter((record) => record.branch === "legislative").slice(0, 8),
    sorted.filter((record) => record.kind === "rule" || record.kind === "proposed-rule").slice(0, 8),
    sorted.filter((record) => record.kind === "notice").slice(0, 4),
    sorted.filter((record) => matches(record, "presidential")).slice(0, 6),
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

function formatDay(iso) {
  if (!iso) return "date not stated";
  const parsed = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString("en-US", { timeZone: "UTC", year: "numeric", month: "short", day: "numeric" });
}

function formatStamp(iso) {
  if (!iso) return "not yet checked";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }) + " UTC";
}

function countLine(records) {
  const counts = { Congress: 0, "Agency rules": 0, Notices: 0, Presidential: 0, Courts: 0 };
  for (const record of records) {
    if (record.branch === "legislative") counts.Congress += 1;
    else if (record.branch === "judicial") counts.Courts += 1;
    else if (record.kind === "notice") counts.Notices += 1;
    else if (matches(record, "presidential")) counts.Presidential += 1;
    else if (record.kind === "rule" || record.kind === "proposed-rule") counts["Agency rules"] += 1;
  }
  return Object.entries(counts).map(([label, count]) => `${count.toLocaleString("en-US")} ${label}`).join(" · ");
}

function ensureStyle() {
  if (document.getElementById("rol-federal-live-style")) return;
  const style = el("style");
  style.id = "rol-federal-live-style";
  style.textContent = `
#${PANEL_ID}{margin:14px 0 18px}
#${PANEL_ID} .fl-bar{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;padding:10px 12px}
#${PANEL_ID} .fl-status{flex:1 1 280px;margin:0}
#${PANEL_ID} .fl-actions{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
#${PANEL_ID} .fl-actions button,#${PANEL_ID} .fl-link{
  padding:6px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.18);
  background:transparent;color:inherit;cursor:pointer;text-decoration:none
}
#${PANEL_ID} .fl-actions button:hover,#${PANEL_ID} .fl-link:hover{border-color:#e7c675;color:#f3e2b3}
#${PANEL_ID} [data-state-ledger-slot]:empty{display:none}
#${PANEL_ID} .fl-filters{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
#${PANEL_ID} .fl-filters button{padding:6px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.15);background:transparent;color:inherit;cursor:pointer}
#${PANEL_ID} .fl-filters button[aria-pressed="true"]{border-color:#e7c675;color:#f3e2b3;background:#e7c6751f}
#${PANEL_ID} .fl-table-wrap{overflow-x:auto}
#${PANEL_ID} .fl-src{display:block;margin-top:8px}
#${PANEL_ID} .fl-src summary{cursor:pointer}
#${PANEL_ID} .fl-src li{margin:.35em 0}
#${PANEL_ID} .fl-error{margin-top:8px}
`;
  document.head.appendChild(style);
}

async function loadFiles() {
  const bust = Date.now();
  const [metaRes, liveRes] = await Promise.all([
    fetch(`/ledger/meta.json?t=${bust}`, { cache: "no-store" }),
    fetch(`/ledger/federal-live.json?t=${bust}`, { cache: "no-store" }),
  ]);
  if (!metaRes.ok || !liveRes.ok) {
    throw new Error(`Ledger files could not be read (meta ${metaRes.status}, federal ${liveRes.status}).`);
  }
  const meta = await metaRes.json();
  const live = await liveRes.json();
  if (!live || !Array.isArray(live.records) || !meta || !meta.federal) {
    throw new Error("Federal ledger files were missing the expected fields.");
  }
  state.meta = meta;
  state.live = live;
  state.readAt = new Date().toISOString();
  state.error = "";
}

function render(host) {
  const previousSlot = host.querySelector("[data-state-ledger-slot]");
  host.replaceChildren();
  ensureStyle();
  const federal = state.meta?.federal;
  const records = byDate(state.live?.records || []);
  const bar = el("div", "fl-bar glass");
  const status = el("p", "fl-status");
  const stamp = el("time");
  stamp.dateTime = federal?.lastChecked || "";
  stamp.textContent = formatStamp(federal?.lastChecked);
  status.append("Official sources last checked ", stamp, ". ");
  const statusNote = el("span", "muted");
  statusNote.textContent = "Refresh re-reads this ledger. Check sources opens the ingest that also runs four times a day.";
  status.append(statusNote);
  const actions = el("div", "fl-actions");
  const refresh = el("button");
  refresh.type = "button";
  refresh.textContent = state.loading ? "Refreshing…" : "Refresh";
  refresh.disabled = state.loading;
  refresh.addEventListener("click", () => { void refreshLedger(host); });
  const check = el("a", "fl-link");
  check.href = safeUrl(federal?.workflow) || WORKFLOW_FALLBACK;
  check.target = "_blank";
  check.rel = "noreferrer";
  check.textContent = "Check sources";
  const slot = previousSlot || el("span");
  slot.setAttribute("data-state-ledger-slot", "");
  actions.append(refresh, check, slot);
  bar.append(status, actions);
  host.append(bar);

  const note = el("div", "gap-note");
  note.setAttribute("role", "note");
  const noteStrong = el("b");
  noteStrong.textContent = "Living federal record. ";
  note.append(noteStrong);
  note.append("Congress, federal agencies, presidential documents, and courts stay in one list. Each row links to its official source. Past rows already in the ledger are kept; this list is what the sync has checked.");
  host.append(note);

  if (state.error) {
    const warn = el("p", "warn fl-error");
    warn.textContent = state.error;
    host.append(warn);
  }

  const counts = el("p", "muted small");
  counts.textContent = records.length
    ? `${countLine(records)}. ${records.length.toLocaleString("en-US")} federal records in the live file.`
    : "No federal live records have been synced yet.";
  host.append(counts);

  const filters = el("div", "fl-filters");
  filters.setAttribute("role", "toolbar");
  filters.setAttribute("aria-label", "Federal activity");
  for (const [id, label] of FILTERS) {
    const button = el("button");
    button.type = "button";
    button.textContent = label;
    button.setAttribute("aria-pressed", state.filter === id ? "true" : "false");
    button.addEventListener("click", () => {
      state.filter = id;
      state.limit = 25;
      render(host);
    });
    filters.append(button);
  }
  host.append(filters);

  const shown = state.filter === "mix" ? balanced(records) : byDate(records.filter((record) => matches(record, state.filter))).slice(0, state.limit);
  const wrap = el("div", "fl-table-wrap");
  const table = el("table", "ledger-table");
  const caption = el("caption", "sr-only");
  caption.textContent = "Recent federal activity with official source links";
  const thead = el("thead");
  const headRow = el("tr");
  for (const label of ["Date", "Where", "Kind", "Record", "Official source"]) {
    const th = el("th");
    th.textContent = label;
    headRow.append(th);
  }
  thead.append(headRow);
  const tbody = el("tbody");
  if (!shown.length) {
    const tr = el("tr");
    const td = el("td");
    td.colSpan = 5;
    td.textContent = "Nothing in this slice yet.";
    tr.append(td);
    tbody.append(tr);
  }
  for (const record of shown) {
    const tr = el("tr");
    const dateCell = el("td", "nowrap");
    dateCell.textContent = formatDay(record.date);
    const kindNote = el("div", "muted small");
    kindNote.textContent = DATE_LABEL[record.dateKind] || record.dateKind || "";
    dateCell.append(kindNote);
    const where = el("td", "nowrap");
    where.textContent = lane(record);
    const kind = el("td", "nowrap");
    kind.textContent = KIND_LABEL[record.kind] || record.kind || "";
    const titleCell = el("td");
    const href = safeUrl(record.officialUrl);
    if (href) {
      const link = el("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = record.title || record.officialId || "Official record";
      titleCell.append(link);
    } else {
      titleCell.textContent = record.title || "Untitled";
    }
    const sub = [record.citation, record.actor, record.detail].filter(Boolean).join(" · ");
    if (sub) {
      const line = el("div", "muted small");
      line.textContent = sub;
      titleCell.append(line);
    }
    if (record.sourceText) {
      const quote = el("div", "muted small");
      quote.textContent = record.sourceText;
      titleCell.append(quote);
    }
    const sourceCell = el("td", "nowrap");
    if (href) {
      const link = el("a");
      link.href = href;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Verify";
      sourceCell.append(link);
    } else {
      sourceCell.textContent = "—";
    }
    tr.append(dateCell, where, kind, titleCell, sourceCell);
    tbody.append(tr);
  }
  table.append(caption, thead, tbody);
  wrap.append(table);
  host.append(wrap);

  if (state.filter !== "mix") {
    const matched = records.filter((record) => matches(record, state.filter)).length;
    if (shown.length < matched) {
      const more = el("div", "pager");
      const button = el("button");
      button.type = "button";
      button.textContent = `Show more (${shown.length} of ${matched})`;
      button.addEventListener("click", () => {
        state.limit += 25;
        render(host);
      });
      more.append(button);
      host.append(more);
    }
  }

  const sources = Array.isArray(federal?.sources) ? federal.sources : [];
  if (sources.length) {
    const details = el("details", "fl-src small");
    const summary = el("summary");
    summary.textContent = "Sources checked";
    const list = el("ul");
    for (const source of sources) {
      const item = el("li");
      const href = safeUrl(source.url);
      if (href) {
        const link = el("a");
        link.href = href;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = source.label || source.id;
        item.append(link);
      } else {
        item.append(source.label || source.id || "Source");
      }
      const bits = [];
      if (source.skipped) bits.push("not configured");
      else if (source.ok) bits.push("reached");
      else bits.push("not reached");
      if (source.upserted) bits.push(`${source.upserted} records`);
      if (source.error) bits.push(source.error);
      const rest = el("span", "muted");
      rest.textContent = bits.length ? ` — ${bits.join("; ")}` : "";
      item.append(rest);
      if (source.note) {
        const noteLine = el("div", "muted");
        noteLine.textContent = source.note;
        item.append(noteLine);
      }
      list.append(item);
    }
    details.append(summary, list);
    host.append(details);
  }

  if (state.readAt) {
    const reread = el("p", "muted small");
    reread.textContent = `Ledger file re-read ${formatStamp(state.readAt)}.`;
    host.append(reread);
  }
}

async function refreshLedger(host) {
  state.loading = true;
  render(host);
  try {
    await loadFiles();
  } catch (error) {
    state.error = error instanceof Error ? error.message : "The ledger could not be re-read.";
  } finally {
    state.loading = false;
    const current = document.getElementById(PANEL_ID);
    if (current) render(current);
  }
}

function mount() {
  if (!onLedger()) {
    document.getElementById(PANEL_ID)?.remove();
    return;
  }
  const page = document.querySelector(".page.ledger");
  if (!page || page.querySelector(`#${PANEL_ID}`)) return;
  ensureStyle();
  const host = el("section");
  host.id = PANEL_ID;
  host.setAttribute("aria-label", "Living federal ledger");
  const lede = page.querySelector(".lede");
  if (lede?.nextSibling) page.insertBefore(host, lede.nextSibling);
  else page.prepend(host);
  if (!state.live && !state.loading) {
    state.loading = true;
    render(host);
    loadFiles().then(() => {
      state.loading = false;
      const current = document.getElementById(PANEL_ID);
      if (current) render(current);
    }).catch((error) => {
      state.loading = false;
      state.error = error instanceof Error ? error.message : "The ledger could not be read.";
      const current = document.getElementById(PANEL_ID);
      if (current) render(current);
    });
    return;
  }
  render(host);
}

function watch() {
  const start = () => {
    mount();
    const observer = new MutationObserver(() => mount());
    observer.observe(document.body, { childList: true, subtree: true });
    window.addEventListener("popstate", mount);
  };
  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start);
}

watch();
