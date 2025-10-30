const { useEffect, useMemo, useRef, useState } = React;

const variantStyles = {
  primary: "bg-sky-600 hover:bg-sky-700 text-white",
  secondary: "bg-slate-700 hover:bg-slate-800 text-white",
  ghost: "text-slate-600 hover:text-slate-900",
  danger: "bg-rose-600 hover:bg-rose-700 text-white",
};

const supplyCodes = {
  supply1: "BPS",
  supply2: "S2",
  supply3: "LPS",
  supply4: "BOND",
};

function classNames(...classes) {
  return classes.filter(Boolean).join(" ");
}

function Button({ variant = "primary", className = "", as = "button", href, children, ...props }) {
  const Component = as === "a" ? "a" : "button";
  const base = variantStyles[variant] || variantStyles.primary;
  const shared = classNames(
    "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
    base,
    className
  );
  if (Component === "a") {
    return (
      <a className={shared} href={href} {...props}>
        {children}
      </a>
    );
  }
  return (
    <button className={shared} {...props}>
      {children}
    </button>
  );
}

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

function FlashMessages({ initial }) {
  const [messages, setMessages] = useState(initial || []);
  if (!messages || !messages.length) {
    return null;
  }
  const toneMap = {
    success: "success",
    danger: "danger",
    warning: "info",
    info: "info",
  };
  return (
    <div className="fixed top-4 right-4 z-50 space-y-3">
      {messages.map(([category, text], index) => (
        <div
          key={`${category}-${index}`}
          className="flex items-start gap-3 rounded-xl bg-white p-4 shadow-xl ring-1 ring-slate-200"
        >
          <div className="flex-1 text-sm text-slate-700">
            <Badge tone={toneMap[category] || "info"}>{category.toUpperCase()}</Badge>
            <p className="mt-1 leading-relaxed">{text}</p>
          </div>
          <button
            type="button"
            className="text-slate-400 transition hover:text-slate-600"
            aria-label="Dismiss notification"
            onClick={() => setMessages((current) => current.filter((_, idx) => idx !== index))}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}

function Layout({ page, navLinks, userEmail, logoutUrl, children }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4">
          <a href="/" className="text-lg font-semibold tracking-tight">
            Inventory Analyzer
          </a>
          <button
            className="rounded-md p-2 text-slate-200 transition hover:bg-slate-800 md:hidden"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Toggle navigation"
          >
            ☰
          </button>
          <nav className="hidden items-center gap-4 md:flex">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className={classNames(
                  "rounded-lg px-3 py-2 text-sm font-medium transition",
                  page === link.page
                    ? "bg-slate-100 text-slate-900"
                    : "text-slate-200 hover:bg-slate-800"
                )}
              >
                {link.label}
              </a>
            ))}
          </nav>
          <div className="hidden items-center gap-3 md:flex">
            {userEmail ? (
              <>
                <span className="text-sm text-slate-200">{userEmail}</span>
                <Button as="a" href={logoutUrl} variant="ghost" className="px-3 py-1 text-xs">
                  Logout
                </Button>
              </>
            ) : (
              <Button as="a" href={logoutUrl} variant="ghost" className="px-3 py-1 text-xs">
                Login
              </Button>
            )}
          </div>
        </div>
        {menuOpen && (
          <div className="border-t border-slate-800 px-4 pb-4 pt-2 md:hidden">
            <div className="flex flex-col gap-2">
              {navLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className={classNames(
                    "rounded-lg px-3 py-2 text-sm font-medium transition",
                    page === link.page
                      ? "bg-slate-100 text-slate-900"
                      : "text-slate-200 hover:bg-slate-800"
                  )}
                >
                  {link.label}
                </a>
              ))}
              <div className="flex items-center justify-between pt-2 text-sm">
                <span>{userEmail || "Guest"}</span>
                <a className="text-slate-200 underline" href={logoutUrl}>
                  {userEmail ? "Logout" : "Login"}
                </a>
              </div>
            </div>
          </div>
        )}
      </header>
      <main className="mx-auto max-w-7xl px-4 py-10">
        {children}
      </main>
    </div>
  );
}

