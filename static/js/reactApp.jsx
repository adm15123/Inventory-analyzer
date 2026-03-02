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
// SearchPage — IMPROVEMENT #3: debounce + IMPROVEMENT #7: Add to List
// ================================================================
function SearchPage({ data }) {
  const [supply, setSupply] = useState(data.supply || "supply1");
  const [query, setQuery] = useState(data.query || "");
  const [columns, setColumns] = useState(data.columns || []);
  const [rows, setRows] = useState(data.rows || []);
  const [loading, setLoading] = useState(false);
  const [addedIndices, setAddedIndices] = useState({});
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

  // IMPROVEMENT #3: debounce 300 ms
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

  // IMPROVEMENT #7: add item to pending cart then redirect
  const handleAddToList = (row, index) => {
    const pending = getPendingItems();
    pending.push({
      description: row.Description || row.description || "",
      supply: supplyCodes[supply] || supply,
      lookupSupply: supply,
      unit: row.Unit || row.unit || "",
      lastPrice: parseFloat(row["Price per Unit"] || 0),
      quantity: 1,
    });
    setPendingItems(pending);
    setAddedIndices((prev) => ({ ...prev, [index]: true }));
  };

  const handleGoToList = () => {
    window.location.href = "/material_list";
  };

  const pendingCount = getPendingItems().length;

  return (
    <div className="space-y-6">
      <div className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Search Description</h1>
            <p className="text-sm text-slate-500">Results update as you type (300 ms debounce).</p>
          </div>
          {/* IMPROVEMENT #7: cart indicator */}
          {pendingCount > 0 && (
            <button
              onClick={handleGoToList}
              className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition"
            >
              <span>🛒</span>
              <span>{pendingCount} item{pendingCount !== 1 ? "s" : ""} — Go to Material List</span>
            </button>
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

      {loading ? (
        <SkeletonRows cols={(columns.length || 4) + 2} rows={6} />
      ) : (
        <Table
          columns={[...columns, { key: "addToList", label: "Add to List" }, { key: "history", label: "History" }]}
          rows={rows}
          renderRow={(row, index) => (
            <>
              {columns.map((column) => (
                <td key={`${column}-${index}`} className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {row[column] ?? ""}
                </td>
              ))}
              {/* IMPROVEMENT #7: Add to List button */}
              <td className="px-4 py-3 text-sm">
                <button
                  onClick={() => handleAddToList(row, index)}
                  disabled={!!addedIndices[index]}
                  className={classNames(
                    "rounded-lg px-3 py-1 text-xs font-semibold transition",
                    addedIndices[index]
                      ? "bg-emerald-100 text-emerald-700 cursor-default"
                      : "bg-sky-600 text-white hover:bg-sky-700"
                  )}
                >
                  {addedIndices[index] ? "✓ Added" : "+ Add"}
                </button>
              </td>
              <td className="px-4 py-3 text-sm">
                {row.graphUrl ? (
                  <Button as="a" href={row.graphUrl} variant="secondary" className="px-3 py-1 text-xs">
                    History
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
function MaterialListPage({ data }) {
  const catalogLookups = useMemo(() => {
    const lookups = {};
    Object.entries(data.catalog || {}).forEach(([key, records]) => {
      const map = {};
      (records || []).forEach((item) => {
        const description = (item.Description || item["Product Description"] || item.description || "")
          .toLowerCase().trim();
        if (!description) return;
        const price = parseFloat(item["Price per Unit"] ?? item.price ?? item.last_price ?? 0) || 0;
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

  const [lookupSupply, setLookupSupply] = useState("supply1");
  const [templateFolder, setTemplateFolder] = useState(data.templateFolder || "");
  const [templateName, setTemplateName] = useState(data.templateName || "");
  const [pdfLoading, setPdfLoading] = useState(false); // IMPROVEMENT #6

  // IMPROVEMENT #7: absorb pending cart items on mount
  const [items, setItems] = useState(() => {
    const baseItems = (data.products || []).map((product) => ({
      quantity: Number(product.quantity ?? product.Quantity ?? 0) || 0,
      description: product["Product Description"] || product.description || "",
      supply: product.Supply || product.supply || supplyCodes[lookupSupply],
      lookupSupply: getSupplyKeyFromCode(product.Supply || product.supply) || lookupSupply,
      unit: product.Unit || product.unit || "",
      lastPrice: Number(product["Last Price"] ?? product.last_price ?? product["Price per Unit"] ?? 0) || 0,
      predetermined: false,
    }));

    // Merge pending cart items from Search
    const pending = getPendingItems();
    if (pending.length) {
      setPendingItems([]); // clear after consuming
      return [...baseItems, ...pending];
    }
    return baseItems;
  });

  const [draggingIndex, setDraggingIndex] = useState(null);
  const formRef = useRef(null);
  const productDataRef = useRef(null);
  const includePriceRef = useRef(null);

  const updateItem = (index, patch) => {
    setItems((current) =>
      current.map((item, i) => (i === index ? { ...item, ...patch } : item))
    );
  };

  const applySupplyPrices = useCallback(() => {
    setItems((current) =>
      current.map((item) => {
        const itemLookupSupply = item.lookupSupply || lookupSupply;
        const lookup = catalogLookups[itemLookupSupply] || {};
        const normalized = item.description.toLowerCase().trim();
        const entry = lookup[normalized];
        if (!entry) return { ...item, lookupSupply: itemLookupSupply, supply: supplyCodes[itemLookupSupply] };
        return {
          ...item,
          lookupSupply: itemLookupSupply,
          supply: supplyCodes[itemLookupSupply],
          unit: entry.unit || item.unit,
          lastPrice: Number(entry.price.toFixed(2)),
          total: Number(((Number(item.quantity) || 0) * entry.price).toFixed(2)),
        };
      })
    );
  }, [catalogLookups, lookupSupply]);

  const handleSupplyChange = (index, value) => {
    const supplyKey = getSupplyKeyFromCode(value) || lookupSupply;
    updateItem(index, { supply: value, lookupSupply: supplyKey });
  };

  // IMPROVEMENT #8: qty validated as integer >= 0
  const handleQuantityChange = (index, rawValue) => {
    if (rawValue === "") { updateItem(index, { quantity: "" }); return; }
    const normalized = Math.max(0, Math.round(Number(rawValue)));
    updateItem(index, { quantity: Number.isFinite(normalized) ? normalized : 0 });
  };

  const handleDescriptionChange = (index, value) => {
    updateItem(index, { description: value });
  };

  const addManualItem = () => {
    setItems((current) => [
      ...current,
      { quantity: 0, description: "", supply: supplyCodes[lookupSupply], lookupSupply, unit: "", lastPrice: 0, predetermined: false },
    ]);
  };

  const removeItem = (index) => {
    setItems((current) => current.filter((_, i) => i !== index));
  };

  const moveItem = (index, direction) => {
    setItems((current) => {
      const next = [...current];
      const target = index + direction;
      if (target < 0 || target >= next.length) return next;
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return next;
    });
  };

  const handleDragStart = (event, index) => {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", String(index));
    setDraggingIndex(index);
  };

  const handleDragOver = (event, index) => {
    event.preventDefault();
    if (draggingIndex === null || draggingIndex === index) return;
    setItems((current) => {
      const next = [...current];
      const [moved] = next.splice(draggingIndex, 1);
      next.splice(index, 0, moved);
      return next;
    });
    setDraggingIndex(index);
  };

  const handleDrop = (event) => { event.preventDefault(); setDraggingIndex(null); };
  const handleDragEnd = () => setDraggingIndex(null);

  const grandTotal = useMemo(
    () => items.reduce((sum, item) => sum + Number(item.total || (item.quantity || 0) * (item.lastPrice || 0)), 0),
    [items]
  );

  const serializeProducts = () =>
    items.map((item) => ({
      description: item.description,
      supply: item.supply,
      unit: item.unit,
      last_price: Number(item.lastPrice || 0),
      quantity: Number(item.quantity || 0),
      total: Number(((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)),
    }));

  // IMPROVEMENT #6: show loading state during PDF generation
  const handleExport = () => {
    const includePrice = window.confirm("Include prices in the PDF?");
    if (includePriceRef.current) includePriceRef.current.value = includePrice ? "yes" : "no";
    if (productDataRef.current) productDataRef.current.value = JSON.stringify(serializeProducts());
    setPdfLoading(true);
    // Give the UI a tick to show loading, then submit
    setTimeout(() => {
      formRef.current?.submit();
      // Reset after a reasonable delay (server-side redirect will handle it)
      setTimeout(() => setPdfLoading(false), 8000);
    }, 100);
  };

  const handleSaveTemplate = () => {
    if (!templateName.trim()) { window.alert("Template name required"); return; }
    const folder = templateFolder.trim();
    const fullName = folder ? `${folder}/${templateName.trim()}` : templateName.trim();
    const payload = {
      template_name: fullName,
      product_data: JSON.stringify(serializeProducts()),
    };
    fetch(data.saveTemplateUrl || "/save_template", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(payload).toString(),
    }).then((r) => {
      if (r.ok) window.alert("Template saved!");
      else window.alert("Error saving template.");
    });
  };

  // IMPROVEMENT #11: detect mobile to show cards
  const [isMobile, setIsMobile] = useState(window.innerWidth < 640);
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 640);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Material List</h1>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supplier</label>
          <select
            value={lookupSupply}
            onChange={(e) => setLookupSupply(e.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            {Object.entries(supplyLabels).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <Button type="button" variant="secondary" className="text-xs py-1.5 px-3" onClick={applySupplyPrices}>
            Apply Prices
          </Button>
        </div>
      </div>

      {/* IMPROVEMENT #11: Mobile card view vs desktop table */}
      {isMobile ? (
        <div className="space-y-3">
          {items.length === 0 && (
            <EmptyState title="No items yet" description="Add items or load a template below." />
          )}
          {items.map((item, index) => (
            <div
              key={index}
              className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 space-y-3"
            >
              <div className="flex items-center gap-2">
                {/* IMPROVEMENT #8: min=0 step=1 */}
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={item.quantity === "" ? "" : item.quantity}
                  onChange={(e) => handleQuantityChange(index, e.target.value)}
                  className="w-16 rounded-lg border border-slate-300 px-2 py-1 text-sm text-center"
                  placeholder="Qty"
                />
                <input
                  type="text"
                  value={item.description}
                  onChange={(e) => handleDescriptionChange(index, e.target.value)}
                  className="flex-1 rounded-lg border border-slate-300 px-2 py-1 text-sm"
                  placeholder="Description"
                />
                <button onClick={() => removeItem(index)} className="text-rose-500 font-bold text-lg leading-none px-1">×</button>
              </div>
              <div className="flex gap-2 text-xs text-slate-500 justify-between">
                <span>Supply: <strong>{item.supply}</strong></span>
                <span>Unit: <strong>{item.unit || "—"}</strong></span>
                <span>Price: <strong>${Number(item.lastPrice || 0).toFixed(2)}</strong></span>
                <span>Total: <strong>${((item.quantity || 0) * (item.lastPrice || 0)).toFixed(2)}</strong></span>
              </div>
            </div>
          ))}
          <div className="rounded-xl bg-slate-50 px-4 py-2 text-right text-sm font-semibold text-slate-900">
            Grand Total: ${grandTotal.toFixed(2)}
          </div>
        </div>
      ) : (
        /* Desktop table */
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {["Qty", "Description", "Supply", "Unit", "Price", "Total", "Actions"].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
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
                      draggingIndex === index ? "opacity-40" : "hover:bg-slate-50"
                    )}
                    style={{ cursor: "grab" }}
                  >
                    <td className="px-2 py-1">
                      {/* IMPROVEMENT #8: min=0 step=1 */}
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={item.quantity === "" ? "" : item.quantity}
                        onChange={(e) => handleQuantityChange(index, e.target.value)}
                        className="w-16 rounded border border-slate-300 px-1 py-0.5 text-center text-sm"
                      />
                    </td>
                    <td className="px-2 py-1 min-w-[200px]">
                      <input
                        type="text"
                        value={item.description}
                        onChange={(e) => handleDescriptionChange(index, e.target.value)}
                        className="w-full rounded border border-slate-300 px-1 py-0.5 text-sm"
                      />
                    </td>
                    <td className="px-2 py-1 whitespace-nowrap text-slate-600">{item.supply}</td>
                    <td className="px-2 py-1 whitespace-nowrap text-slate-600">{item.unit || "—"}</td>
                    <td className="px-2 py-1 whitespace-nowrap text-slate-600">${Number(item.lastPrice || 0).toFixed(2)}</td>
                    <td className="px-2 py-1 whitespace-nowrap font-medium text-slate-800">
                      ${((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)}
                    </td>
                    <td className="px-2 py-1">
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          className="rounded-full bg-slate-200 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-300 transition"
                          onClick={() => moveItem(index, -1)}
                          aria-label="Move up"
                        >↑</button>
                        <button
                          type="button"
                          className="rounded-full bg-slate-200 px-1.5 py-0.5 text-[11px] font-semibold text-slate-600 hover:bg-slate-300 transition"
                          onClick={() => moveItem(index, 1)}
                          aria-label="Move down"
                        >↓</button>
                        <button
                          type="button"
                          className="rounded-full bg-rose-500 px-1.5 py-0.5 text-[11px] font-semibold text-white hover:bg-rose-600 transition"
                          onClick={() => removeItem(index)}
                          aria-label="Remove"
                        >×</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-slate-50 text-xs">
                <tr>
                  <td colSpan={5} className="px-3 py-2 text-right font-semibold text-slate-700">Grand Total</td>
                  <td className="px-3 py-2 font-semibold text-slate-900">${grandTotal.toFixed(2)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={addManualItem} variant="secondary">
          + Add Item
        </Button>
        {/* IMPROVEMENT #6: loading state on PDF export */}
        <Button type="button" onClick={handleExport} disabled={pdfLoading}>
          {pdfLoading ? "⏳ Generating PDF…" : "Export to PDF"}
        </Button>
        <Button as="a" href={data.downloadUrl} variant="ghost">
          Download Last PDF
        </Button>
      </div>

      {/* Save template section */}
      <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 space-y-3">
        <h2 className="text-sm font-semibold text-slate-800">Save as Template</h2>
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            value={templateFolder}
            onChange={(e) => setTemplateFolder(e.target.value)}
            placeholder="Folder (optional)"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
          <input
            type="text"
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
            placeholder="Template name"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
          <Button type="button" variant="success" onClick={handleSaveTemplate}>
            Save Template
          </Button>
        </div>
      </div>

      {/* Hidden form for PDF POST */}
      <form ref={formRef} method="POST" action={data.materialListUrl || "/material_list"} className="hidden">
        <input name="contractor" defaultValue={data.contractor || ""} />
        <input name="address" defaultValue={data.address || ""} />
        <input name="date" defaultValue={data.orderDate || ""} />
        <input ref={productDataRef} name="product_data" defaultValue="" />
        <input ref={includePriceRef} name="include_price" defaultValue="yes" />
      </form>
    </div>
  );
}

// ================================================================
// TemplatesPage
// ================================================================
function TemplatesPage({ data }) {
  const entries = data.entries || [];
  const [filterQuery, setFilterQuery] = useState("");
  const [expandedFolders, setExpandedFolders] = useState(() => {
    const grouped = {};
    entries.forEach((e) => { const k = e.group || "__root__"; grouped[k] = true; });
    return grouped;
  });

  const grouped = useMemo(() => {
    const filtered = filterQuery
      ? entries.filter((e) => e.full_name?.toLowerCase().includes(filterQuery.toLowerCase()))
      : entries;
    const result = {};
    filtered.forEach((e) => {
      const key = e.group || "";
      if (!result[key]) result[key] = [];
      result[key].push(e);
    });
    return result;
  }, [entries, filterQuery]);

  const toggleFolder = (folder) => {
    const key = folder || "__root__";
    setExpandedFolders((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleAction = (url, body) => {
    const payload = new URLSearchParams(body || {});
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: payload.toString(),
    }).then(() => window.location.reload());
  };

  const confirmAndDelete = (entry) => {
    if (window.confirm(`Delete template "${entry.full_name}"?`)) handleAction(entry.delete_url);
  };

  const promptRename = (entry) => {
    const next = window.prompt("New template name", entry.full_name);
    if (next) handleAction(entry.rename_url, { new_name: next });
  };

  const promptMove = (entry) => {
    const target = window.prompt("Move to folder (leave blank for root)", entry.group || "");
    if (target !== null) handleAction(entry.move_url, { target_folder: target });
  };

  const renderTableRows = (rows) => (
    <Table
      columns={["Name", "Modified", "Total w/ Tax", "Actions"]}
      rows={rows}
      renderRow={(row) => (
        <>
          <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">{row.full_name}</td>
          <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-500">
            {row.mtime ? new Date(row.mtime * 1000).toLocaleString() : "—"}
          </td>
          <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">
            ${row.total_with_tax?.toFixed?.(2) ?? "—"}
          </td>
          <td className="px-4 py-3 text-sm">
            <div className="flex flex-wrap gap-1">
              {row.load_url && (
                <Button as="a" href={row.load_url} className="px-2 py-0.5 text-xs">Load</Button>
              )}
              <Button variant="secondary" className="px-2 py-0.5 text-xs" onClick={() => promptRename(row)}>Rename</Button>
              <Button variant="ghost" className="px-2 py-0.5 text-xs" onClick={() => promptMove(row)}>Move</Button>
              <Button variant="danger" className="px-2 py-0.5 text-xs" onClick={() => confirmAndDelete(row)}>Delete</Button>
            </div>
          </td>
        </>
      )}
    />
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Templates</h1>
          <p className="mt-1 text-sm text-slate-500">{entries.length} saved template{entries.length !== 1 ? "s" : ""}</p>
        </div>
        <input
          type="text"
          value={filterQuery}
          onChange={(e) => setFilterQuery(e.target.value)}
          placeholder="Filter templates…"
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200 w-full sm:w-60"
        />
      </div>

      {Object.keys(grouped).length === 0 ? (
        <EmptyState title="No templates" description="Save a template from the Material List page." />
      ) : Object.entries(grouped).map(([folder, folderEntries]) => {
        const key = folder || "__root__";
        const isExpanded = expandedFolders[key] ?? true;
        return (
          <div key={key} className="space-y-2">
            <button
              type="button"
              onClick={() => toggleFolder(folder)}
              className="flex w-full items-center justify-between rounded-lg bg-slate-100 px-4 py-2 text-left text-sm font-semibold text-slate-700 hover:bg-slate-200 transition"
            >
              <span className="flex items-center gap-2">
                <span>{folder || "Ungrouped"}</span>
                <span className="text-xs font-medium text-slate-500">({folderEntries.length})</span>
              </span>
              <span className={classNames("text-slate-500 transition-transform", isExpanded ? "rotate-180" : "rotate-0")}>⌃</span>
            </button>
            {isExpanded && renderTableRows(folderEntries)}
          </div>
        );
      })}
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
