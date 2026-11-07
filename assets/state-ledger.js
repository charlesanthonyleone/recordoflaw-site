import { g as useSearchParams, j as e, r as React } from "./react-8qEOpjgC.js";

const WORKFLOW =
  "https://github.com/charlesanthonyleone/recordoflaw-site/actions/workflows/state-ledger.yml";
const PAGE = 50;

const DATE_KIND = {
  signed: "Signed",
  approved: "Approved",
  effective: "Effective",
  presentment: "Presented",
  "last-action": "Last action",
  status: "Status date",
  action: "Action",
};

function formatChecked(value) {
  if (!value) return "not yet checked against a bill source";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  const hh = String(date.getUTCHours()).padStart(2, "0");
  const mm = String(date.getUTCMinutes()).padStart(2, "0");
  return `${y}-${m}-${d} ${hh}:${mm} UTC`;
}

function formatDate(record) {
  if (!record.date) return "date not stated";
  const kind = DATE_KIND[record.dateKind];
  return kind ? `${kind} ${record.date}` : record.date;
}

export default function StateLedger({ tabs }) {
  const [params, setParams] = useSearchParams();
  const [meta, setMeta] = React.useState(null);
  const [metaError, setMetaError] = React.useState(false);
  const [file, setFile] = React.useState(null);
  const [fileError, setFileError] = React.useState(false);
  const code = (params.get("st") || "").toUpperCase();
  const query = params.get("q") || "";
  const page = Math.max(1, Number(params.get("sp") || 1) || 1);

  React.useEffect(() => {
    let alive = true;
    fetch("/ledger/states-meta.json")
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        if (alive) setMeta(payload);
      })
      .catch(() => {
        if (alive) setMetaError(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  React.useEffect(() => {
    if (!code) {
      setFile(null);
      setFileError(false);
      return undefined;
    }
    let alive = true;
    setFile(null);
    setFileError(false);
    fetch(`/ledger/states/${code.toLowerCase()}.json`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((payload) => {
        if (alive) setFile(payload);
      })
      .catch(() => {
        if (alive) setFileError(true);
      });
    return () => {
      alive = false;
    };
  }, [code]);

  function setParam(key, value) {
    const next = new URLSearchParams(params);
    next.set("tab", "state");
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "sp") next.delete("sp");
    setParams(next, { replace: true });
  }

  const info = meta && code ? meta.states?.[code] : null;
  const states = meta
    ? (meta.order || Object.keys(meta.states || {})).map((postal) => ({
        postal,
        ...(meta.states?.[postal] || {}),
      }))
    : [];
  const rows = React.useMemo(() => {
    const records = file?.records || [];
    const needle = query.trim().toLowerCase();
    if (!needle) return records;
    const compact = (value) => String(value || "").toLowerCase().replace(/\s+/g, "");
    const billQuery = /^[a-z]{1,5}\s*\d+[a-z]?$/.test(needle);
    return records.filter((record) => {
      const identifier = String(record.identifier || "");
      if (billQuery) return compact(identifier) === compact(needle);
      return [identifier, record.title, record.chapter, record.session, record.statusLabel]
        .filter(Boolean)
        .some((part) => String(part).toLowerCase().includes(needle));
    });
  }, [file, query]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE));
  const shown = rows.slice((page - 1) * PAGE, page * PAGE);
  const checked = info?.lastChecked || info?.lastSynced;

  return e.jsxs("div", {
    className: "page ledger",
    children: [
      e.jsx("p", { className: "eyebrow", children: "Law ledger" }),
      e.jsx("h1", { children: "State laws" }),
      e.jsx("p", {
        className: "lede",
        children:
          "Enacted and signed laws from state legislatures, one state at a time. Each row links to the official bill or session-law page the record was taken from. Federal statutes and executive orders stay on the other tabs.",
      }),
      tabs,
      metaError &&
        e.jsx("p", { className: "warn", children: "The state ledger index could not be loaded." }),
      !meta && !metaError && e.jsx("p", { className: "muted", children: "Loading state ledger…" }),
      meta &&
        e.jsxs(e.Fragment, {
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
                    states.map((state) =>
                      e.jsx(
                        "option",
                        { value: state.postal, children: state.name || state.postal },
                        state.postal
                      )
                    ),
                  ],
                }),
                code &&
                  e.jsx("input", {
                    type: "search",
                    placeholder: "Search titles, bill numbers, chapters…",
                    value: query,
                    onChange: (event) => setParam("q", event.target.value),
                    "aria-label": "Search this state's laws",
                  }),
                e.jsx("a", {
                  href: WORKFLOW,
                  target: "_blank",
                  rel: "noreferrer",
                  children: "Check sources",
                }),
              ],
            }),
            e.jsx("p", {
              className: "muted small",
              children: code
                ? `${info?.name || code} last checked ${formatChecked(checked)}. ${
                    info?.recordCount ?? rows.length
                  } records stored. Check sources opens the state ingest workflow${
                    code ? `; set its state input to ${code} to refresh this state` : ""
                  }.`
                : `Last index update ${formatChecked(meta.updated)}. Check sources opens the scheduled state ingest workflow.`,
            }),
            (info?.note || (!code && meta.openStates?.note)) &&
              e.jsx("div", {
                className: "gap-note",
                role: "note",
                children: code ? info?.note : meta.description,
              }),
            info?.error && e.jsx("p", { className: "warn", children: info.error }),
            !code &&
              e.jsxs(e.Fragment, {
                children: [
                  e.jsx("div", {
                    className: "table-wrap",
                    children: e.jsxs("table", {
                      className: "ledger-table",
                      children: [
                        e.jsx("thead", {
                          children: e.jsxs("tr", {
                            children: [
                              e.jsx("th", { children: "State" }),
                              e.jsx("th", { children: "Records" }),
                              e.jsx("th", { children: "Last checked" }),
                              e.jsx("th", { children: "Legislature" }),
                            ],
                          }),
                        }),
                        e.jsx("tbody", {
                          children: states.map((state) =>
                            e.jsxs(
                              "tr",
                              {
                                children: [
                                  e.jsx("td", {
                                    children: e.jsx("button", {
                                      className: "linkish",
                                      onClick: () => setParam("st", state.postal),
                                      children: state.name || state.postal,
                                    }),
                                  }),
                                  e.jsx("td", { children: state.recordCount || 0 }),
                                  e.jsx("td", {
                                    className: "nowrap",
                                    children: state.lastChecked
                                      ? formatChecked(state.lastChecked)
                                      : "not checked",
                                  }),
                                  e.jsx("td", {
                                    children: state.officialUrl
                                      ? e.jsx("a", {
                                          href: state.officialUrl,
                                          target: "_blank",
                                          rel: "noreferrer",
                                          children: "Official site",
                                        })
                                      : "—",
                                  }),
                                ],
                              },
                              state.postal
                            )
                          ),
                        }),
                      ],
                    }),
                  }),
                  (meta.recent || []).length > 0 &&
                    e.jsxs(e.Fragment, {
                      children: [
                        e.jsx("h2", { children: "Recently dated records" }),
                        e.jsx(RecordTable, { rows: meta.recent }),
                      ],
                    }),
                ],
              }),
            code && fileError &&
              e.jsx("p", {
                className: "muted",
                children: info?.coverage === "unconfigured"
                  ? "No enacted records are stored for this state yet."
                  : "This state's ledger file could not be loaded.",
              }),
            code && !file && !fileError &&
              e.jsx("p", { className: "muted", children: "Loading this state…" }),
            code && file &&
              e.jsxs(e.Fragment, {
                children: [
                  e.jsxs("p", {
                    className: "muted small",
                    children: [
                      rows.length.toLocaleString("en-US"),
                      " records match",
                      file.officialUrl &&
                        e.jsxs(e.Fragment, {
                          children: [
                            " · ",
                            e.jsx("a", {
                              href: file.officialUrl,
                              target: "_blank",
                              rel: "noreferrer",
                              children: "Legislature",
                            }),
                          ],
                        }),
                    ],
                  }),
                  e.jsx(RecordTable, { rows: shown }),
                  pages > 1 &&
                    e.jsxs("div", {
                      className: "pager",
                      children: [
                        e.jsx("button", {
                          disabled: page <= 1,
                          onClick: () => setParam("sp", String(page - 1)),
                          children: "‹ Prev",
                        }),
                        e.jsxs("span", { children: ["Page ", page, " of ", pages] }),
                        e.jsx("button", {
                          disabled: page >= pages,
                          onClick: () => setParam("sp", String(page + 1)),
                          children: "Next ›",
                        }),
                      ],
                    }),
                ],
              }),
          ],
        }),
    ],
  });
}

