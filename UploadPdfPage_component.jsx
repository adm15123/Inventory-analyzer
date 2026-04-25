// ================================================================
// UploadPdfPage
// Add this component to reactApp.jsx
//
// ALSO add "upload_pdf" to pageComponentMap:
//   upload_pdf: UploadPdfPage,
//
// AND add a nav link in ZamoraInventoryApp.py nav_links:
//   {"label": "Upload PDF", "href": url_for("upload_pdf")}
// ================================================================

function UploadPdfPage({ data }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [invoices, setInvoices] = useState(data.invoices || []);
  const fileInputRef = React.useRef(null);

  const uploadFile = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please select a PDF file.");
      return;
    }
    setUploading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("pdf_file", file);

    try {
      const resp = await fetch(data.uploadUrl || "/upload_pdf", {
        method: "POST",
        body: formData,
      });
      const json = await resp.json();

      if (json.success) {
        setResult(json);
        // Reload invoice list
        const listResp = await fetch("/upload_pdf", { headers: { Accept: "application/json" } });
        // Re-fetch by reloading page data — simplest approach
        window.location.reload();
      } else if (json.duplicate) {
        setError(`Already imported: ${json.error}`);
      } else {
        setError(json.error || "Upload failed.");
      }
    } catch (e) {
      setError("Network error. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  const handleFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  };

  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);

  const docTypeBadge = (type) =>
    type === "invoice"
      ? "bg-sky-100 text-sky-700"
      : "bg-violet-100 text-violet-700";

  return (
    <div className="space-y-8">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Upload PDF Invoice or Bid</h1>
        <p className="mt-1 text-sm text-slate-500">
          Drop a Lion Plumbing Supply Sales Order Acknowledgement or Bid Proposal.
          Items are extracted automatically and saved to the database.
        </p>
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
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleFileInput}
        />
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
            <p className="text-xs text-slate-400">Sales Order Acknowledgement or Bid Proposal</p>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-200">
          ⚠ {error}
        </div>
      )}

      {/* Success result */}
      {result && (
        <div className="rounded-2xl bg-emerald-50 p-5 ring-1 ring-emerald-200 space-y-3">
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
            <div><span className="font-medium">Job:</span> {result.job_name}</div>
          </div>
          {result.items_preview?.length > 0 && (
            <div className="text-xs text-emerald-600">
              <span className="font-medium">First items: </span>
              {result.items_preview.map((i) => i.description).join(" · ")}
              {result.item_count > 5 && ` · +${result.item_count - 5} more`}
            </div>
          )}
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
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {inv.imported_at?.slice(0, 10)}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 max-w-[140px] truncate">
                      {inv.filename || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <form method="POST" action={data.deleteUrl || "/delete_invoice"}
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