function EmptyState({ title, description, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500">
      <h3 className="text-lg font-semibold text-slate-700">{title}</h3>
      {description && <p className="mt-2 text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

function HomePage({ data }) {
  const actions = data.actions || [];
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-900">{data.pageTitle || "Welcome"}</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-500">
          Navigate through the Zamora Plumbing Corp inventory toolkit. Each section has been redesigned with a responsive React +
          Tailwind interface for faster exploration and analysis.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {actions.map((action) => (
          <a
            key={action.href}
            href={action.href}
            className="group relative overflow-hidden rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg"
          >
            <div className="flex h-full flex-col justify-between">
              <div>
                <span className="inline-flex items-center rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-700">
                  Quick action
                </span>
                <h2 className="mt-4 text-lg font-semibold text-slate-900">{action.label}</h2>
              </div>
              <div className="mt-6 flex items-center justify-between text-sm font-medium text-sky-600">
                <span>Open</span>
                <span aria-hidden>→</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function Table({ columns, rows, renderRow }) {
  if (!rows || rows.length === 0) {
    return (
      <EmptyState
        title="No data available"
        description="Adjust your filters or try a different selection to populate the table."
      />
    );
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

function ViewAllPage({ data }) {
  const [supply, setSupply] = useState(data.supply || "supply1");
  const [rows, setRows] = useState(data.rows || []);
  const [columns] = useState(data.columns || []);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setRows(data.rows || []);
  }, [data.rows]);

  const handleSupplyChange = (event) => {
    const value = event.target.value;
    setSupply(value);
    setLoading(true);
    const url = new URL(data.viewAllUrl || window.location.pathname, window.location.origin);
    url.searchParams.set("supply", value);
    url.searchParams.set("format", "json");
    fetch(url.toString(), { headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((payload) => {
        setRows(payload.rows || []);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">All Inventory Records</h1>
          <p className="mt-1 text-sm text-slate-500">
            Browse the complete catalog for a supplier. Select a different supply to instantly refresh the dataset.
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500" htmlFor="supply-selector">
            Supply
          </label>
          <select
            id="supply-selector"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200 sm:w-56"
            value={supply}
            onChange={handleSupplyChange}
          >
            {(data.supplyOptions || []).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {loading ? (
        <EmptyState title="Loading records" description="Fetching the latest rows for the selected supply." />
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

function SearchPage({ data }) {
  const [supply, setSupply] = useState(data.supply || "supply1");
  const [query, setQuery] = useState(data.query || "");
  const [columns, setColumns] = useState(data.columns || []);
  const [rows, setRows] = useState(data.rows || []);
  const [loading, setLoading] = useState(false);

  const runSearch = (nextQuery, nextSupply) => {
    const trimmed = nextQuery.trim();
    if (!trimmed) {
      setColumns([]);
      setRows([]);
      return;
    }
    setLoading(true);
    const url = new URL(data.searchApi || "/api/search", window.location.origin);
    url.searchParams.set("supply", nextSupply);
    url.searchParams.set("query", trimmed);
    fetch(url.toString(), { headers: { Accept: "application/json" } })
      .then((response) => response.json())
      .then((payload) => {
        setColumns(payload.columns || []);
        setRows(payload.rows || []);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (query) {
      runSearch(query, supply);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Search Description</h1>
          <p className="text-sm text-slate-500">
            Type a description to discover matching items across the selected supplier. Results update instantly as you type.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supply</label>
            <select
              value={supply}
              onChange={(event) => {
                const value = event.target.value;
                setSupply(value);
                runSearch(query, value);
              }}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            >
              {(data.supplyOptions || []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Search query</label>
            <input
              type="text"
              value={query}
              onChange={(event) => {
                const value = event.target.value;
                setQuery(value);
                runSearch(value, supply);
              }}
              placeholder="Type a description"
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
          </div>
        </div>
      </div>
      {loading ? (
        <EmptyState title="Searching" description="Retrieving matches for your description." />
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
      .then((response) => response.json())
      .then((payload) => {
        setColumns(payload.columns || []);
        setRows(payload.rows || []);
      })
      .finally(() => setLoading(false));
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
            Compare monthly price averages and surface items that changed between consecutive periods within a custom date range.
          </p>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Supply</label>
          <select
            value={supply}
            onChange={(event) => setSupply(event.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            {(data.supplyOptions || []).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Start date</label>
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            required
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">End date</label>
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            required
          />
        </div>
        <div className="flex items-end">
          <Button type="submit" className="w-full">
            Analyze
          </Button>
        </div>
      </form>
      {loading ? (
        <EmptyState title="Analyzing" description="Crunching the numbers for your selected range." />
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

function ProductDetailPage({ data }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    if (!canvasRef.current || !data.chart) {
      return undefined;
    }
    const chart = new Chart(canvasRef.current, {
      type: "line",
      data: {
        labels: data.chart.dates,
        datasets: [
          {
            label: "Price per Unit",
            data: data.chart.prices,
            borderColor: "#0284c7",
            backgroundColor: "rgba(2,132,199,0.1)",
            tension: 0.25,
            pointRadius: 4,
            pointBackgroundColor: "#0c4a6e",
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            ticks: { color: "#475569" },
            grid: { color: "#e2e8f0" },
          },
          x: {
            ticks: { color: "#475569" },
            grid: { color: "#e2e8f0" },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
    return () => chart.destroy();
  }, [data.chart]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">{data.supply}</p>
          <h1 className="text-2xl font-semibold text-slate-900">{data.description}</h1>
        </div>
        <Button as="a" href={data.backUrl || "/view_all"} variant="secondary" className="w-full md:w-auto">
          ← Back
        </Button>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Price History</h2>
          <canvas ref={canvasRef} className="mt-4 h-64 w-full" aria-label="Price trend"></canvas>
        </div>
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="text-lg font-semibold text-slate-900">Transactions</h2>
          <Table
            columns={["Date", "Price per Unit"]}
            rows={data.rows || []}
            renderRow={(row, index) => (
              <>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{row.Date}</td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                  {row["Price per Unit"]}
                </td>
              </>
            )}
          />
        </div>
      </div>
    </div>
  );
}

function MaterialListPage({ data }) {
  const catalogLookups = useMemo(() => {
    const lookups = {};
    Object.entries(data.catalog || {}).forEach(([key, records]) => {
      const map = {};
      (records || []).forEach((item) => {
        const description = (item.Description || item["Product Description"] || item.description || "")
          .toLowerCase()
          .trim();
        if (!description) {
          return;
        }
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
  const [items, setItems] = useState(() => {
    return (data.products || []).map((product) => ({
      quantity: Number(product.quantity ?? product.Quantity ?? 0) || 0,
      description: product["Product Description"] || product.description || "",
      supply: product.Supply || product.supply || supplyCodes[lookupSupply],
      unit: product.Unit || product.unit || "",
      lastPrice: Number(product["Last Price"] ?? product.last_price ?? product["Price per Unit"] ?? 0) || 0,
      predetermined: true,
    }));
  });
  const [projectInfo, setProjectInfo] = useState({
    contractor: data.projectInfo?.contractor || "",
    address: data.projectInfo?.address || "",
    date: data.projectInfo?.date || "",
  });

  const productDataRef = useRef(null);
  const includePriceRef = useRef(null);
  const formRef = useRef(null);

  const supplyListIds = {
    supply1: "supply1List",
    supply2: "supply2List",
    supply3: "supply3List",
    supply4: "supply4List",
  };

  const datalistOptions = useMemo(() => {
    const options = {};
    Object.entries(data.catalog || {}).forEach(([key, records]) => {
      const unique = Array.from(
        new Set((records || []).map((record) => record.Description || record["Product Description"] || record.description || ""))
      ).filter(Boolean);
      options[key] = unique;
    });
    return options;
  }, [data.catalog]);

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
        unit: entry.unit || "",
        lastPrice: Number(entry.price.toFixed(2)),
      });
    } else {
      updateItem(index, { description: value });
    }
  };

  useEffect(() => {
    setItems((current) =>
      current.map((item) => {
        if (!item.predetermined || !item.description) {
          return item;
        }
        const normalized = item.description.toLowerCase().trim();
        const entry = catalogLookups[lookupSupply]?.[normalized];
        if (!entry) {
          return { ...item, supply: supplyCodes[lookupSupply] };
        }
        return {
          ...item,
          supply: supplyCodes[lookupSupply],
          unit: entry.unit || item.unit,
          lastPrice: Number(entry.price.toFixed(2)),
          total: Number(((Number(item.quantity) || 0) * entry.price).toFixed(2)),
        };
      })
    );
  }, [lookupSupply, catalogLookups]);

  const addManualItem = () => {
    setItems((current) => [
      ...current,
      {
        quantity: 0,
        description: "",
        supply: supplyCodes[lookupSupply],
        unit: "",
        lastPrice: 0,
        predetermined: false,
      },
    ]);
  };

  const removeItem = (index) => {
    setItems((current) => current.filter((_, idx) => idx !== index));
  };

  const moveItem = (index, direction) => {
    setItems((current) => {
      const next = [...current];
      const target = index + direction;
      if (target < 0 || target >= next.length) {
        return next;
      }
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return next;
    });
  };

  const grandTotal = useMemo(() => {
    return items.reduce((sum, item) => sum + Number(item.total || (item.quantity || 0) * (item.lastPrice || 0)), 0);
  }, [items]);

  const serializeProducts = () =>
    items.map((item) => ({
      description: item.description,
      supply: item.supply,
      unit: item.unit,
      last_price: Number(item.lastPrice || 0),
      quantity: Number(item.quantity || 0),
      total: Number(((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)),
    }));

  const handleExport = () => {
    const includePrice = window.confirm("Would you like to include the price in the PDF?");
    if (includePriceRef.current) {
      includePriceRef.current.value = includePrice ? "yes" : "no";
    }
    if (productDataRef.current) {
      productDataRef.current.value = JSON.stringify(serializeProducts());
    }
    formRef.current?.submit();
  };

  const handleSaveTemplate = () => {
    if (!templateName.trim()) {
      window.alert("Template name required");
      return;
    }
    const folder = templateFolder.trim();
    const fullName = folder ? `${folder}/${templateName.trim()}` : templateName.trim();
    const payload = new URLSearchParams();
    payload.set("template_name", fullName);
    payload.set("product_data", JSON.stringify(serializeProducts()));
    payload.set("project_info", JSON.stringify(projectInfo));
    fetch(data.saveTemplateUrl || "/save_template", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: payload.toString(),
    }).then(() => {
      window.location.href = `${data.listUrl}?list=${encodeURIComponent(fullName)}`;
    });
  };

  const handleTemplateChange = (event) => {
    const value = event.target.value;
    window.location.href = `${data.listUrl}?list=${encodeURIComponent(value)}`;
  };

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-slate-900">Material List</h1>
        {data.fullTemplateName && (
          <Badge tone="info">Editing template: {data.fullTemplateName}</Badge>
        )}
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 lg:col-span-2">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Choose template</label>
              <select
                value={data.listOption || "underground"}
                onChange={handleTemplateChange}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              >
                <option value="underground">Underground List</option>
                <option value="rough">Rough List</option>
                <option value="final">Final List</option>
                <option value="new">New List</option>
                {(data.customTemplates || []).map((name) => (
                  <option key={name} value={name}>
                    {name} Template
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Lookup supply</label>
              <select
                value={lookupSupply}
                onChange={(event) => setLookupSupply(event.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              >
                <option value="supply1">Supply 1</option>
                <option value="supply2">Supply 2</option>
                <option value="supply3">Lion Plumbing Supply</option>
                <option value="supply4">Bond Plumbing Supply</option>
              </select>
            </div>
          </div>
          <div className="mt-6 space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Project information</h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                name="contractor"
                value={projectInfo.contractor}
                onChange={(event) => setProjectInfo((info) => ({ ...info, contractor: event.target.value }))}
                placeholder="Contractor"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
              <input
                name="address"
                value={projectInfo.address}
                onChange={(event) => setProjectInfo((info) => ({ ...info, address: event.target.value }))}
                placeholder="Address"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
              <input
                type="date"
                name="date"
                value={projectInfo.date}
                onChange={(event) => setProjectInfo((info) => ({ ...info, date: event.target.value }))}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
              />
            </div>
          </div>
        </div>
        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Template save</h2>
          <div className="mt-4 space-y-3">
            <input
              value={templateFolder}
              onChange={(event) => setTemplateFolder(event.target.value)}
              list="template-folders"
              placeholder="Folder (optional)"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
            <input
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
              placeholder="Template name"
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
            />
            <Button type="button" onClick={handleSaveTemplate} className="w-full">
              Save template
            </Button>
          </div>
          <datalist id="template-folders">
            {(data.templateFolders || []).map((folder) => (
              <option key={folder} value={folder} />
            ))}
          </datalist>
        </div>
      </div>
      <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200">
            <thead className="bg-slate-50">
              <tr>
                {[
                  "Quantity",
                  "Product Description",
                  "Supply",
                  "Unit",
                  "Last Price",
                  "Total",
                  "Actions",
                ].map((header) => (
                  <th
                    key={header}
                    className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item, index) => (
                <tr key={index} className="hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm">
                    <input
                      type="number"
                      min="0"
                      value={item.quantity}
                      onChange={(event) => updateItem(index, { quantity: Number(event.target.value) })}
                      className="w-24 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <input
                      type="text"
                      value={item.description}
                      onChange={(event) => handleDescriptionChange(index, event.target.value)}
                      list={supplyListIds[lookupSupply]}
                      placeholder="Enter product"
                      className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <input
                      type="text"
                      value={item.supply}
                      onChange={(event) => updateItem(index, { supply: event.target.value })}
                      className="w-20 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <input
                      type="text"
                      value={item.unit}
                      onChange={(event) => updateItem(index, { unit: event.target.value })}
                      className="w-24 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <input
                      type="number"
                      value={item.lastPrice}
                      step="0.01"
                      min="0"
                      onChange={(event) => updateItem(index, { lastPrice: Number(event.target.value) })}
                      className="w-28 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    ${((Number(item.quantity) || 0) * (Number(item.lastPrice) || 0)).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        className="rounded-full bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-300"
                        onClick={() => moveItem(index, -1)}
                        aria-label="Move up"
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        className="rounded-full bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-600 transition hover:bg-slate-300"
                        onClick={() => moveItem(index, 1)}
                        aria-label="Move down"
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        className="rounded-full bg-rose-500 px-2 py-1 text-xs font-semibold text-white transition hover:bg-rose-600"
                        onClick={() => removeItem(index)}
                        aria-label="Remove item"
                      >
                        ×
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-slate-50">
              <tr>
                <td colSpan={5} className="px-4 py-3 text-right text-sm font-semibold text-slate-700">
                  Grand total
                </td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-900">${grandTotal.toFixed(2)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button type="button" onClick={addManualItem} variant="secondary">
          Add manual item
        </Button>
        <Button type="button" onClick={handleExport}>
          Export to PDF
        </Button>
        <Button as="a" href={data.downloadUrl} variant="ghost">
          Download PDF
        </Button>
      </div>
      <form
        method="POST"
        action={data.listUrl}
        ref={formRef}
        className="hidden"
      >
        <input type="hidden" name="contractor" value={projectInfo.contractor} />
        <input type="hidden" name="address" value={projectInfo.address} />
        <input type="hidden" name="date" value={projectInfo.date} />
        <input type="hidden" name="product_data" ref={productDataRef} />
        <input type="hidden" name="include_price" ref={includePriceRef} value="yes" />
      </form>
      <datalist id="supply1List">
        {(datalistOptions.supply1 || []).map((option) => (
          <option key={`s1-${option}`} value={option} />
        ))}
      </datalist>
      <datalist id="supply2List">
        {(datalistOptions.supply2 || []).map((option) => (
          <option key={`s2-${option}`} value={option} />
        ))}
      </datalist>
      <datalist id="supply3List">
        {(datalistOptions.supply3 || []).map((option) => (
          <option key={`s3-${option}`} value={option} />
        ))}
      </datalist>
      <datalist id="supply4List">
        {(datalistOptions.supply4 || []).map((option) => (
          <option key={`s4-${option}`} value={option} />
        ))}
      </datalist>
    </div>
  );
}

function TemplatesPage({ data }) {
  const entries = data.entries || [];
  const grouped = data.grouped || {};

  const applyQuery = (params) => {
    const url = new URL(window.location.href);
    Object.entries(params).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value);
      } else {
        url.searchParams.delete(key);
      }
    });
    window.location.href = url.toString();
  };

  const handleFolderCreate = (event) => {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    fetch(data.createFolderUrl || "/create_template_folder", {
      method: "POST",
      body: formData,
    }).then(() => window.location.reload());
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
    if (window.confirm(`Delete template "${entry.full_name}"?`)) {
      handleAction(entry.delete_url);
    }
  };

  const promptRename = (entry) => {
    const next = window.prompt("New template name", entry.full_name);
    if (next) {
      handleAction(entry.rename_url, { new_name: next });
    }
  };

  const promptMove = (entry) => {
    const target = window.prompt("Move to folder (leave blank for root)", entry.group || "");
    if (target !== null) {
      handleAction(entry.move_url, { target_folder: target });
    }
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
          <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-700">${
            row.total_with_tax?.toFixed?.(2) ?? row.total_with_tax
          }</td>
          <td className="px-4 py-3 text-sm">
            <div className="flex flex-wrap gap-2">
              <Button as="a" href={row.edit_url} variant="secondary" className="px-3 py-1 text-xs">
                Edit
              </Button>
              <Button type="button" variant="ghost" className="px-3 py-1 text-xs" onClick={() => promptRename(row)}>
                Rename
              </Button>
              <Button type="button" variant="ghost" className="px-3 py-1 text-xs" onClick={() => promptMove(row)}>
                Move
              </Button>
              <Button type="button" variant="danger" className="px-3 py-1 text-xs" onClick={() => confirmAndDelete(row)}>
                Delete
              </Button>
            </div>
          </td>
        </>
      )}
    />
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Saved Templates</h1>
          <p className="mt-1 text-sm text-slate-500">
            Organize and maintain proposal templates. Use the actions menu to quickly edit, rename, move, or delete entries.
          </p>
        </div>
        <form onSubmit={handleFolderCreate} className="flex gap-2">
          <input
            name="folder_name"
            placeholder="New folder"
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          />
          <Button type="submit" variant="secondary">
            Create folder
          </Button>
        </form>
      </div>
      <div className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sort by</label>
          <select
            value={data.sortKey || "name"}
            onChange={(event) => applyQuery({ sort: event.target.value })}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="name">Name</option>
            <option value="date">Date</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Group by</label>
          <select
            value={data.groupBy || "folder"}
            onChange={(event) => applyQuery({ group: event.target.value })}
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 shadow-sm focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200"
          >
            <option value="folder">Folder</option>
            <option value="none">None</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Folders</label>
          <div className="flex flex-wrap gap-2">
            {(data.folders || []).map((folder) => (
              <Badge key={folder}>{folder}</Badge>
            ))}
            {!data.folders?.length && <span className="text-sm text-slate-400">No custom folders yet.</span>}
          </div>
        </div>
      </div>
      {data.groupBy === "folder" ? (
        Object.keys(grouped).length ? (
          <div className="space-y-8">
            {Object.entries(grouped).map(([folder, folderEntries]) => (
              <div key={folder || "root"} className="space-y-3">
                <h2 className="text-lg font-semibold text-slate-800">{folder || "Ungrouped"}</h2>
                {renderTableRows(folderEntries)}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No templates saved"
            description="Create your first template from the Material List page and it will appear here."
          />
        )
      ) : (
        renderTableRows(entries)
      )}
    </div>
  );
}

function LoginPage({ data }) {
  return (
    <div className="mx-auto max-w-md space-y-6 rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
      <div className="space-y-2 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">Login</h1>
        <p className="text-sm text-slate-500">
          Enter your code or email to receive a sign-in link. The refreshed interface keeps all authentication flows unchanged.
        </p>
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
        <Button type="submit" className="w-full">
          Log in
        </Button>
      </form>
    </div>
  );
}

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