function RecordTable({ rows }) {
  if (!rows.length) {
    return e.jsx("p", { className: "muted", children: "No matching records." });
  }
  return e.jsx("div", {
    className: "table-wrap",
    children: e.jsxs("table", {
      className: "ledger-table",
      children: [
        e.jsx("thead", {
          children: e.jsxs("tr", {
            children: [
              e.jsx("th", { children: "Law" }),
              e.jsx("th", { children: "Title" }),
              e.jsx("th", { children: "Status" }),
              e.jsx("th", { children: "Date" }),
            ],
          }),
        }),
        e.jsx("tbody", {
          children: rows.map((record) =>
            e.jsxs(
              "tr",
              {
                children: [
                  e.jsxs("td", {
                    className: "nowrap",
                    children: [
                      record.state ? `${record.state} ` : "",
                      record.officialUrl
                        ? e.jsx("a", {
                            href: record.officialUrl,
                            target: "_blank",
                            rel: "noreferrer",
                            children: record.identifier,
                          })
                        : record.identifier,
                      record.chapter &&
                        e.jsxs("div", { className: "muted small", children: ["Ch. ", record.chapter] }),
                    ],
                  }),
                  e.jsx("td", {
                    children: record.title || e.jsx("span", { className: "muted", children: "title not stated" }),
                  }),
                  e.jsx("td", { children: record.statusLabel || record.status || "—" }),
                  e.jsx("td", { className: "nowrap", children: formatDate(record) }),
                ],
              },
              record.id
            )
          ),
        }),
      ],
    }),
  });
}
