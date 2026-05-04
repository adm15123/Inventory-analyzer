// ============================================================
// reactApp.jsx  — Zamora Inventory Analyzer
// ALL IMPROVEMENTS APPLIED:
//  #1  Production React builds (handled in app.html)
//  #3  Debounced search (300 ms)
//  #6  PDF loading state shown while server generates
//  #7  "Add to List" button in Search results
//  #8  Quantity inputs: min=0 step=1
//  #9  Skeleton rows while View All loads
//  #10 Flash messages auto-dismiss after 5 s
//  #11 Mobile card layout for Material List
//  #12 Analyze CSV export
//  #13 Dashboard home page with stats
// ============================================================

const { useCallback, useEffect, useMemo, useRef, useState } = React;

// --------------- shared cart context (Search → Material List) ---------------
// We store pending "add to list" items in sessionStorage so they survive the
// page navigation between Search and Material List.
const CART_KEY = "zpl_pending_items";
function getPendingItems() {
  try { return JSON.parse(sessionStorage.getItem(CART_KEY) || "[]"); }
  catch { return []; }
}
function setPendingItems(items) {
  try { sessionStorage.setItem(CART_KEY, JSON.stringify(items)); }
  catch {}
}

// --------------- helpers ---------------
const variantStyles = {
  primary: "bg-sky-600 hover:bg-sky-700 text-white",
  secondary: "bg-slate-700 hover:bg-slate-800 text-white",
  ghost: "text-slate-600 hover:text-slate-900",
  danger: "bg-rose-600 hover:bg-rose-700 text-white",
  success: "bg-emerald-600 hover:bg-emerald-700 text-white",
};

const supplyCodes = {
  supply1: "BPS",
  supply2: "S2",
  supply3: "LPS",
  supply4: "BOND",
};

const supplyLabels = {
  supply1: "Supply 1 (BPS)",
  supply2: "Supply 2",
  supply3: "Lion Plumbing Supply",
  supply4: "Bond Plumbing Supply",
};

function getSupplyKeyFromCode(code) {
  return Object.entries(supplyCodes).find(([, v]) => v === code)?.[0];
}

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

// --------------- Button ---------------
function Button({ variant = "primary", className = "", as = "button", href, children, ...props }) {
  const Component = as === "a" ? "a" : "button";
  const base = variantStyles[variant] || variantStyles.primary;
  const shared = classNames(
    "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
    base,
    className
  );
  if (Component === "a") {
    return <a className={shared} href={href} {...props}>{children}</a>;
  }
  return <button className={shared} {...props}>{children}</button>;
}

// --------------- Badge ---------------
function Badge({ children, tone = "default" }) {
  const tones = {
    default: "bg-slate-200 text-slate-800",
    success: "bg-emerald-100 text-emerald-700",
    info: "bg-sky-100 text-sky-700",
    danger: "bg-rose-100 text-rose-700",
  };
  return (
    <span className={classNames("inline-flex items-center rounded-full px-3 py-1 text-xs font-medium", tones[tone] || tones.default)}>
      {children}
    </span>
  );
}

