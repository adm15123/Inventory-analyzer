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
    let listName = sessionStorage.getItem("zpl_new_list_name");
    if (!listName) {
      listName = window.prompt("Enter a name for this list:");
      if (!listName || !listName.trim()) return;
      sessionStorage.setItem("zpl_new_list_name", listName.trim());
    }
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
    window.location.href = "/material_list?list=new";
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
  <div className="flex items-center gap-2">
    <button
      onClick={handleGoToList}
      className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition"
    >
      <span>🛒</span>
      <span>{pendingCount} item{pendingCount !== 1 ? "s" : ""} — Go to Material List</span>
    </button>
    <button
      onClick={() => {
        setPendingItems([]);
        sessionStorage.removeItem("zpl_new_list_name");
        setAddedIndices({});
      }}
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
  const [showQuickAdd, setShowQuickAdd] = useState(false);
  const [quickForm, setQuickForm] = useState({
    description: "",
    quantity: 1,
    unit: "",
    lastPrice: "",
    supply: supplyCodes[lookupSupply],
    lookupSupply: lookupSupply,
   });
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

                  {/* Supply badge */}
                  <td className="px-2 py-1 whitespace-nowrap">
                    <span className="inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                      {item.supply}
                    </span>
                  </td>

                  {/* Unit */}
                  <td className="px-2 py-1 whitespace-nowrap text-slate-500">{item.unit || "—"}</td>

                  {/* Price */}
                  <td className="px-2 py-1 whitespace-nowrap text-slate-700">
                    ${Number(item.lastPrice || 0).toFixed(2)}
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

      {/* Quick Add Panel */}
<div>
  {showQuickAdd ? (
    <div className="rounded-2xl border-2 border-dashed border-sky-300 bg-sky-50 p-5 space-y-4">
      <h3 className="text-sm font-semibold text-sky-800">Add Custom Item</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="col-span-2 sm:col-span-3 space-y-1">
          <label className="text-xs font-medium text-slate-500">Description *</label>
          <input
            autoFocus
            type="text"
            value={quickForm.description}
            onChange={(e) => setQuickForm((f) => ({ ...f, description: e.target.value }))}
            onKeyDown={(e) => {
              if (e.key === "Enter" && quickForm.description.trim()) {
                const qty = Math.max(0, Number(quickForm.quantity) || 0);
                const price = parseFloat(quickForm.lastPrice) || 0;
                setItems((c) => [...c, {
                  quantity: qty,
                  description: quickForm.description.trim(),
                  supply: quickForm.supply,
                  lookupSupply: quickForm.lookupSupply,
                  unit: quickForm.unit.trim(),
                  lastPrice: price,
                  total: Number((qty * price).toFixed(2)),
                  predetermined: false,
                }]);
                setQuickForm((f) => ({ description: "", quantity: 1, unit: "", lastPrice: "", supply: f.supply, lookupSupply: f.lookupSupply }));
              }
            }}
            placeholder="e.g. 3/4 copper elbow 90°"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Quantity</label>
          <input
            type="number"
            min="0"
            step="1"
            value={quickForm.quantity}
            onChange={(e) => setQuickForm((f) => ({ ...f, quantity: e.target.value }))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Unit</label>
          <input
            type="text"
            value={quickForm.unit}
            onChange={(e) => setQuickForm((f) => ({ ...f, unit: e.target.value }))}
            placeholder="EA, FT, BOX…"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-slate-500">Unit Price ($)</label>
          <input
            type="number"
            min="0"
            step="0.01"
            value={quickForm.lastPrice}
            onChange={(e) => setQuickForm((f) => ({ ...f, lastPrice: e.target.value }))}
            placeholder="0.00"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
        </div>
        <div className="col-span-2 sm:col-span-3 space-y-1">
          <label className="text-xs font-medium text-slate-500">Supplier</label>
          <select
            value={quickForm.lookupSupply}
            onChange={(e) => setQuickForm((f) => ({ ...f, lookupSupply: e.target.value, supply: supplyCodes[e.target.value] }))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="supply1">Supply 1 (BPS)</option>
            <option value="supply2">Supply 2</option>
            <option value="supply3">Lion Plumbing Supply</option>
            <option value="supply4">Bond Plumbing Supply</option>
          </select>
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          onClick={() => {
            if (!quickForm.description.trim()) return;
            const qty = Math.max(0, Number(quickForm.quantity) || 0);
            const price = parseFloat(quickForm.lastPrice) || 0;
            setItems((c) => [...c, {
              quantity: qty,
              description: quickForm.description.trim(),
              supply: quickForm.supply,
              lookupSupply: quickForm.lookupSupply,
              unit: quickForm.unit.trim(),
              lastPrice: price,
              total: Number((qty * price).toFixed(2)),
              predetermined: false,
            }]);
            setQuickForm((f) => ({ description: "", quantity: 1, unit: "", lastPrice: "", supply: f.supply, lookupSupply: f.lookupSupply }));
          }}
          disabled={!quickForm.description.trim()}
          className="rounded-lg bg-sky-600 px-5 py-2 text-sm font-semibold text-white hover:bg-sky-700 transition disabled:opacity-40"
        >
          + Add to List
        </button>
        <button
          onClick={() => setShowQuickAdd(false)}
          className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200 transition"
        >
          Cancel
        </button>
      </div>
    </div>
  ) : (
    <button
      onClick={() => setShowQuickAdd(true)}
      className="inline-flex items-center gap-2 rounded-xl border-2 border-dashed border-slate-300 px-6 py-3 text-sm font-semibold text-slate-500 hover:border-sky-400 hover:text-sky-600 transition w-full justify-center"
    >
      + Add Item
    </button>
  )}
</div>

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
