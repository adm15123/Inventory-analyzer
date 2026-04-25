# ================================================================
# PDF UPLOAD ROUTES
# Add these to ZamoraInventoryApp.py
#
# STEP 1: Add these imports at the top of ZamoraInventoryApp.py
#         (after your existing imports):
#
#   from pdf_parser import parse_pdf
#   from db import init_db, save_parsed_document, list_invoices, delete_invoice
#
# STEP 2: After  app = Flask(__name__)  add:
#
#   init_db()
#
# STEP 3: Paste all the routes below into ZamoraInventoryApp.py
# ================================================================

import tempfile
from pdf_parser import parse_pdf
from db import init_db, save_parsed_document, list_invoices, delete_invoice

# Call this once after app is created:
# init_db()


@app.route("/upload_pdf", methods=["GET", "POST"])
@login_required
def upload_pdf():
    """
    GET  — show the upload page (history of imported docs + upload form)
    POST — accept a PDF, parse it, save to DB, return result
    """
    if request.method == "GET":
        invoices = list_invoices()
        initial = {
            "invoices": invoices,
            "uploadUrl": url_for("upload_pdf"),
            "deleteUrl": url_for("delete_invoice_route"),
        }
        return render_app("upload_pdf", initial)

    # ── POST ──────────────────────────────────────────────────────────────
    if "pdf_file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    pdf_file = request.files["pdf_file"]
    if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Please upload a PDF file"}), 400

    # Save to a temp file so pdfplumber can open it
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        parsed = parse_pdf(tmp_path)
    except ValueError as e:
        os.unlink(tmp_path)
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        os.unlink(tmp_path)
        app.logger.error(f"PDF parse error: {e}")
        return jsonify({"success": False, "error": "Failed to parse PDF. Check server logs."}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    invoice_id = save_parsed_document(parsed, filename=pdf_file.filename)

    if invoice_id == -1:
        return jsonify({
            "success": False,
            "duplicate": True,
            "error": f"Document {parsed['order_number']} has already been imported.",
        }), 409

    return jsonify({
        "success": True,
        "invoice_id": invoice_id,
        "doc_type": parsed["doc_type"],
        "order_number": parsed["order_number"],
        "date": parsed["date"],
        "job_name": parsed["job_name"],
        "item_count": len(parsed["items"]),
        "items_preview": parsed["items"][:5],   # first 5 for preview
    })


@app.route("/delete_invoice", methods=["POST"])
@login_required
def delete_invoice_route():
    invoice_id = request.form.get("invoice_id", type=int)
    if not invoice_id:
        flash("Invalid invoice ID.", "danger")
        return redirect(url_for("upload_pdf"))
    delete_invoice(invoice_id)
    flash("Document deleted.", "success")
    return redirect(url_for("upload_pdf"))