// --------------- FlashMessages — IMPROVEMENT #10: auto-dismiss after 5s ---------------
function FlashMessages({ initial }) {
  const [messages, setMessages] = useState(initial || []);

  useEffect(() => {
    if (!messages.length) return;
    const timer = setTimeout(() => setMessages([]), 5000);
    return () => clearTimeout(timer);
  }, [messages]);

  if (!messages.length) return null;

  const toneMap = { success: "success", danger: "danger", warning: "info", info: "info" };
  return (
    <div className="fixed top-4 right-4 z-50 space-y-3 max-w-sm">
      {messages.map(([category, text], index) => (
        <div
          key={`${category}-${index}`}
          className="flex items-start gap-3 rounded-xl bg-white p-4 shadow-xl ring-1 ring-slate-200 animate-pulse-once"
        >
          <div className="flex-1 text-sm text-slate-700">
            <Badge tone={toneMap[category] || "info"}>{category.toUpperCase()}</Badge>
            <p className="mt-1 leading-relaxed">{text}</p>
          </div>
          <button
            type="button"
            className="text-slate-400 transition hover:text-slate-600 text-lg leading-none"
            aria-label="Dismiss"
            onClick={() => setMessages((c) => c.filter((_, i) => i !== index))}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

// --------------- EmptyState ---------------
function EmptyState({ title, description }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl bg-white py-16 shadow-sm ring-1 ring-slate-200">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {description && <p className="mt-1 text-xs text-slate-500">{description}</p>}
    </div>
  );
}

// --------------- IMPROVEMENT #9: Skeleton table rows ---------------
function SkeletonRows({ cols = 5, rows = 8 }) {
  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {Array.from({ length: cols }).map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <div className="h-3 w-20 rounded bg-slate-200 animate-pulse" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {Array.from({ length: rows }).map((_, ri) => (
              <tr key={ri}>
                {Array.from({ length: cols }).map((_, ci) => (
                  <td key={ci} className="px-4 py-3">
                    <div className="h-3 rounded bg-slate-100 animate-pulse" style={{ width: `${60 + (ci * 13) % 35}%` }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --------------- Table ---------------
function Table({ columns, rows, renderRow }) {
  if (!rows || !rows.length) {
    return <EmptyState title="No results" description="Nothing matched your query." />;
  }
  return (
    <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key || column}
                  scope="col"
                  className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {column.label || column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row, rowIndex) => (
              <tr key={row.id || rowIndex} className="hover:bg-slate-50">
                {renderRow(row, rowIndex)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --------------- Layout ---------------
function Layout({ page, navLinks, userEmail, logoutUrl, children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <div className="min-h-screen bg-slate-100">
      <nav className="sticky top-0 z-40 border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <span className="text-base font-bold text-sky-700 tracking-tight">
            Zamora Plumbing
          </span>
          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <a
                key={link.page}
                href={link.href}
                className={classNames(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition",
                  link.page === page
                    ? "bg-sky-50 text-sky-700"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                {link.label}
              </a>
            ))}
          </div>
          <div className="hidden md:flex items-center gap-3">
            {userEmail && <span className="text-xs text-slate-500 truncate max-w-[160px]">{userEmail}</span>}
            {logoutUrl && (
              <a href={logoutUrl} className="text-xs text-slate-500 hover:text-rose-600 transition">
                Sign out
              </a>
            )}
          </div>
          {/* Mobile hamburger */}
          <button
            className="md:hidden rounded-lg p-2 text-slate-600 hover:bg-slate-100"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? "✕" : "☰"}
          </button>
        </div>
        {/* Mobile menu */}
        {mobileOpen && (
          <div className="md:hidden border-t border-slate-100 bg-white px-4 pb-3">
            {navLinks.map((link) => (
              <a
                key={link.page}
                href={link.href}
                className="block py-2 text-sm font-medium text-slate-700 hover:text-sky-700"
              >
                {link.label}
              </a>
            ))}
            {userEmail && <p className="pt-2 text-xs text-slate-500">{userEmail}</p>}
            {logoutUrl && <a href={logoutUrl} className="text-xs text-rose-500">Sign out</a>}
          </div>
        )}
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-8">
        {children}
      </main>
    </div>
  );
}

// ================================================================
// IMPROVEMENT #13: Dashboard home page with stats
// ================================================================
function HomePage({ data }) {
  const stats = data.stats || {};
  const statCards = [
    { label: "Supply 1 Items", value: stats.supply1Count ?? "—", color: "sky" },
    { label: "Supply 2 Items", value: stats.supply2Count ?? "—", color: "violet" },
    { label: "Lion Supply Items", value: stats.supply3Count ?? "—", color: "amber" },
    { label: "Bond Supply Items", value: stats.supply4Count ?? "—", color: "emerald" },
    { label: "Templates Saved", value: stats.templateCount ?? "—", color: "rose" },
  ];

  const colorMap = {
    sky: "bg-sky-50 border-sky-200 text-sky-700",
    violet: "bg-violet-50 border-violet-200 text-violet-700",
    amber: "bg-amber-50 border-amber-200 text-amber-700",
    emerald: "bg-emerald-50 border-emerald-200 text-emerald-700",
    rose: "bg-rose-50 border-rose-200 text-rose-700",
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          {data.pageTitle || "Zamora Plumbing Corp"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">Material Analyzer &amp; Pricing Dashboard</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {statCards.map((card) => (
          <div
            key={card.label}
            className={classNames(
              "rounded-2xl border p-4",
              colorMap[card.color] || "bg-slate-50 border-slate-200 text-slate-700"
            )}
          >
            <p className="text-2xl font-bold">{card.value.toLocaleString()}</p>
            <p className="mt-1 text-xs font-medium opacity-75">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Quick search */}
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h2 className="text-base font-semibold text-slate-800 mb-3">Quick Search</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const q = e.target.elements.q.value.trim();
            if (q) window.location.href = `/search?supply=supply1&query=${encodeURIComponent(q)}`;
          }}
          className="flex gap-2"
        >
          <input
            name="q"
            type="text"
            placeholder="Search item description…"
            className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
          <Button type="submit">Search</Button>
        </form>
      </div>

      {/* Quick action cards */}
      <div>
        <h2 className="mb-4 text-base font-semibold text-slate-800">Quick Actions</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(data.actions || []).map((action) => (
            <a
              key={action.label}
              href={action.href}
              className="group flex flex-col gap-2 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 transition hover:ring-sky-400 hover:shadow-md"
            >
              <span className="text-sm font-semibold text-slate-800 group-hover:text-sky-700 transition">
                {action.label}
              </span>
              <span className="text-xs text-slate-400">→</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ================================================================
// ViewAllPage — IMPROVEMENT #9: skeleton rows while loading
// ================================================================
function ViewAllPage({ data }) {
  const [supply, setSupply] = useState(data.supply || "supply1");
  const [rows, setRows] = useState(data.rows || []);
  const [columns] = useState(data.columns || []);
  const [loading, setLoading] = useState(false);

  useEffect(() => { setRows(data.rows || []); }, [data.rows]);

  const handleSupplyChange = (event) => {
    const value = event.target.value;
    setSupply(value);
    setLoading(true);
    const url = new URL(data.viewAllUrl || window.location.pathname, window.location.origin);
    url.searchParams.set("supply", value);
    url.searchParams.set("format", "json");
    fetch(url.toString(), { headers: { Accept: "application/json" } })
      .then((r) => r.json())
      .then((p) => { setRows(p.rows || []); })
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">All Inventory Records</h1>
          <p className="mt-1 text-sm text-slate-500">
            Browse the complete catalog. Select a supplier to refresh.
          </p>
        </div>
        <select
          value={supply}
          onChange={handleSupplyChange}
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
        >
          {(data.supplyOptions || []).map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <SkeletonRows cols={columns.length + 1} rows={10} />
      ) : (
        <Table
          columns={[...columns, { key: "actions", label: "History" }]}
          rows={rows}
          renderRow={(row, index) => (
            <>
              {columns.map((column) => (
                <td key={`${column}-${index}`} className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {row[column] ?? ""}
                </td>
              ))}
              <td className="px-4 py-3 text-sm">
                {row.graphUrl ? (
                  <Button as="a" href={row.graphUrl} variant="secondary" className="px-3 py-1 text-xs">
                    View history
                  </Button>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </td>
            </>
          )}
        />
      )}
    </div>
  );
}

// ================================================================
// SearchPage
// ================================================================
function SearchPage({ data }) {
  const [supply, setSupply]       = useState(data.supply || "supply1");
  const [query, setQuery]         = useState(data.query || "");
  const [columns, setColumns]     = useState(data.columns || []);
  const [rows, setRows]           = useState(data.rows || []);
  const [loading, setLoading]     = useState(false);
  const [addedDescs, setAddedDescs] = useState({});   // keyed by description
  const [expanded, setExpanded]   = useState(new Set());
  const debounceRef = useRef(null);

  const runSearch = useCallback((nextQuery, nextSupply) => {
    const trimmed = nextQuery.trim();
    if (!trimmed) { setColumns([]); setRows([]); return; }
    setLoading(true);
    const url = new URL(data.searchApi || "/api/search", window.location.origin);
    url.searchParams.set("supply", nextSupply);
    url.searchParams.set("query", trimmed);
    fetch(url.toString(), { headers: { Accept: "application/json" } })
      .then((r) => r.json())
      .then((p) => { setColumns(p.columns || []); setRows(p.rows || []); })
      .finally(() => setLoading(false));
  }, [data.searchApi]);

  useEffect(() => {
    if (query) runSearch(query, supply);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleQueryChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(val, supply), 300);
  };

  const handleSupplyChange = (e) => {
    setSupply(e.target.value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(query, e.target.value), 300);
  };

  const toggleExpanded = (desc) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(desc) ? next.delete(desc) : next.add(desc);
      return next;
    });
  };

  const handleAddToList = (row, desc) => {
    let listName = sessionStorage.getItem("zpl_new_list_name");
    if (!listName) {
      listName = window.prompt("Enter a name for this list:");
      if (!listName || !listName.trim()) return;
      sessionStorage.setItem("zpl_new_list_name", listName.trim());
    }
    const pending = getPendingItems();
    pending.push({
      description: desc,
      supply: supplyCodes[supply] || supply,
      lookupSupply: supply,
      unit: row.Unit || row.unit || "",
      lastPrice: parseFloat(row["Price per Unit"] || 0),
      quantity: 1,
    });
    setPendingItems(pending);
    setAddedDescs((prev) => ({ ...prev, [desc]: true }));
  };

  const handleGoToList = () => { window.location.href = "/material_list?list=new"; };
  const pendingCount = getPendingItems().length;

  // Build ordered description groups from the sorted rows
  const groups = React.useMemo(() => {
    const map = new Map();
    for (const row of rows) {
      const desc = row.Description || "";
      if (!map.has(desc)) map.set(desc, []);
      map.get(desc).push(row);
    }
    return [...map.entries()];
  }, [rows]);

  // Per-row columns (Description is the group header, so skip it here)
  const rowCols = (columns || []).filter((c) => c !== "Description");

  return (
    <div className="space-y-6">
      {/* Search controls */}
      <div className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Search Description</h1>
            <p className="text-sm text-slate-500">Results update as you type (300 ms debounce).</p>
          </div>
          {pendingCount > 0 && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleGoToList}
                className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition"
              >
                <span>🛒</span>
                <span>{pendingCount} item{pendingCount !== 1 ? "s" : ""} — Go to Material List</span>
              </button>
              <button
                onClick={() => { setPendingItems([]); sessionStorage.removeItem("zpl_new_list_name"); setAddedDescs({}); }}
                className="rounded-xl bg-rose-500 px-3 py-2 text-sm font-semibold text-white hover:bg-rose-600 transition"
              >
                ✕ Clear List
              </button>
            </div>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <input
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder="e.g. copper elbow 1/2"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
          <select
            value={supply}
            onChange={handleSupplyChange}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            {(data.supplyOptions || []).map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <SkeletonRows cols={(rowCols.length || 4) + 1} rows={6} />
      ) : groups.length === 0 && query.trim() ? (
        <p className="text-sm text-slate-500 px-1">No results found.</p>
      ) : (
        <div className="space-y-3">
          {groups.map(([desc, groupRows]) => {
            const recentRows = groupRows.filter((r) => r.is_recent);
            const histRows   = groupRows.filter((r) => !r.is_recent);
            const isExpanded = expanded.has(desc);
            const displayRows = isExpanded ? groupRows : recentRows;
            const graphUrl   = groupRows[0]?.graphUrl;
            const isAdded    = !!addedDescs[desc];

            return (
              <div key={desc} className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
                {/* Group header */}
                <div className="flex items-center justify-between gap-3 px-4 py-3 bg-slate-50 border-b border-slate-200 flex-wrap">
                  <span className="font-semibold text-slate-800 text-sm">{desc}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    {histRows.length > 0 && (
                      <button
                        onClick={() => toggleExpanded(desc)}
                        className="rounded-lg border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 transition"
                      >
                        {isExpanded ? "Hide History" : `Show History (${histRows.length} more)`}
                      </button>
                    )}
                    {graphUrl && (
                      <a
                        href={graphUrl}
                        className="rounded-lg border border-sky-300 px-3 py-1 text-xs font-medium text-sky-700 hover:bg-sky-50 transition"
                      >
                        Graph
                      </a>
                    )}
                    <button
                      onClick={() => handleAddToList(recentRows[0] || groupRows[0], desc)}
                      disabled={isAdded}
                      className={classNames(
                        "rounded-lg px-3 py-1 text-xs font-semibold transition",
                        isAdded
                          ? "bg-emerald-100 text-emerald-700 cursor-default"
                          : "bg-sky-600 text-white hover:bg-sky-700"
                      )}
                    >
                      {isAdded ? "✓ Added" : "+ Add"}
                    </button>
                  </div>
                </div>

                {/* Rows table */}
                <div className="overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead className="bg-slate-100 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      <tr>
                        {rowCols.map((col) => (
                          <th key={col} className="px-4 py-2 text-left whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {displayRows.map((row, i) => (
                        <tr key={i} className={classNames("hover:bg-slate-50", !row.is_recent && "text-slate-400")}>
                          {rowCols.map((col) => (
                            <td key={col} className="px-4 py-2 whitespace-nowrap">{row[col] ?? ""}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ================================================================
// AnalyzePage — IMPROVEMENT #12: CSV export button
// ================================================================
function AnalyzePage({ data }) {
  const [supply, setSupply] = useState(data.supply || "supply1");
  const [startDate, setStartDate] = useState(data.startDate || "");
  const [endDate, setEndDate] = useState(data.endDate || "");
  const [columns, setColumns] = useState(data.columns || []);
  const [rows, setRows] = useState(data.rows || []);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    setLoading(true);
    fetch(data.analyzeApi || "/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ supply, start_date: startDate, end_date: endDate }),
    })
      .then((r) => r.json())
      .then((p) => { setColumns(p.columns || []); setRows(p.rows || []); })
      .finally(() => setLoading(false));
  };

  // IMPROVEMENT #12: export to CSV
  const handleExportCSV = () => {
    if (!rows.length) return;
    const header = columns.join(",");
    const body = rows.map((row) =>
      columns.map((col) => {
        const val = row[col] ?? "";
        return typeof val === "string" && val.includes(",") ? `"${val}"` : val;
      }).join(",")
    ).join("\n");
    const blob = new Blob([header + "\n" + body], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `price_analysis_${supply}_${startDate}_${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 lg:grid-cols-4"
      >
        <div className="lg:col-span-4">
          <h1 className="text-2xl font-semibold text-slate-900">Analyze Price Changes</h1>
          <p className="mt-1 text-sm text-slate-500">
            Compare monthly price averages and surface items that changed between periods.
          </p>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supplier</label>
          <select
            value={supply}
            onChange={(e) => setSupply(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            {(data.supplyOptions || []).map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="flex items-end gap-2">
          <Button type="submit" className="flex-1" disabled={loading}>
            {loading ? "Analyzing…" : "Analyze"}
          </Button>
          {/* IMPROVEMENT #12 */}
          {rows.length > 0 && (
            <Button type="button" variant="secondary" onClick={handleExportCSV} title="Export to CSV">
              ⬇ CSV
            </Button>
          )}
        </div>
      </form>

      {loading ? (
        <SkeletonRows cols={5} rows={8} />
      ) : rows.length === 0 ? (
        <EmptyState title="No results" description="Adjust the date range and run the analysis." />
      ) : (
        <Table
          columns={columns}
          rows={rows}
          renderRow={(row, index) => (
            <>
              {columns.map((column) => (
                <td key={`${column}-${index}`} className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {row[column] ?? ""}
                </td>
              ))}
            </>
          )}
        />
      )}
    </div>
  );
}

// ================================================================
// ProductDetailPage
// ================================================================
function ProductDetailPage({ data }) {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!chartRef.current || !data.chart) return;
    if (chartInstance.current) chartInstance.current.destroy();
    chartInstance.current = new Chart(chartRef.current, {
      type: "line",
      data: {
        labels: data.chart.dates || [],
        datasets: [{
          label: "Price per Unit",
          data: data.chart.prices || [],
          borderColor: "#0284c7",
          backgroundColor: "rgba(2,132,199,0.08)",
          pointRadius: 4,
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: false } },
      },
    });
    return () => { if (chartInstance.current) chartInstance.current.destroy(); };
  }, [data.chart]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        {data.backUrl && (
          <Button as="a" href={data.backUrl} variant="ghost" className="text-xs px-2 py-1">
            ← Back
          </Button>
        )}
        <h1 className="text-xl font-semibold text-slate-900 truncate">{data.description}</h1>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-4 text-sm font-semibold text-slate-900">Price History</h2>
          <canvas ref={chartRef} />
        </div>
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="mb-4 text-sm font-semibold text-slate-900">Transactions</h2>
          <Table
            columns={["Date", "Price per Unit"]}
            rows={data.rows || []}
            renderRow={(row) => (
              <>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{row.Date}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{row["Price per Unit"]}</td>
              </>
            )}
          />
        </div>
      </div>
    </div>
  );
}

// ================================================================
// MaterialListPage — IMPROVEMENT #8: min/step on qty inputs
//                  IMPROVEMENT #6: PDF loading state
//                  IMPROVEMENT #7: consume pending cart items
//                  IMPROVEMENT #11: mobile card layout
// ================================================================
// ================================================================
// IMPROVED MaterialListPage
// New features:
//  - Sticky header row while scrolling
//  - Always-visible price summary panel (subtotal, tax, total)
//  - Autocomplete descriptions from catalog (already existed via
//    <datalist> but now shown as a live dropdown suggestion panel)
//  - Duplicate row button per item
//  - Cleaner project info section with labels
// ================================================================
function MaterialListPage({ data }) {
  const TAX_RATE = 0.07;

  const catalogLookups = useMemo(() => {
    const lookups = {};
    Object.entries(data.catalog || {}).forEach(([key, records]) => {
      const map = {};
      (records || []).forEach((item) => {
        const description = (
          item.Description ||
          item["Product Description"] ||
          item.description ||
          ""
        )
          .toLowerCase()
          .trim();
        if (!description) return;
        const price =
          parseFloat(item["Price per Unit"] ?? item.price ?? item.last_price ?? 0) || 0;
        const unit = item.Unit || item.unit || "";
        const dateValue = item.Date || item.date;
        const date = dateValue ? new Date(dateValue) : new Date(0);
        const existing = map[description];
        if (!existing || date > existing.date) {
          map[description] = { price, unit, date };
        }
      });
      lookups[key] = map;
    });
    return lookups;
  }, [data.catalog]);

  // All unique descriptions per supply for autocomplete
  const datalistOptions = useMemo(() => {
    const options = {};
    Object.entries(data.catalog || {}).forEach(([key, records]) => {
      const unique = Array.from(
        new Set(
          (records || []).map(
            (r) => r.Description || r["Product Description"] || r.description || ""
          )
        )
      ).filter(Boolean);
      options[key] = unique;
    });
    return options;
  }, [data.catalog]);

  const [lookupSupply, setLookupSupply] = useState("supply1");
  const [templateFolder, setTemplateFolder] = useState(data.templateFolder || "");
  const [templateName, setTemplateName] = useState(   data.templateName || sessionStorage.getItem("zpl_new_list_name") || "" );
  // Clear the stored list name after consuming it
useEffect(() => {
  if (sessionStorage.getItem("zpl_new_list_name")) {
    sessionStorage.removeItem("zpl_new_list_name");
  }
}, []);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [projectInfo, setProjectInfo] = useState({
    contractor: data.projectInfo?.contractor || "",
    address: data.projectInfo?.address || "",
    date: data.projectInfo?.date || new Date().toISOString().slice(0, 10),
  });

  const [items, setItems] = useState(() => {
  const fromServer = (data.products || []).map((product) => ({
    quantity: Number(product.quantity ?? product.Quantity ?? 0) || 0,
    description: product["Product Description"] || product.description || "",
    supply: product.Supply || product.supply || supplyCodes[lookupSupply],
    lookupSupply:
      getSupplyKeyFromCode(product.Supply || product.supply) || lookupSupply,
    unit: product.Unit || product.unit || "",
    lastPrice:
      Number(
        product["Last Price"] ??
          product.last_price ??
          product["Price per Unit"] ??
          0
      ) || 0,
    predetermined: true,
  }));

  // Consume pending cart items added from Search Description
  const pending = getPendingItems();
  if (pending.length > 0) {
    setPendingItems([]); // clear the cart now that we've consumed it
    const fromCart = pending.map((item) => ({
      quantity: item.quantity ?? 1,
      description: item.description || "",
      supply: item.supply || supplyCodes[lookupSupply],
      lookupSupply: item.lookupSupply || lookupSupply,
      unit: item.unit || "",
      lastPrice: item.lastPrice || 0,
      predetermined: false,
    }));
    return [...fromServer, ...fromCart];
  }

  return fromServer;
});

  const [draggingIndex, setDraggingIndex] = useState(null);
  const productDataRef = useRef(null);
  const includePriceRef = useRef(null);
  const formRef = useRef(null);

  // ---- item mutations ----
  const updateItem = (index, updates) => {
    setItems((current) => {
      const next = [...current];
      const nextItem = { ...next[index], ...updates };
      const quantity = Number(nextItem.quantity) || 0;
      const lastPrice = Number(nextItem.lastPrice) || 0;
      nextItem.total = Number((quantity * lastPrice).toFixed(2));
      next[index] = nextItem;
      return next;
    });
  };

  const handleDescriptionChange = (index, value) => {
    const normalized = value.toLowerCase().trim();
    const entry = catalogLookups[lookupSupply]?.[normalized];
    if (entry) {
      updateItem(index, {
        description: value,
        supply: supplyCodes[lookupSupply],
        lookupSupply,
        unit: entry.unit || "",
        lastPrice: Number(entry.price.toFixed(2)),
      });
    } else {
      updateItem(index, { description: value, lookupSupply });
    }
  };

  const handleQuantityChange = (index, rawValue) => {
    if (rawValue === "") { updateItem(index, { quantity: "" }); return; }
    const n = Math.max(0, Math.round(Number(rawValue)));
    updateItem(index, { quantity: Number.isFinite(n) ? n : 0 });
  };

  const addManualItem = () => {
  setItems((c) => [
    ...c,
    {
      quantity: 0,
      description: "",
      supply: supplyCodes[lookupSupply],
      lookupSupply,
      unit: "",
      lastPrice: 0,
      predetermined: false,
    },
  ]);
};

  // NEW: duplicate a row
  const duplicateItem = (index) => {
    setItems((c) => {
      const next = [...c];
      next.splice(index + 1, 0, { ...c[index] });
      return next;
    });
  };

  const removeItem = (index) => {
    setItems((c) => c.filter((_, i) => i !== index));
  };

  const moveItem = (index, direction) => {
    setItems((c) => {
      const next = [...c];
      const target = index + direction;
      if (target < 0 || target >= next.length) return next;
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return next;
    });
  };

  const handleDragStart = (e, index) => {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
    setDraggingIndex(index);
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggingIndex === null || draggingIndex === index) return;
    setItems((c) => {
      const next = [...c];
      const [moved] = next.splice(draggingIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDraggingIndex(index);
  };

  const handleDrop = (e) => { e.preventDefault(); setDraggingIndex(null); };
  const handleDragEnd = () => setDraggingIndex(null);

  const handleSupplyChange = (index, supplyKey) => {
    updateItem(index, { supply: supplyCodes[supplyKey] || supplyKey, lookupSupply: supplyKey });
  };
  const handleUnitChange  = (index, value) => updateItem(index, { unit: value });
  const handlePriceChange = (index, value) => updateItem(index, { lastPrice: parseFloat(value) || 0 });

  // ---- totals ----
  const subtotal = useMemo(
    () =>
      items.reduce(
        (sum, item) =>
          sum +
          Number(
            item.total || (Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)
          ),
        0
      ),
    [items]
  );
  const tax = subtotal * TAX_RATE;
  const grandTotal = subtotal + tax;

  const serializeProducts = () =>
    items.map((item) => ({
      description: item.description,
      supply: item.supply,
      unit: item.unit,
      last_price: Number(item.lastPrice || 0),
      quantity: Number(item.quantity || 0),
      total: Number(
        ((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)
      ),
    }));
  const [pdfLoading, setPdfLoading] = useState(false);
  const handleExport = () => {
    const includePrice = window.confirm("Include prices in the PDF?");
    if (includePriceRef.current) includePriceRef.current.value = includePrice ? "yes" : "no";
    if (productDataRef.current)
      productDataRef.current.value = JSON.stringify(serializeProducts());
    setPdfLoading(true);
    setTimeout(() => {
      formRef.current?.submit();
      setTimeout(() => setPdfLoading(false), 8000);
    }, 100);
  };

  const handleSaveTemplate = () => {
    if (!templateName.trim()) { window.alert("Template name required"); return; }
    const folder = templateFolder.trim();
    const fullName = folder ? `${folder}/${templateName.trim()}` : templateName.trim();
    const payload = new URLSearchParams();
    payload.set("template_name", fullName);
    payload.set("product_data", JSON.stringify(serializeProducts()));
    payload.set("project_info", JSON.stringify(projectInfo));
    setSavingTemplate(true);
    setSaveSuccess(false);
    fetch(data.saveTemplateUrl || "/save_template", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: payload.toString(),
    })
      .then(() => { setSaveSuccess(true); })
      .catch(() => window.alert("Error saving template."))
      .finally(() => setSavingTemplate(false));
  };

  const handleTemplateChange = (e) => {
    const value = e.target.value;
    window.location.href = `${data.listUrl}?list=${encodeURIComponent(value)}`;
  };

  const supplyListId = {
    supply1: "supply1List",
    supply2: "supply2List",
    supply3: "supply3List",
    supply4: "supply4List",
  };

  return (
    <div className="space-y-6">

      {/* ── Header ── */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Material List</h1>
          {data.fullTemplateName && (
            <span className="mt-1 inline-flex items-center rounded-full bg-sky-100 px-3 py-0.5 text-xs font-medium text-sky-700">
              Editing: {data.fullTemplateName}
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleExport}
            disabled={pdfLoading || items.length === 0}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 transition"
          >
            {pdfLoading ? "⏳ Generating…" : "📄 Export PDF"}
          </button>
          <a
            href={data.downloadUrl}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition"
          >
            ⬇ Download Last PDF
          </a>
        </div>
      </div>

      {/* ── Top panel: project info + template select ── */}
      <div className="grid gap-4 lg:grid-cols-3">

        {/* Project info */}
        <div className="lg:col-span-2 rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Project Information</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Contractor</label>
              <input
                value={projectInfo.contractor}
                onChange={(e) => setProjectInfo((p) => ({ ...p, contractor: e.target.value }))}
                placeholder="Contractor name"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Job Address</label>
              <input
                value={projectInfo.address}
                onChange={(e) => setProjectInfo((p) => ({ ...p, address: e.target.value }))}
                placeholder="123 Main St"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Date</label>
              <input
                type="date"
                value={projectInfo.date}
                onChange={(e) => setProjectInfo((p) => ({ ...p, date: e.target.value }))}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Load Template</label>
              <select
                value={data.listOption || "underground"}
                onChange={handleTemplateChange}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              >
                <option value="underground">Underground List</option>
                <option value="rough">Rough List</option>
                <option value="final">Final List</option>
                <option value="new">— New Empty List —</option>
                {(data.customTemplates || []).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-slate-500">Price Lookup Supply</label>
              <select
                value={lookupSupply}
                onChange={(e) => setLookupSupply(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              >
                <option value="supply1">Supply 1 (BPS)</option>
                <option value="supply2">Supply 2</option>
                <option value="supply3">Lion Plumbing Supply</option>
                <option value="supply4">Bond Plumbing Supply</option>
              </select>
            </div>
          </div>
        </div>

        {/* ── ALWAYS-VISIBLE price summary panel ── */}
        <div className="rounded-2xl bg-slate-900 p-5 text-white shadow-sm space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Order Summary</h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Items</span>
              <span className="font-medium">{items.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Subtotal</span>
              <span className="font-medium">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Tax (7%)</span>
              <span className="font-medium">${tax.toFixed(2)}</span>
            </div>
            <div className="mt-1 border-t border-slate-700 pt-2 flex justify-between">
              <span className="font-semibold text-white">Total</span>
              <span className="text-lg font-bold text-sky-400">${grandTotal.toFixed(2)}</span>
            </div>
          </div>
          {/* Quick save template inside summary panel */}
          <div className="border-t border-slate-700 pt-3 space-y-2">
            <p className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Save as Template</p>
            <input
              value={templateFolder}
              onChange={(e) => setTemplateFolder(e.target.value)}
              list="template-folders"
              placeholder="Folder (optional)"
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
            <input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              placeholder="Template name"
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-2 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
            <button
              onClick={handleSaveTemplate}
              disabled={savingTemplate || !templateName.trim()}
              className="w-full rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition"
            >
              {savingTemplate ? "Saving…" : saveSuccess ? "✓ Saved!" : "Save Template"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Item table with sticky header ── */}
      <div className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
        <div className="overflow-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            {/* STICKY header */}
            <thead className="bg-slate-50 sticky top-0 z-10 shadow-sm">
              <tr>
                {["#", "Qty", "Description", "Supply", "Unit", "Price", "Total", "Actions"].map((h) => (
                  <th
                    key={h}
                    className="whitespace-nowrap px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-sm text-slate-400">
                    No items yet — add one below or load a template above.
                  </td>
                </tr>
              )}
              {items.map((item, index) => (
                <tr
                  key={index}
                  draggable
                  onDragStart={(e) => handleDragStart(e, index)}
                  onDragOver={(e) => handleDragOver(e, index)}
                  onDrop={handleDrop}
                  onDragEnd={handleDragEnd}
                  className={classNames(
                    "transition",
                    draggingIndex === index
                      ? "opacity-40 bg-sky-50"
                      : "hover:bg-slate-50"
                  )}
                  style={{ cursor: "grab" }}
                >
                  {/* Row number */}
                  <td className="px-3 py-1 text-slate-400 select-none">{index + 1}</td>

                  {/* Quantity */}
                  <td className="px-2 py-1">
                    <input
                      type="number"
                      min="0"
                      step="1"
                      value={item.quantity === "" ? "" : item.quantity}
                      onChange={(e) => handleQuantityChange(index, e.target.value)}
                      className="w-14 rounded border border-slate-300 px-1.5 py-0.5 text-center text-sm focus:border-sky-500 focus:outline-none"
                    />
                  </td>

                  {/* Description — with autocomplete datalist */}
                  <td className="px-2 py-1 min-w-[220px]">
                    <input
                      type="text"
                      value={item.description}
                      onChange={(e) => handleDescriptionChange(index, e.target.value)}
                      list={supplyListId[item.lookupSupply || lookupSupply]}
                      placeholder="Type or pick description…"
                      className="w-full rounded border border-slate-300 px-1.5 py-0.5 text-sm focus:border-sky-500 focus:outline-none"
                    />
                  </td>

                  {/* Supply — badge for template rows, dropdown for manual rows */}
                  <td className="px-2 py-1 whitespace-nowrap">
                    {item.predetermined ? (
                      <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                        {item.supply}
                      </span>
                    ) : (
                      <select
                        value={item.lookupSupply || lookupSupply}
                        onChange={(e) => handleSupplyChange(index, e.target.value)}
                        className="rounded border border-slate-300 px-1.5 py-0.5 text-xs focus:border-sky-500 focus:outline-none"
                      >
                        <option value="supply1">BPS</option>
                        <option value="supply2">S2</option>
                        <option value="supply3">LPS</option>
                        <option value="supply4">BOND</option>
                      </select>
                    )}
                  </td>

                  {/* Unit — read-only for template rows, editable for manual rows */}
                  <td className="px-2 py-1 whitespace-nowrap text-slate-500">
                    {item.predetermined ? (
                      item.unit || "—"
                    ) : (
                      <input
                        type="text"
                        value={item.unit}
                        onChange={(e) => handleUnitChange(index, e.target.value)}
                        placeholder="EA"
                        className="w-16 rounded border border-slate-300 px-1.5 py-0.5 text-sm focus:border-sky-500 focus:outline-none"
                      />
                    )}
                  </td>

                  {/* Price — read-only for template rows, editable for manual rows */}
                  <td className="px-2 py-1 whitespace-nowrap text-slate-700">
                    {item.predetermined ? (
                      `$${Number(item.lastPrice || 0).toFixed(2)}`
                    ) : (
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        value={item.lastPrice || ""}
                        onChange={(e) => handlePriceChange(index, e.target.value)}
                        placeholder="0.00"
                        className="w-20 rounded border border-slate-300 px-1.5 py-0.5 text-sm focus:border-sky-500 focus:outline-none"
                      />
                    )}
                  </td>

                  {/* Total — highlighted */}
                  <td className="px-2 py-1 whitespace-nowrap font-semibold text-slate-900">
                    ${((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)}
                  </td>

                  {/* Actions */}
                  <td className="px-2 py-1">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => moveItem(index, -1)}
                        className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-bold text-slate-500 hover:bg-slate-200 transition"
                        title="Move up"
                      >↑</button>
                      <button
                        onClick={() => moveItem(index, 1)}
                        className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-bold text-slate-500 hover:bg-slate-200 transition"
                        title="Move down"
                      >↓</button>
                      {/* NEW: duplicate button */}
                      <button
                        onClick={() => duplicateItem(index)}
                        className="rounded bg-sky-100 px-1.5 py-0.5 text-[11px] font-bold text-sky-600 hover:bg-sky-200 transition"
                        title="Duplicate row"
                      >⧉</button>
                      <button
                        onClick={() => removeItem(index)}
                        className="rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-bold text-rose-600 hover:bg-rose-200 transition"
                        title="Remove"
                      >✕</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>

            {/* Sticky footer totals row */}
            <tfoot className="bg-slate-50 sticky bottom-0 border-t border-slate-200">
              <tr>
                <td colSpan={6} className="px-3 py-2 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  Subtotal
                </td>
                <td className="px-2 py-2 font-semibold text-slate-800">${subtotal.toFixed(2)}</td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={6} className="px-3 py-1 text-right text-xs text-slate-400">
                  Tax 7%
                </td>
                <td className="px-2 py-1 text-xs text-slate-500">${tax.toFixed(2)}</td>
                <td></td>
              </tr>
              <tr>
                <td colSpan={6} className="px-3 py-2 text-right text-sm font-bold text-slate-700">
                  Grand Total
                </td>
                <td className="px-2 py-2 text-sm font-bold text-sky-700">${grandTotal.toFixed(2)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Add Item button — appends an empty editable row to the table */}
      <button
        onClick={addManualItem}
        className="inline-flex items-center gap-2 rounded-xl border-2 border-dashed border-slate-300 px-6 py-3 text-sm font-semibold text-slate-500 hover:border-sky-400 hover:text-sky-600 transition w-full justify-center"
      >
        + Add Item
      </button>

      {/* Hidden form for PDF submit */}
      <form ref={formRef} method="POST" action={data.listUrl} className="hidden">
        <input type="hidden" name="contractor" value={projectInfo.contractor} />
        <input type="hidden" name="address" value={projectInfo.address} />
        <input type="hidden" name="date" value={projectInfo.date} />
        <input type="hidden" name="product_data" ref={productDataRef} />
        <input type="hidden" name="include_price" ref={includePriceRef} value="yes" />
      </form>

      {/* Datalists for autocomplete */}
      <datalist id="supply1List">
        {(datalistOptions.supply1 || []).map((o) => <option key={o} value={o} />)}
      </datalist>
      <datalist id="supply2List">
        {(datalistOptions.supply2 || []).map((o) => <option key={o} value={o} />)}
      </datalist>
      <datalist id="supply3List">
        {(datalistOptions.supply3 || []).map((o) => <option key={o} value={o} />)}
      </datalist>
      <datalist id="supply4List">
        {(datalistOptions.supply4 || []).map((o) => <option key={o} value={o} />)}
      </datalist>
      <datalist id="template-folders">
        {(data.templateFolders || []).map((f) => <option key={f} value={f} />)}
      </datalist>
    </div>
  );
}



// ================================================================
// IMPROVED TemplatesPage
// New features:
//  - Item count badge per template
//  - Expandable preview panel showing items before loading
//  - Quick-load button (loads into Material List without page nav)
//  - Duplicate template button
//  - Filter search bar
// ================================================================
function TemplatesPage({ data }) {
  const entries = data.entries || [];
  const grouped = data.grouped || {};

  const [filterQuery, setFilterQuery] = useState("");
  const [expandedFolders, setExpandedFolders] = useState(() => {
    const initial = {};
    Object.keys(grouped).forEach((folder) => {
      initial[folder || "__root__"] = true;
    });
    return initial;
  });
  const [previewEntry, setPreviewEntry] = useState(null); // which template is expanded
  const [previewItems, setPreviewItems] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [duplicating, setDuplicating] = useState(null);

  const filteredEntries = useMemo(() => {
    if (!filterQuery.trim()) return entries;
    const q = filterQuery.toLowerCase();
    return entries.filter((e) => e.full_name?.toLowerCase().includes(q));
  }, [entries, filterQuery]);

  const filteredGrouped = useMemo(() => {
    const result = {};
    filteredEntries.forEach((e) => {
      const key = e.group || "";
      if (!result[key]) result[key] = [];
      result[key].push(e);
    });
    return result;
  }, [filteredEntries]);

  const toggleFolder = (folder) => {
    const key = folder || "__root__";
    setExpandedFolders((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleAction = (url, body) => {
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(body || {}).toString(),
    }).then(() => window.location.reload());
  };

  const confirmAndDelete = (entry) => {
    if (window.confirm(`Delete "${entry.full_name}"?`)) handleAction(entry.delete_url);
  };

  const promptRename = (entry) => {
    const next = window.prompt("New template name:", entry.name);
    if (next && next.trim()) handleAction(entry.rename_url, { new_name: next.trim() });
  };

  const promptMove = (entry) => {
    const target = window.prompt("Move to folder (leave blank for root):", entry.group || "");
    if (target !== null) handleAction(entry.move_url, { target_folder: target });
  };

  // NEW: preview template items
  const handlePreview = (entry) => {
    if (previewEntry?.full_name === entry.full_name) {
      setPreviewEntry(null);
      setPreviewItems([]);
      return;
    }
    setPreviewEntry(entry);
    setPreviewLoading(true);
    fetch(`/api/template_preview?name=${encodeURIComponent(entry.full_name)}`)
      .then((r) => r.json())
      .then((d) => setPreviewItems(d.products || []))
      .catch(() => setPreviewItems([]))
      .finally(() => setPreviewLoading(false));
  };

  // NEW: duplicate template
  const handleDuplicate = (entry) => {
    const newName = window.prompt(
      "Name for the duplicate:",
      `${entry.name}_copy`
    );
    if (!newName || !newName.trim()) return;
    setDuplicating(entry.full_name);
    fetch("/api/duplicate_template", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        source_name: entry.full_name,
        new_name: newName.trim(),
      }).toString(),
    })
      .then(() => window.location.reload())
      .finally(() => setDuplicating(null));
  };

  const renderEntries = (rows) =>
    rows.map((row) => (
      <div key={row.full_name} className="rounded-xl bg-white ring-1 ring-slate-200 overflow-hidden">
        {/* Main row */}
        <div className="flex flex-wrap items-center gap-3 px-4 py-3">
          {/* Name + meta */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-slate-800 truncate">
                {row.name}
              </span>
              {/* Item count badge */}
              {row.item_count != null && (
                <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                  {row.item_count} item{row.item_count !== 1 ? "s" : ""}
                </span>
              )}
              {/* Total badge */}
              {row.total_with_tax != null && (
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
                  ${row.total_with_tax.toFixed(2)} w/tax
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-slate-400">
              {row.mtime ? new Date(row.mtime * 1000).toLocaleString() : ""}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {/* Preview toggle */}
            <button
              onClick={() => handlePreview(row)}
              className={classNames(
                "rounded-lg px-2.5 py-1 text-xs font-semibold transition",
                previewEntry?.full_name === row.full_name
                  ? "bg-sky-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              )}
              title="Preview items"
            >
              {previewEntry?.full_name === row.full_name ? "▲ Hide" : "▼ Preview"}
            </button>

            {/* Load directly */}
            <a
              href={`${data.materialListUrl || "/material_list"}?list=${encodeURIComponent(row.full_name)}`}
              className="rounded-lg bg-sky-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-sky-700 transition"
            >
              Load
            </a>

            {/* Duplicate */}
            <button
              onClick={() => handleDuplicate(row)}
              disabled={duplicating === row.full_name}
              className="rounded-lg bg-violet-100 px-2.5 py-1 text-xs font-semibold text-violet-700 hover:bg-violet-200 transition disabled:opacity-50"
              title="Duplicate template"
            >
              {duplicating === row.full_name ? "…" : "⧉ Copy"}
            </button>

            <button
              onClick={() => promptRename(row)}
              className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
            >
              Rename
            </button>
            <button
              onClick={() => promptMove(row)}
              className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
            >
              Move
            </button>
            <button
              onClick={() => confirmAndDelete(row)}
              className="rounded-lg bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-600 hover:bg-rose-200 transition"
            >
              Delete
            </button>
          </div>
        </div>

        {/* Preview panel */}
        {previewEntry?.full_name === row.full_name && (
          <div className="border-t border-slate-100 bg-slate-50 px-4 py-3">
            {previewLoading ? (
              <p className="text-xs text-slate-400 py-2">Loading preview…</p>
            ) : previewItems.length === 0 ? (
              <p className="text-xs text-slate-400 py-2">No items in this template.</p>
            ) : (
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-left text-slate-400">
                    <th className="pb-1 pr-4 font-semibold">Description</th>
                    <th className="pb-1 pr-4 font-semibold">Qty</th>
                    <th className="pb-1 pr-4 font-semibold">Unit</th>
                    <th className="pb-1 pr-4 font-semibold">Price</th>
                    <th className="pb-1 font-semibold">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {previewItems.map((item, i) => (
                    <tr key={i} className="text-slate-700">
                      <td className="py-1 pr-4 max-w-xs truncate">{item.description || item["Product Description"] || "—"}</td>
                      <td className="py-1 pr-4">{item.quantity ?? "—"}</td>
                      <td className="py-1 pr-4">{item.unit || "—"}</td>
                      <td className="py-1 pr-4">${Number(item.last_price || 0).toFixed(2)}</td>
                      <td className="py-1">${Number(item.total || 0).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    ));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Saved Templates</h1>
          <p className="mt-1 text-sm text-slate-500">
            {entries.length} template{entries.length !== 1 ? "s" : ""} saved
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Filter templates…"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200 w-52"
          />
          <a
            href={data.materialListUrl || "/material_list"}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 transition"
          >
            + New List
          </a>
        </div>
      </div>

      {/* Folder groups */}
      {Object.keys(filteredGrouped).length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl bg-white py-16 shadow-sm ring-1 ring-slate-200">
          <p className="text-sm font-semibold text-slate-700">No templates found</p>
          <p className="mt-1 text-xs text-slate-500">
            {filterQuery ? "Try a different search term." : "Save a template from the Material List page."}
          </p>
        </div>
      ) : (
        Object.entries(filteredGrouped).map(([folder, folderEntries]) => {
          const key = folder || "__root__";
          const isExpanded = expandedFolders[key] ?? true;
          return (
            <div key={key} className="space-y-2">
              {/* Folder header */}
              <button
                onClick={() => toggleFolder(folder)}
                className="flex w-full items-center justify-between rounded-xl bg-slate-100 px-4 py-2.5 text-left text-sm font-semibold text-slate-700 hover:bg-slate-200 transition"
              >
                <span className="flex items-center gap-2">
                  <span>{folder || "📁 Ungrouped"}</span>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200">
                    {folderEntries.length}
                  </span>
                </span>
                <span className={classNames("text-slate-400 transition-transform text-xs", isExpanded ? "rotate-180" : "")}>
                  ▲
                </span>
              </button>

              {isExpanded && (
                <div className="space-y-2 pl-2">
                  {renderEntries(folderEntries)}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}

// ================================================================
// UploadPdfPage
// ================================================================
function UploadPdfPage({ data }) {
  const SUPPLIERS = data.suppliers || [
    { code: "LPS",  label: "Lion Plumbing Supply" },
    { code: "BPS",  label: "Berger Plumbing Supply" },
    { code: "S2",   label: "Supply 2" },
    { code: "BOND", label: "Bond Plumbing Supply" },
  ];

  const [supplier, setSupplier]   = useState("LPS");
  const [dragging, setDragging]   = useState(false);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving]       = useState(false);
  const [parsed, setParsed]       = useState(null);   // editable preview state
  const [file, setFile]           = useState(null);   // original File object
  const [result, setResult]       = useState(null);   // confirmed-save result
  const [error, setError]         = useState("");
  const [invoices]                = useState(data.invoices || []);
  const fileInputRef = useRef(null);

  // ── Step 1: parse the PDF (does NOT save) ───────────────────────────────
  const parseFile = async (f) => {
    if (!f || !f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }
    setFile(f);
    setUploading(true);
    setError("");
    setParsed(null);
    setResult(null);

    const formData = new FormData();
    formData.append("pdf_file", f);
    formData.append("supplier", supplier);

    try {
      const resp = await fetch(data.uploadUrl || "/upload_pdf", {
        method: "POST",
        body: formData,
      });
      const json = await resp.json();

      if (json.success) {
        setParsed({
          doc_type:     json.doc_type,
          order_number: json.order_number,
          date:         json.date         || "",
          job_name:     json.job_name     || "",
          supplier:     json.supplier     || supplier,
          items: (json.items || []).map((item, i) => ({ ...item, _id: i })),
        });
      } else {
        setError(json.error || "Parse failed.");
      }
    } catch (e) {
      setError("Network error. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  // ── Step 2: confirm & save the (possibly edited) data ───────────────────
  const confirmSave = async () => {
    if (!parsed) return;
    setSaving(true);
    setError("");

    const payload = {
      parsed: {
        ...parsed,
        items: parsed.items.map(({ _id, ...rest }) => rest),
      },
      filename: file?.name || "",
    };

    try {
      const resp = await fetch(data.confirmUrl || "/confirm_upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const json = await resp.json();

      if (json.success) {
        setResult(json);
        setParsed(null);
        setFile(null);
        window.location.reload();
      } else if (json.duplicate) {
        setError(`Already imported: ${json.error}`);
      } else {
        setError(json.error || "Save failed.");
      }
    } catch (e) {
      setError("Network error during save.");
    } finally {
      setSaving(false);
    }
  };

  // ── Item editing helpers ────────────────────────────────────────────────
  const updateItem = (idx, field, value) =>
    setParsed(prev => ({
      ...prev,
      items: prev.items.map((item, i) => i === idx ? { ...item, [field]: value } : item),
    }));

  const deleteItem = (idx) =>
    setParsed(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== idx) }));

  const addRow = () =>
    setParsed(prev => ({
      ...prev,
      items: [...prev.items, { _id: Date.now(), item_number: "", description: "", uom: "EA", quantity: 1, unit_price: 0 }],
    }));

  // ── File input handlers ─────────────────────────────────────────────────
  const handleFileInput = (e) => {
    const f = e.target.files?.[0];
    if (f) parseFile(f);
    e.target.value = "";
  };
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) parseFile(f);
  };
  const handleDragOver  = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  const docTypeBadge = (type) =>
    type === "invoice" ? "bg-sky-100 text-sky-700" : "bg-violet-100 text-violet-700";

  const inputCls = "w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-xs focus:border-sky-400 focus:outline-none focus:ring-1 focus:ring-sky-300";

  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Upload PDF Invoice or Bid</h1>
        <p className="mt-1 text-sm text-slate-500">
          Select a supplier, drop a PDF to parse it, review and edit the extracted items,
          then confirm to save to the database.
        </p>
      </div>

      {/* Supplier + drop zone — hidden while preview is shown */}
      {!parsed && (
        <>
          {/* Supplier dropdown */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700 shrink-0">Supplier</label>
            <select
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-sky-400"
            >
              {SUPPLIERS.map((s) => (
                <option key={s.code} value={s.code}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={classNames(
              "flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-12 cursor-pointer transition",
              dragging
                ? "border-sky-500 bg-sky-50"
                : "border-slate-300 bg-white hover:border-sky-400 hover:bg-slate-50"
            )}
          >
            <input ref={fileInputRef} type="file" accept=".pdf" className="hidden" onChange={handleFileInput} />
            {uploading ? (
              <>
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-sky-600 border-t-transparent" />
                <p className="text-sm font-semibold text-sky-700">Parsing PDF…</p>
              </>
            ) : (
              <>
                <span className="text-4xl">📄</span>
                <p className="text-sm font-semibold text-slate-700">
                  Drop PDF here or <span className="text-sky-600 underline">click to browse</span>
                </p>
                <p className="text-xs text-slate-400">
                  {SUPPLIERS.find((s) => s.code === supplier)?.label} format
                </p>
              </>
            )}
          </div>
        </>
      )}

      {/* Error banner */}
      {error && (
        <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-200">
          ⚠ {error}
        </div>
      )}

      {/* ── Preview table (shown after parse, before save) ── */}
      {parsed && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <h2 className="text-base font-semibold text-slate-800">
              Review Extracted Data
              <span className="ml-2 text-sm font-normal text-slate-500">
                ({parsed.items.length} items —{" "}
                {SUPPLIERS.find((s) => s.code === parsed.supplier)?.label || parsed.supplier})
              </span>
            </h2>
          </div>

          {/* Editable header fields */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
            {[
              { label: "Type",              field: "doc_type"     },
              { label: "Order / Ticket No.", field: "order_number" },
              { label: "Date",              field: "date"         },
              { label: "Job Name",          field: "job_name"     },
            ].map(({ label, field }) => (
              <div key={field}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
                <input
                  type="text"
                  value={parsed[field] || ""}
                  onChange={(e) => setParsed((prev) => ({ ...prev, [field]: e.target.value }))}
                  className="w-full rounded-lg border border-slate-300 px-2 py-1 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-sky-400"
                />
              </div>
            ))}
          </div>

          {/* Items table */}
          <div className="overflow-x-auto rounded-2xl ring-1 ring-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                <tr>
                  <th className="px-3 py-2 text-left w-8">#</th>
                  <th className="px-3 py-2 text-left w-28">Item Number</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-left w-16">Unit</th>
                  <th className="px-3 py-2 text-right w-16">Qty</th>
                  <th className="px-3 py-2 text-right w-24">Unit Price</th>
                  <th className="px-3 py-2 w-8"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {parsed.items.map((item, idx) => (
                  <tr key={item._id ?? idx} className="hover:bg-slate-50">
                    <td className="px-3 py-1 text-slate-400 text-xs">{idx + 1}</td>
                    <td className="px-3 py-1">
                      <input
                        type="text"
                        value={item.item_number || ""}
                        onChange={(e) => updateItem(idx, "item_number", e.target.value)}
                        className={inputCls + " font-mono text-slate-700"}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <input
                        type="text"
                        value={item.description || ""}
                        onChange={(e) => updateItem(idx, "description", e.target.value)}
                        className={inputCls + " min-w-[180px] text-slate-800"}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <input
                        type="text"
                        value={item.uom || ""}
                        onChange={(e) => updateItem(idx, "uom", e.target.value)}
                        className={inputCls + " w-14 text-slate-700"}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <input
                        type="number"
                        value={item.quantity ?? ""}
                        onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))}
                        className={inputCls + " w-16 text-right text-slate-700"}
                      />
                    </td>
                    <td className="px-3 py-1">
                      <input
                        type="number"
                        step="0.0001"
                        value={item.unit_price ?? ""}
                        onChange={(e) => updateItem(idx, "unit_price", parseFloat(e.target.value) || 0)}
                        className={inputCls + " w-20 text-right text-slate-700"}
                      />
                    </td>
                    <td className="px-3 py-1 text-center">
                      <button
                        onClick={() => deleteItem(idx)}
                        className="text-slate-300 hover:text-rose-500 transition leading-none"
                        title="Remove row"
                      >✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Add row */}
          <button
            onClick={addRow}
            className="text-sm text-sky-600 hover:text-sky-800 font-medium transition"
          >
            + Add Row
          </button>

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={confirmSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-5 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 transition"
            >
              {saving && (
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              )}
              {saving ? "Saving…" : "Confirm & Save to Turso"}
            </button>
            <button
              onClick={() => { setParsed(null); setFile(null); setError(""); }}
              className="rounded-xl bg-slate-100 px-5 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Success banner (brief — page reloads immediately after) */}
      {result && (
        <div className="rounded-2xl bg-emerald-50 p-5 ring-1 ring-emerald-200 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">✅</span>
            <p className="text-sm font-semibold text-emerald-800">
              Successfully imported {result.item_count} items
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-emerald-700 sm:grid-cols-4">
            <div><span className="font-medium">Type:</span> {result.doc_type}</div>
            <div><span className="font-medium">Number:</span> {result.order_number}</div>
            <div><span className="font-medium">Date:</span> {result.date}</div>
            <div><span className="font-medium">Job:</span> {result.job_name || "—"}</div>
          </div>
        </div>
      )}

      {/* Import history */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Import History ({invoices.length})
        </h2>

        {invoices.length === 0 ? (
          <div className="rounded-xl bg-white py-10 text-center text-sm text-slate-400 ring-1 ring-slate-200">
            No documents imported yet. Upload your first PDF above.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Type</th>
                  <th className="px-4 py-3 text-left">Number</th>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left">Job</th>
                  <th className="px-4 py-3 text-left">Items</th>
                  <th className="px-4 py-3 text-left">Imported</th>
                  <th className="px-4 py-3 text-left">File</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <span className={classNames(
                        "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                        docTypeBadge(inv.doc_type)
                      )}>
                        {inv.doc_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{inv.order_number}</td>
                    <td className="px-4 py-3 text-slate-600">{inv.date || "—"}</td>
                    <td className="px-4 py-3 text-slate-600">{inv.job_name || "—"}</td>
                    <td className="px-4 py-3 text-slate-600">{inv.item_count}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{inv.imported_at?.slice(0, 10)}</td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-[140px] truncate">{inv.filename || "—"}</td>
                    <td className="px-4 py-3">
                      <form
                        method="POST"
                        action={data.deleteUrl || "/delete_invoice"}
                        onSubmit={(e) => {
                          if (!window.confirm("Delete this import? All items will be removed.")) {
                            e.preventDefault();
                          }
                        }}
                      >
                        <input type="hidden" name="invoice_id" value={inv.id} />
                        <button
                          type="submit"
                          className="rounded px-2 py-1 text-xs text-rose-500 hover:bg-rose-50 hover:text-rose-700 transition"
                        >
                          Delete
                        </button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ================================================================
// LoginPage
// ================================================================
function LoginPage({ data }) {
  return (
    <div className="mx-auto max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">Login</h1>
        <p className="text-sm text-slate-500">Enter your code or email to receive a sign-in link.</p>
      </div>
      <form method="POST" action={data.loginUrl} className="space-y-4">
        <div className="space-y-1">
          <label htmlFor="email" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Email (optional)
          </label>
          <input
            id="email"
            name="email"
            type="email"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            placeholder="name@example.com"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="code" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Access code
          </label>
          <input
            id="code"
            name="code"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            placeholder="Enter code"
          />
        </div>
        <Button type="submit" className="w-full">Log in</Button>
      </form>
    </div>
  );
}

// ── Auto-expanding textarea for long text fields ──────────────────
function AutoTextarea({ value, onChange, className, placeholder, onBlur }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    ref.current.style.height = "auto";
    ref.current.style.height = ref.current.scrollHeight + "px";
  }, [value]);
  return (
    <textarea
      ref={ref}
      value={value}
      onChange={onChange}
      onBlur={onBlur}
      className={className}
      placeholder={placeholder}
      rows={1}
      style={{ resize: "none", overflow: "hidden" }}
    />
  );
}

// ================================================================
// EstimatesPage — list of saved estimates
// ================================================================
function EstimatesPage({ data }) {
  const [estimates, setEstimates] = useState(data.estimates || []);
  const [dupSrc, setDupSrc] = useState(null);
  const [dupName, setDupName] = useState("");

  const handleDelete = (fullName) => {
    if (!window.confirm(`Delete estimate "${fullName}"?`)) return;
    fetch(`/delete_estimate/${encodeURIComponent(fullName)}`, { method: "POST" })
      .then(() => setEstimates((c) => c.filter((e) => e.full_name !== fullName)))
      .catch(() => window.alert("Delete failed."));
  };

  const handleDuplicate = () => {
    if (!dupName.trim()) return;
    const payload = new URLSearchParams({ src_name: dupSrc, dst_name: dupName.trim() });
    fetch("/api/duplicate_estimate", { method: "POST", body: payload })
      .then(() => window.location.reload())
      .catch(() => window.alert("Duplicate failed."));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">Estimates</h1>
        <div className="flex gap-2">
          <Button as="a" href={data.newUrl}>+ New Estimate (Template)</Button>
          <Button as="a" href={data.blankUrl} variant="secondary">+ Blank Estimate</Button>
        </div>
      </div>

      {estimates.length === 0 ? (
        <div className="rounded-2xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
          <p className="text-slate-500">No estimates yet.</p>
          <Button as="a" href={data.newUrl} className="mt-4">Create your first estimate</Button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {estimates.map((est) => (
            <div key={est.id} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-slate-800 text-sm">{est.name}</p>
                  {est.group && <p className="text-xs text-slate-400">{est.group}</p>}
                </div>
                <Badge tone="info">${Number(est.grand_total || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</Badge>
              </div>
              <p className="text-xs text-slate-500">{est.row_count} line item{est.row_count !== 1 ? "s" : ""}</p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Button as="a" href={`/estimate?name=${encodeURIComponent(est.full_name)}`} variant="secondary" className="text-xs px-3 py-1.5">Edit</Button>
                <button
                  onClick={() => { setDupSrc(est.full_name); setDupName(`${est.name} Copy`); }}
                  className="text-xs px-3 py-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 transition"
                >Duplicate</button>
                <button
                  onClick={() => handleDelete(est.full_name)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-rose-200 text-rose-600 hover:bg-rose-50 transition"
                >Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Duplicate modal */}
      {dupSrc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800">Duplicate Estimate</h2>
            <p className="text-sm text-slate-500">New name for the copy of <strong>{dupSrc}</strong>:</p>
            <input
              value={dupName}
              onChange={(e) => setDupName(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              autoFocus
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDupSrc(null)} className="text-sm text-slate-500 hover:text-slate-700">Cancel</button>
              <Button onClick={handleDuplicate} className="text-sm">Duplicate</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ================================================================
// EstimateBuilderPage — create / edit a sectioned estimate
// ================================================================
function EstimateBuilderPage({ data }) {
  const [estimateName, setEstimateName]   = useState(data.estimateName || "");
  const [estimateFolder, setEstimateFolder] = useState("");
  const [projectInfo, setProjectInfo]     = useState(data.content?.project_info || { name: "", address: "", contractor: "", date: "" });
  const [sections, setSections]           = useState(data.content?.sections || []);
  const [saving, setSaving]               = useState(false);
  const [saveOk, setSaveOk]               = useState(false);
  const [pdfLoading, setPdfLoading]       = useState(false);
  const [xlsLoading, setXlsLoading]       = useState(false);
  const [mlModal, setMlModal]             = useState(null);   // { sectionIdx, rowIdx }
  const [catalogSuggestions, setCatalogSuggestions] = useState([]);
  const [activeInput, setActiveInput]     = useState(null);   // { si, ri }

  const exportFormRef = useRef(null);
  const exportDataRef = useRef(null);

  // ── section helpers ──────────────────────────────────────────────
  const addSection = () => {
    setSections((c) => [...c, { id: crypto.randomUUID(), name: "New Section", rows: [] }]);
  };

  const removeSection = (si) => {
    if (!window.confirm("Remove this section and all its rows?")) return;
    setSections((c) => c.filter((_, i) => i !== si));
  };

  const updateSectionName = (si, name) => {
    setSections((c) => c.map((s, i) => i === si ? { ...s, name } : s));
  };

  // ── row helpers ──────────────────────────────────────────────────
  const addRow = (si) => {
    setSections((c) => c.map((s, i) => i !== si ? s : {
      ...s,
      rows: [...s.rows, { id: crypto.randomUUID(), type: "manual", qty: "", description: "", unit_cost: "", total: "", comments: "", add_comments: "" }],
    }));
  };

  const removeRow = (si, ri) => {
    setSections((c) => c.map((s, i) => i !== si ? s : { ...s, rows: s.rows.filter((_, j) => j !== ri) }));
  };

  const updateRow = (si, ri, patch) => {
    setSections((c) => c.map((s, i) => {
      if (i !== si) return s;
      const rows = s.rows.map((r, j) => {
        if (j !== ri) return r;
        const next = { ...r, ...patch };
        const qty = parseFloat(next.qty) || 0;
        const cost = parseFloat(next.unit_cost) || 0;
        if (next.type !== "material_list") {
          next.total = parseFloat((qty * cost).toFixed(2));
        }
        return next;
      });
      return { ...s, rows };
    }));
  };

  // ── catalog autocomplete (debounced fetch as user types) ─────────
  const fetchCatalog = useCallback(
    (() => {
      let timer;
      return (q, si, ri) => {
        clearTimeout(timer);
        if (!q || q.length < 2) { setCatalogSuggestions([]); return; }
        timer = setTimeout(() => {
          fetch(`${data.catalogUrl}?q=${encodeURIComponent(q)}`)
            .then((r) => r.json())
            .then((rows) => { setCatalogSuggestions(rows); setActiveInput({ si, ri }); })
            .catch((err) => console.error("catalog fetch error:", err));
        }, 250);
      };
    })(),
    [data.catalogUrl]
  );

  const applyCatalogItem = (si, ri, item) => {
    updateRow(si, ri, {
      description:  item.description,
      unit_cost:    item.unit_cost,
      comments:     item.comments,
      add_comments: item.add_comments,
    });
    setCatalogSuggestions([]);
    setActiveInput(null);
  };

  // ── link material list ────────────────────────────────────────────
  const linkMaterialList = (mlName) => {
    if (!mlModal) return;
    const { si, ri } = mlModal;
    fetch(`${data.mlTotalUrl}?name=${encodeURIComponent(mlName)}`)
      .then((r) => r.json())
      .then((res) => {
        if (!res.ok) { window.alert("Could not fetch material list total."); return; }
        const total = res.total;
        updateRow(si, ri, {
          type:                "material_list",
          description:         mlName,
          unit_cost:           total,
          total:               total,
          qty:                 1,
          comments:            "See linked material list",
          material_list_name:  mlName,
        });
        setMlModal(null);
      })
      .catch(() => window.alert("Error fetching material list total."));
  };

  // ── computed totals ──────────────────────────────────────────────
  const plumbingTotal = useMemo(
    () => sections.filter((s) => !s.is_gas).reduce((sum, s) => sum + s.rows.reduce((rs, r) => rs + (parseFloat(r.total) || 0), 0), 0),
    [sections]
  );
  const gasTotal = useMemo(
    () => sections.filter((s) => s.is_gas).reduce((sum, s) => sum + s.rows.reduce((rs, r) => rs + (parseFloat(r.total) || 0), 0), 0),
    [sections]
  );
  const grandTotal = plumbingTotal + gasTotal;

  const buildPayload = () => JSON.stringify({
    project_info: projectInfo, sections,
    plumbing_total: parseFloat(plumbingTotal.toFixed(2)),
    gas_total:      parseFloat(gasTotal.toFixed(2)),
    grand_total:    parseFloat(grandTotal.toFixed(2)),
  });

  // ── save ─────────────────────────────────────────────────────────
  const handleSave = () => {
    const folder = estimateFolder.trim();
    const fullName = folder ? `${folder}/${estimateName.trim()}` : estimateName.trim();
    if (!fullName) { window.alert("Estimate name required."); return; }
    setSaving(true); setSaveOk(false);
    const payload = new URLSearchParams({ estimate_name: fullName, estimate_data: buildPayload() });
    fetch(data.saveUrl, { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: payload.toString() })
      .then((r) => r.json())
      .then((res) => { if (res.ok) { setSaveOk(true); setEstimateName(fullName); } else window.alert(res.error || "Save failed."); })
      .catch(() => window.alert("Save failed."))
      .finally(() => setSaving(false));
  };

  // ── export helpers ────────────────────────────────────────────────
  const triggerExport = (action) => {
    const url = action === "pdf" ? data.exportPdfUrl : data.exportXlsUrl;
    if (!exportFormRef.current) return;
    exportFormRef.current.action = url;
    if (exportDataRef.current) exportDataRef.current.value = buildPayload();
    if (action === "pdf") setPdfLoading(true);
    if (action === "xls") setXlsLoading(true);
    setTimeout(() => {
      exportFormRef.current?.submit();
      setTimeout(() => { setPdfLoading(false); setXlsLoading(false); }, 8000);
    }, 100);
  };

  // ── section subtotals ─────────────────────────────────────────────
  const sectionSubtotal = (s) => s.rows.reduce((sum, r) => sum + (parseFloat(r.total) || 0), 0);

  const inputClass = "w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            {estimateName ? `Estimate: ${estimateName}` : "New Estimate"}
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition"
          >
            {saving ? "Saving…" : saveOk ? "✓ Saved" : "Save Estimate"}
          </button>
          <button
            onClick={() => triggerExport("pdf")}
            disabled={pdfLoading}
            className="inline-flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 transition"
          >
            {pdfLoading ? "⏳ Generating…" : "📄 Export PDF"}
          </button>
          <button
            onClick={() => triggerExport("xls")}
            disabled={xlsLoading}
            className="inline-flex items-center gap-1.5 rounded-lg bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
          >
            {xlsLoading ? "⏳ Generating…" : "📊 Export Excel"}
          </button>
        </div>
      </div>

      {/* Hidden export form */}
      <form ref={exportFormRef} method="POST" style={{ display: "none" }}>
        <input ref={exportDataRef} name="estimate_data" />
      </form>

      {/* Project info */}
      <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Estimate Details</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ["Estimate Name", "name", estimateName, setEstimateName, false],
            ["Folder (optional)", "folder", estimateFolder, setEstimateFolder, false],
          ].map(([label, , val, setter]) => (
            <div key={label} className="space-y-1">
              <label className="text-xs text-slate-500">{label}</label>
              <input value={val} onChange={(e) => setter(e.target.value)} className={inputClass} placeholder={label} />
            </div>
          ))}
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Project Name", "name"],
            ["Contractor", "contractor"],
            ["Job Address", "address"],
            ["Date", "date"],
          ].map(([label, field]) => (
            <div key={field} className="space-y-1">
              <label className="text-xs text-slate-500">{label}</label>
              <input
                type={field === "date" ? "date" : "text"}
                value={projectInfo[field] || ""}
                onChange={(e) => setProjectInfo((p) => ({ ...p, [field]: e.target.value }))}
                className={inputClass}
                placeholder={label}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Sections */}
      {sections.map((section, si) => (
        <div key={section.id} className="rounded-2xl bg-white shadow-sm ring-1 ring-slate-200 overflow-hidden">
          {/* Section header */}
          <div className={classNames("flex items-center gap-3 px-5 py-3", section.is_gas ? "bg-emerald-900" : "bg-slate-800")}>
            <input
              value={section.name}
              onChange={(e) => updateSectionName(si, e.target.value)}
              className="flex-1 bg-transparent text-white font-semibold text-sm focus:outline-none placeholder-slate-400"
              placeholder="Section name"
            />
            <span className="text-slate-300 text-sm font-medium">
              ${sectionSubtotal(section).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <button
              onClick={() => removeSection(si)}
              className="text-slate-400 hover:text-rose-400 text-lg leading-none transition"
              title="Remove section"
            >×</button>
          </div>

          {/* Rows table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-20">QTY</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-64">DESCRIPTION</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-32">UNIT COST</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-32">TOTAL</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-44">COMMENTS</th>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-slate-500 w-44">ADD. COMMENTS</th>
                  <th className="px-3 py-2 w-20"></th>
                </tr>
              </thead>
              <tbody>
                {section.rows.map((row, ri) => (
                  <tr key={row.id} className={ri % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                    {/* QTY */}
                    <td className="px-3 py-1.5">
                      {row.type === "material_list" ? (
                        <span className="text-xs text-slate-400">1</span>
                      ) : (
                        <input
                          type="number" min="0" step="1"
                          value={row.qty}
                          onChange={(e) => updateRow(si, ri, { qty: e.target.value })}
                          className={inputClass}
                        />
                      )}
                    </td>

                    {/* DESCRIPTION with autocomplete */}
                    <td className="px-3 py-1.5 relative">
                      {row.type === "material_list" ? (
                        <div className="flex items-center gap-1">
                          <span className="inline-block bg-sky-100 text-sky-700 text-xs font-semibold rounded px-1.5 py-0.5">ML</span>
                          <span className="text-sm text-slate-700">{row.description}</span>
                        </div>
                      ) : (
                        <>
                          <AutoTextarea
                            value={row.description}
                            onChange={(e) => {
                              updateRow(si, ri, { description: e.target.value });
                              fetchCatalog(e.target.value, si, ri);
                            }}
                            onBlur={() => setTimeout(() => setCatalogSuggestions([]), 200)}
                            className={inputClass}
                            placeholder="Description…"
                          />
                          {catalogSuggestions.length > 0 && activeInput?.si === si && activeInput?.ri === ri && (
                            <div className="absolute z-30 top-full left-0 mt-1 bg-white rounded-xl shadow-2xl ring-1 ring-slate-200" style={{ minWidth: "420px" }}>
                              <div className="flex items-center justify-between px-3 py-2 border-b border-slate-100 bg-slate-50 rounded-t-xl sticky top-0">
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                                  {catalogSuggestions.length} suggestion{catalogSuggestions.length !== 1 ? "s" : ""}
                                </span>
                                <button onMouseDown={() => setCatalogSuggestions([])} className="text-slate-400 hover:text-slate-600 text-base leading-none">×</button>
                              </div>
                              {(() => {
                                const groups = {};
                                catalogSuggestions.forEach((item) => {
                                  const cat = item.category || "Other";
                                  if (!groups[cat]) groups[cat] = [];
                                  groups[cat].push(item);
                                });
                                return Object.entries(groups).map(([cat, items]) => (
                                  <div key={cat}>
                                    <div className="px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-white bg-slate-700 sticky top-8">{cat}</div>
                                    {items.map((item) => (
                                      <button
                                        key={item.id}
                                        onMouseDown={() => applyCatalogItem(si, ri, item)}
                                        className="w-full text-left px-3 py-2 text-xs hover:bg-sky-50 border-b border-slate-100 last:border-0 transition"
                                      >
                                        <div className="font-medium text-slate-800 leading-snug">{item.description}</div>
                                        <div className="flex flex-wrap gap-x-3 mt-0.5">
                                          <span className="text-emerald-600 font-semibold">${Number(item.unit_cost || 0).toLocaleString()}</span>
                                          {item.used_in && <span className="text-sky-600">Used in: {item.used_in}</span>}
                                        </div>
                                      </button>
                                    ))}
                                  </div>
                                ));
                              })()}
                            </div>
                          )}
                        </>
                      )}
                    </td>

                    {/* UNIT COST */}
                    <td className="px-3 py-1.5">
                      {row.type === "material_list" ? (
                        <span className="text-sm text-slate-700">${Number(row.unit_cost || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                      ) : (
                        <input
                          type="number" min="0" step="0.01"
                          value={row.unit_cost}
                          onChange={(e) => updateRow(si, ri, { unit_cost: e.target.value })}
                          className={inputClass}
                        />
                      )}
                    </td>

                    {/* TOTAL (auto) */}
                    <td className="px-3 py-1.5 text-sm font-medium text-slate-700">
                      ${Number(row.total || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>

                    {/* COMMENTS */}
                    <td className="px-3 py-1.5">
                      <AutoTextarea
                        value={row.comments}
                        onChange={(e) => updateRow(si, ri, { comments: e.target.value })}
                        className={inputClass}
                        placeholder="Comments…"
                      />
                    </td>

                    {/* ADD. COMMENTS */}
                    <td className="px-3 py-1.5">
                      <AutoTextarea
                        value={row.add_comments}
                        onChange={(e) => updateRow(si, ri, { add_comments: e.target.value })}
                        className={inputClass}
                        placeholder="Additional…"
                      />
                    </td>

                    {/* ACTIONS */}
                    <td className="px-3 py-1.5">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setMlModal({ si, ri })}
                          title="Link Material List"
                          className="text-sky-500 hover:text-sky-700 text-xs font-semibold px-1.5 py-1 rounded hover:bg-sky-50 transition"
                        >ML</button>
                        <button
                          onClick={() => removeRow(si, ri)}
                          className="text-slate-400 hover:text-rose-500 text-lg leading-none transition"
                          title="Remove row"
                        >×</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Section footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100">
            <button
              onClick={() => addRow(si)}
              className="text-sm text-sky-600 font-semibold hover:text-sky-800 transition"
            >+ Add Row</button>
            <span className="text-xs text-slate-400">
              Subtotal: <span className="font-semibold text-slate-700">${sectionSubtotal(section).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </span>
          </div>
        </div>
      ))}

      {/* Plumbing Project Total banner (after last non-gas section) */}
      {sections.some((s) => !s.is_gas) && (
        <div className="rounded-2xl bg-slate-800 px-6 py-4 text-white shadow flex items-center justify-between">
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-300">Plumbing Project Total</p>
          <p className="text-2xl font-bold">${plumbingTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
        </div>
      )}

      {/* Add section + Gas Total */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <button
          onClick={addSection}
          className="inline-flex items-center gap-1.5 rounded-lg border-2 border-dashed border-slate-300 px-5 py-3 text-sm font-semibold text-slate-500 hover:border-sky-400 hover:text-sky-600 transition"
        >+ Add Section</button>
        {sections.some((s) => s.is_gas) && (
          <div className="rounded-2xl bg-emerald-900 px-6 py-4 text-white shadow">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-300">Gas System Total</p>
            <p className="text-2xl font-bold">${gasTotal.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </div>
        )}
      </div>

      {/* Material List link modal */}
      {mlModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm space-y-4">
            <h2 className="text-base font-semibold text-slate-800">Link a Material List</h2>
            <p className="text-sm text-slate-500">
              Select a saved material list. Its grand total (with tax) will be used as the row cost.
            </p>
            <div className="max-h-60 overflow-y-auto space-y-1 rounded-lg border border-slate-200 p-2">
              {(data.mlNames || []).length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-4">No material lists saved yet.</p>
              ) : (
                (data.mlNames || []).map((name) => (
                  <button
                    key={name}
                    onClick={() => linkMaterialList(name)}
                    className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-sky-50 hover:text-sky-700 transition"
                  >{name}</button>
                ))
              )}
            </div>
            <div className="flex justify-end">
              <button onClick={() => setMlModal(null)} className="text-sm text-slate-500 hover:text-slate-700">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ================================================================
// App shell
// ================================================================
const pageComponentMap = {
  home: HomePage,
  view_all: ViewAllPage,
  search: SearchPage,
  analyze: AnalyzePage,
  product_detail: ProductDetailPage,
  material_list: MaterialListPage,
  templates: TemplatesPage,
  estimates: EstimatesPage,
  estimate_builder: EstimateBuilderPage,
  upload_pdf: UploadPdfPage,
  login: LoginPage,
};

function AppShell({ page, data, navLinks, userEmail, logoutUrl }) {
  const Component = pageComponentMap[page] || HomePage;
  return (
    <Layout page={page} navLinks={navLinks} userEmail={userEmail} logoutUrl={logoutUrl}>
      <Component data={data} />
    </Layout>
  );
}

const rootElement = document.getElementById("root");
const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <FlashMessages initial={window.__FLASH_MESSAGES__ || []} />
    <AppShell
      page={window.__INITIAL_PAGE__}
      data={window.__INITIAL_DATA__ || {}}
      navLinks={window.__NAV_LINKS__ || []}
      userEmail={window.__USER_EMAIL__ || ""}
      logoutUrl={window.__LOGOUT_URL__ || "/logout"}
    />
  </React.StrictMode>
);
