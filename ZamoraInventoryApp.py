from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    session,
    jsonify,
    make_response,
    get_flashed_messages,
)
import io
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import time
import json
import base64
import random
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import os
import uuid
from werkzeug.utils import secure_filename

from sku_matcher import judge_same_product
from pdf_parser import parse_pdf
from db import (
    init_db, save_parsed_document, list_invoices, delete_invoice,
    load_catalog_to_memory, get_catalog_df, refresh_catalog,
    get_user, list_users, add_user, set_user_active, set_user_role,
    increment_failed_attempts, reset_failed_attempts,
)
import tempfile

# Additional imports for login functionality
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from itsdangerous import URLSafeTimedSerializer
from functools import wraps

# -------------------------------
# Application Configuration
# -------------------------------

import config
import data_utils as du

app = Flask(__name__)
init_db()
load_catalog_to_memory()
app.secret_key = config.SECRET_KEY

app.config["SESSION_PERMANENT"] = config.SESSION_PERMANENT
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["SESSION_COOKIE_SECURE"] = True   # requires HTTPS in production
app.config["SESSION_COOKIE_HTTPONLY"] = True

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    default_limits=[],
)
# -------------------------------
# Flask-Mail and Login Configuration
# -------------------------------

# Mail settings are sourced from environment variables in ``config.py``.
# This avoids hard-coding credentials in the repository.
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "aliant.delgado07@gmail.com"
app.config["MAIL_PASSWORD"] = "lgco kmqe emqr qdrj"  # Use an app-specific password if using 2FA
app.config["MAIL_DEFAULT_SENDER"] = "aliant.delgado07@gmail.com"

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


@app.errorhandler(429)
def ratelimit_handler(e):
    flash("Too many login attempts. Please wait and try again.", "danger")
    return redirect(url_for("login"))
# Buffer to temporarily store generated order summary PDFs
pdf_buffer: io.BytesIO | None = None
# -------------------------------
# Jinja Filters
# -------------------------------

@app.template_filter("datetimeformat")
def datetimeformat(value, fmt: str = "%Y-%m-%d %H:%M:%S"):
    """Format a timestamp for display in templates."""
    return datetime.fromtimestamp(value).strftime(fmt)
# -------------------------------
# Global Before-Request Handler (Session Timeout)
# -------------------------------

@app.before_request
def check_session_timeout():
    if request.endpoint in ('login', 'verify_code', 'verify_login', 'static'):
        return

    if "email" in session:
        # Backfill role for sessions created before role tracking was added
        if "role" not in session:
            user = get_user(session["email"])
            if user:
                session["role"] = user["role"]

        if session.get("email") == "zamoraplumbing01@gmail.com":
            return
        last_activity = session.get("last_activity", time.time())
        if time.time() - last_activity > 18000000:
            session.clear()
            flash("Session expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for("login"))
        session["last_activity"] = time.time()

# -------------------------------
# Login Helper Functions
# -------------------------------

def is_logged_in():
    if "email" in session:
        # Always consider the Zamora Plumbing account as active.
        if session.get("email") == "zamoraplumbing01@gmail.com":
            return True
        last_activity = session.get("last_activity", time.time())
        if time.time() - last_activity > 18000000:
            session.pop("email", None)
            flash("Session expired due to inactivity. Please log in again.", "warning")
            return False
        session["last_activity"] = time.time()
        return True
    return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Access denied.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function

SUPPLY_CODES = {
    "supply1": "BPS",
    "supply2": "S2",
    "supply3": "LPS",
    "supply4": "BOND",
}


def _ensure_supply_loaded(supply: str):
    loaders = {
        "supply1": du.load_default_file,
        "supply2": du.load_supply2_file,
        "supply3": du.load_supply3_file,
        "supply4": du.load_supply4_file,
    }
    loader = loaders.get(supply)
    if loader:
        loader()


def default_nav_links() -> list[dict[str, str]]:
    """Return the default navigation links for the React shell."""
    return [
        {"label": "Home", "href": url_for("index"), "page": "home"},
        {"label": "View All", "href": url_for("view_all"), "page": "view_all"},
        {"label": "Search", "href": url_for("search"), "page": "search"},
        {"label": "Analyze", "href": url_for("analyze"), "page": "analyze"},
        {"label": "Material List", "href": url_for("material_list"), "page": "material_list"},
        {"label": "Templates", "href": url_for("templates_list"), "page": "templates"},
        {"label": "Upload PDF", "href": url_for("upload_pdf"), "page": "upload_pdf"},
    ]


def render_app(
    page: str,
    initial_data: dict | None = None,
    nav_links: list[dict[str, str]] | None = None,
    status_code: int = 200,
):
    """Render the universal React shell template with serialized state."""

    context = {
        "page": page,
        "initial_data": initial_data or {},
        "nav_links": default_nav_links() if nav_links is None else nav_links,
        "flashes": get_flashed_messages(with_categories=True),
        "user_email": session.get("email"),
        "logout_url": url_for("logout") if session.get("email") else url_for("login"),
    }
    response = make_response(render_template("app.html", **context))
    response.status_code = status_code
    return response


def _search_supply_data(
    supply: str,
    query: str,
    page: int | None = None,
    per_page: int | None = None,
):
    """Search the in-memory catalog DataFrame and shape the result for JSON/React."""
    if not query:
        return {"rows": [], "columns": [], "next_page": None, "prev_page": None}

    df = get_catalog_df()
    if df is None or df.empty:
        return {"rows": [], "columns": [], "next_page": None, "prev_page": None}

    # Filter by supplier when not searching all
    code = SUPPLY_CODES.get(supply)
    if code:
        df = df[df["Supply"] == code]

    # Multi-keyword case-insensitive match on Description
    for kw in query.lower().split():
        df = df[df["Description"].str.lower().str.contains(kw, na=False, regex=False)]

    if df.empty:
        return {"rows": [], "columns": [], "next_page": None, "prev_page": None}

    df = df.sort_values(["Description", "Date"], ascending=[True, False])

    columns = ["Item Number", "Description", "Price per Unit", "Unit", "Invoice No.", "Date"]
    if supply == "all":
        columns.append("Supply")
    existing_cols = [c for c in columns if c in df.columns]

    rows = df[existing_cols].to_dict(orient="records")

    # Mark first 3 rows per description as recent; the rest are historical
    desc_counts: dict[str, int] = {}
    for row in rows:
        desc = row.get("Description", "")
        idx = desc_counts.get(desc, 0)
        row["is_recent"] = idx < 3
        desc_counts[desc] = idx + 1

    if supply != "all":
        for row in rows:
            desc = row.get("Description")
            if desc:
                row["graphUrl"] = url_for(
                    "product_detail", description=desc, supply=supply, ref="search", query=query
                )

    return {"rows": rows, "columns": existing_cols, "next_page": None, "prev_page": None}


def _analyze_price_changes(supply: str, start_date: str, end_date: str) -> dict:
    """Run the price change analysis and return JSON-serializable results."""
    _ensure_supply_loaded(supply)
    current_df = du.get_current_dataframe(supply)
    if current_df is None:
        return {"rows": [], "columns": []}

    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
    except Exception:
        return {"rows": [], "columns": []}

    filtered = current_df[(current_df["Date"] >= start) & (current_df["Date"] <= end)]
    if filtered.empty:
        return {"rows": [], "columns": []}

    grouped = filtered.groupby(["Description", filtered["Date"].dt.to_period("M")])
    result_records: list[dict] = []
    for (desc, month), group in grouped:
        avg_price = group["Price per Unit"].mean()
        next_month = month + 1
        if (desc, next_month) not in grouped.groups:
            continue
        next_group = grouped.get_group((desc, next_month))
        next_avg_price = next_group["Price per Unit"].mean()
        if avg_price != next_avg_price:
            result_records.extend(group.to_dict("records"))
            result_records.extend(next_group.to_dict("records"))

    if not result_records:
        return {"rows": [], "columns": []}

    results_df = pd.DataFrame(result_records)
    if "Date" in results_df.columns:
        results_df["Date"] = pd.to_datetime(results_df["Date"]).dt.strftime("%Y-%m-%d")

    columns = [
        col
        for col in [
            "Description",
            "Item Number",
            "Price per Unit",
            "Unit",
            "Invoice No.",
            "Date",
        ]
        if col in results_df.columns
    ]
    shaped = results_df[columns] if columns else results_df
    return {"rows": shaped.to_dict(orient="records"), "columns": columns or list(results_df.columns)}


# GitHub template saving helper
def save_template_to_github(filename: str, content: str) -> bool:
    """Save the given content to a GitHub repository as filename."""
    token = config.GITHUB_TOKEN
    repo = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH
    if not token or not repo:
        app.logger.error("GitHub credentials not configured")
        return False

    api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {"Authorization": f"Bearer {token}"}
    get_resp = requests.get(api_url, headers=headers, params={"ref": branch})
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None
    data = {
        "message": f"Add template {filename}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }
    if sha:
        data["sha"] = sha
    resp = requests.put(api_url, headers=headers, json=data)
    return resp.status_code in (200, 201)

# Helper to delete templates from GitHub
def delete_template_from_github(filename: str) -> bool:
    """Delete a template file from GitHub."""
    token = config.GITHUB_TOKEN
    repo = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH
    if not token or not repo:
        return False

    api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {"Authorization": f"Bearer {token}"}
    get_resp = requests.get(api_url, headers=headers, params={"ref": branch})
    if get_resp.status_code != 200:
        return False
    sha = get_resp.json().get("sha")
    if not sha:
        return False
    data = {"message": f"Delete template {filename}", "sha": sha, "branch": branch}
    resp = requests.delete(api_url, headers=headers, json=data)
    return resp.status_code == 200
# Helper to pull templates from GitHub when not present locally
def load_templates_if_stale():
    """Fetch template JSON files from GitHub and cache them locally."""
    token = config.GITHUB_TOKEN
    repo = config.GITHUB_REPO
    branch = config.GITHUB_BRANCH
    if not token or not repo:
        return

    templates_dir = config.TEMPLATE_DATA_DIR
    os.makedirs(templates_dir, exist_ok=True)

    api_url = f"https://api.github.com/repos/{repo}/contents/data"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"ref": branch}
    try:
        resp = requests.get(api_url, headers=headers, params=params)
        resp.raise_for_status()
        for item in resp.json():
            if item.get("name", "").endswith(".json"):
                download_url = item.get("url")
                if not download_url:
                    continue
                file_resp = requests.get(download_url, headers=headers, params=params)
                if file_resp.status_code != 200:
                    continue
                content = base64.b64decode(file_resp.json().get("content", "")).decode()
                with open(os.path.join(templates_dir, item["name"]), "w") as f:
                    f.write(content)
    except Exception as e:
        app.logger.error(f"Error fetching templates from GitHub: {e}")
# Load template/list data on startup
du.load_underground_list()
du.load_rough_list()
du.load_final_list()
load_templates_if_stale()


# -------------------------------
# Routes for Main Functionality (Protected by login_required)
# -------------------------------

# Main Menu – note: the file upload functionality has been removed.
@app.route("/")
@login_required
def index():
    template_count = 0
    templates_dir = config.TEMPLATE_DATA_DIR
    if os.path.exists(templates_dir):
        for _root, _dirs, files in os.walk(templates_dir):
            template_count += sum(1 for f in files if f.endswith(".json"))

    _df = get_catalog_df()
    def _unique_count(code):
        if _df is None or _df.empty:
            return 0
        return int(_df[_df["Supply"] == code]["Description"].nunique())

    stats = {
        "supply1Count": _unique_count("BPS"),
        "supply2Count": _unique_count("S2"),
        "supply3Count": _unique_count("LPS"),
        "supply4Count": _unique_count("BOND"),
        "templateCount": template_count,
    }

    initial = {
        "pageTitle": "Zamora Plumbing Corp Material Analyzer",
        "stats": stats,
        "actions": [
            {"label": "View All Content", "href": url_for("view_all"), "variant": "secondary"},
            {"label": "Search Description", "href": url_for("search"), "variant": "secondary"},
            {"label": "Analyze Price Changes", "href": url_for("analyze"), "variant": "secondary"},
            {"label": "Templates", "href": url_for("templates_list"), "variant": "secondary"},
            {"label": "Material List", "href": url_for("material_list"), "variant": "primary"},
            {"label": "Upload PDF", "href": url_for("upload_pdf"), "variant": "secondary"},
        ],
    }
    return render_app("home", initial)

@app.route("/view_all", methods=["GET"])
@login_required
def view_all():
    supply = request.args.get("supply", "supply1")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 200, type=int)

    code = SUPPLY_CODES.get(supply)
    df = get_catalog_df()

    if df is not None and not df.empty:
        if code:
            df = df[df["Supply"] == code]
        # Latest price per description: sort desc by Date, keep first occurrence
        df = (
            df.sort_values("Date", ascending=False)
            .drop_duplicates(subset=["Description"], keep="first")
            .sort_values("Description")
        )
    else:
        df = pd.DataFrame(columns=["Item Number", "Description", "Price per Unit", "Unit", "Date"])

    columns = ["Item Number", "Description", "Price per Unit", "Unit", "Date"]
    existing_cols = [c for c in columns if c in df.columns]
    total_rows = len(df)
    start = (page - 1) * per_page
    df_page = df.iloc[start : start + per_page]

    rows = []
    for record in df_page[existing_cols].to_dict(orient="records"):
        payload_row = {col: record.get(col, "") for col in existing_cols}
        desc = record.get("Description")
        if desc:
            payload_row["graphUrl"] = url_for(
                "product_detail", description=desc, supply=supply, ref="view_all"
            )
        rows.append(payload_row)

    supply_options = [
        {"value": "supply1", "label": "Supply 1"},
        {"value": "supply2", "label": "Supply 2"},
        {"value": "supply3", "label": "Lion Plumbing Supply"},
        {"value": "supply4", "label": "Bond Plumbing Supply"},
    ]

    payload = {
        "supply": supply,
        "columns": existing_cols,
        "rows": rows,
        "supplyOptions": supply_options,
        "productDetailBase": url_for("product_detail"),
        "viewAllUrl": url_for("view_all"),
        "page": page,
        "perPage": per_page,
        "totalRows": total_rows,
        "nextPage": page + 1 if (start + per_page) < total_rows else None,
        "prevPage": page - 1 if page > 1 else None,
    }

    if request.args.get("format") == "json":
        return jsonify(payload)

    return render_app("view_all", payload)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Render the React search page or redirect legacy POST submissions."""

    if request.method == "POST" and not request.is_json:
        supply_value = request.form.get("supply", "supply1")
        query_value = request.form.get("query", "").strip()
        if not query_value:
            flash("⚠ Please enter a search term.")
            return redirect(url_for("search", supply=supply_value))
        return redirect(url_for("search", supply=supply_value, query=query_value))

    supply = request.args.get("supply", "supply1")
    query = request.args.get("query", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", type=int)

    results_payload = _search_supply_data(supply, query, page, per_page)

    supply_options = [
        {"value": "supply1", "label": "Supply 1"},
        {"value": "supply2", "label": "Supply 2"},
        {"value": "supply3", "label": "Lion Plumbing Supply"},
        {"value": "supply4", "label": "Bond Plumbing Supply"},
        {"value": "all", "label": "All Supplies"},
    ]

    initial = {
        "supply": supply,
        "query": query,
        "columns": results_payload.get("columns", []),
        "rows": results_payload.get("rows", []),
        "nextPage": results_payload.get("next_page"),
        "prevPage": results_payload.get("prev_page"),
        "supplyOptions": supply_options,
        "searchApi": url_for("api_search"),
    }

    return render_app("search", initial)


@app.route("/api/search", methods=["GET"])
@login_required
def api_search():
    supply = request.args.get("supply", "supply1")
    query = request.args.get("query", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", type=int)
    payload = _search_supply_data(supply, query, page, per_page)
    return jsonify(
        {
            "columns": payload.get("columns", []),
            "rows": payload.get("rows", []),
            "next_page": payload.get("next_page"),
            "prev_page": payload.get("prev_page"),
        }
    )
    
@app.route("/api/sku_judge", methods=["POST"])
@login_required
def api_sku_judge():
    """
    JSON body: {"a": "<desc from supply A>", "b": "<desc from supply B>", "use_web": true}
    Returns JSON from judge_same_product.
    """
    try:
        data = request.get_json(force=True, silent=False) or {}
        a = (data.get("a") or "").strip()
        b = (data.get("b") or "").strip()
        use_web = bool(data.get("use_web", True))
        if not a or not b:
            return jsonify({"error": "Both 'a' and 'b' descriptions are required."}), 400

        app.logger.info(f"[sku_judge] Judging A='{a}' vs B='{b}', use_web={use_web}")
        result = judge_same_product(a, b, use_web=use_web, max_snippets=8)
        return jsonify(result), 200
    except Exception as e:
        app.logger.exception("SKU judge error")
        return jsonify({"error": str(e)}), 500

@app.route("/graph")
@login_required
def graph():
    """Generate a graph of Price per Unit over time for a given description from the selected supply."""
    supply = request.args.get("supply", "supply1")
    description = request.args.get("description")
    if not description:
        flash("⚠ Data or description not provided.")
        return redirect(url_for("index"))

    supplier_code = SUPPLY_CODES.get(supply)
    df = get_catalog_df()
    if df is None or df.empty:
        flash("⚠ No data available.")
        return redirect(url_for("index"))

    item_df = df[
        (df["Description"].str.lower() == description.lower()) &
        (df["Supply"] == supplier_code)
    ].copy()

    if item_df.empty:
        flash("⚠ No data available for the selected description.")
        return redirect(url_for("view_all", supply=supply))

    item_df = item_df.dropna(subset=["Date"]).sort_values(by="Date")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(item_df["Date"], item_df["Price per Unit"], marker="o")
    ax.set_title(f"Prices Over Time for '{description}'")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price per Unit")
    ax.grid(True)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.close(fig)
    output.seek(0)
    return send_file(output, mimetype="image/png")

@app.route("/graph_data")
@login_required
def graph_data():
    supply = request.args.get("supply", "supply1")
    description = request.args.get("description")
    if not description:
        return jsonify({"dates": [], "prices": []})

    supplier_code = SUPPLY_CODES.get(supply)
    df = get_catalog_df()
    if df is None or df.empty:
        return jsonify({"dates": [], "prices": []})

    item_df = df[
        (df["Description"].str.lower() == description.lower()) &
        (df["Supply"] == supplier_code)
    ].copy()

    item_df = item_df.dropna(subset=["Date"]).sort_values(by="Date")
    dates = item_df["Date"].tolist()
    prices = item_df["Price per Unit"].tolist()
    return jsonify({"dates": dates, "prices": prices})

@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    """
    Analyze price changes for items across a custom date range from the selected supply.
    """
    supply = request.args.get("supply", "supply1")
    _ensure_supply_loaded(supply)
    current_df = du.get_current_dataframe(supply)
    if current_df is None:
        flash("⚠ Please ensure the Excel file for the selected supply is available.")
        return redirect(url_for("index"))

    if request.method == "POST" and request.is_json:
        data = request.get_json(force=True) or {}
        supply_value = data.get("supply", supply)
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        result_payload = _analyze_price_changes(supply_value, start_date, end_date)
        return jsonify(result_payload)

    default_end = datetime.today().date()
    default_start = default_end - timedelta(days=30)

    if request.method == "POST":
        supply = request.form.get("supply", supply)
        start_date = request.form.get("start_date") or default_start.isoformat()
        end_date = request.form.get("end_date") or default_end.isoformat()
        result_payload = _analyze_price_changes(supply, start_date, end_date)
        if not result_payload.get("rows"):
            flash("⚠ No price changes found in the selected range.")
    else:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        if start_date and end_date:
            result_payload = _analyze_price_changes(supply, start_date, end_date)
        else:
            start_date = default_start.isoformat()
            end_date = default_end.isoformat()
            result_payload = {"rows": [], "columns": []}

    supply_options = [
        {"value": "supply1", "label": "Supply 1"},
        {"value": "supply2", "label": "Supply 2"},
        {"value": "supply3", "label": "Lion Plumbing Supply"},
        {"value": "supply4", "label": "Bond Plumbing Supply"},
    ]

    initial = {
        "supply": supply,
        "startDate": start_date,
        "endDate": end_date,
        "columns": result_payload.get("columns", []),
        "rows": result_payload.get("rows", []),
        "supplyOptions": supply_options,
        "analyzeApi": url_for("analyze"),
    }

    return render_app("analyze", initial)

@app.route("/product_detail", methods=["GET"])
@login_required
def product_detail():
    """
    Display a page for a specific product (from the selected supply) with:
      - A graph (rendered by the /graph endpoint)
      - A table with Date and Price per Unit for that product (sorted by Date).
    """
    supply = request.args.get("supply", "supply1")
    description = request.args.get("description")
    if not description:
        flash("⚠ Please provide a product description.")
        return redirect(url_for("index"))

    supplier_code = SUPPLY_CODES.get(supply)
    df = get_catalog_df()
    if df is None or df.empty:
        flash("⚠ No catalog data available.")
        return redirect(url_for("index"))

    item_df = df[
        (df["Description"].str.lower() == description.lower()) &
        (df["Supply"] == supplier_code)
    ].copy()

    if item_df.empty:
        flash("⚠ No data available for the selected product.")
        return redirect(url_for("view_all", supply=supply))

    item_df = item_df.dropna(subset=["Date"]).sort_values(by="Date")
    dates = item_df["Date"].tolist()
    prices = item_df["Price per Unit"].tolist()

    ref = request.args.get("ref", "view_all")
    query = request.args.get("query", "")
    if ref == "search":
        back_url = url_for("search", supply=supply, query=query)
    else:
        back_url = url_for("view_all", supply=supply)

    initial = {
        "description": description,
        "supply": supply,
        "rows": [{"Date": d, "Price per Unit": p} for d, p in zip(dates, prices)],
        "chart": {"dates": dates, "prices": prices},
        "backUrl": back_url,
    }

    return render_app("product_detail", initial)

@app.route("/material_list", methods=["GET", "POST"])
@login_required
def material_list():
    if request.method == "POST":
        contractor = request.form.get("contractor")
        address = request.form.get("address")
        order_date = request.form.get("date")
        product_data_json = request.form.get("product_data")
        try:
            product_data = json.loads(product_data_json) if product_data_json else []
        except Exception as e:
            flash("Error processing product data.", "danger")
            return redirect(url_for("material_list"))
        
        # Retrieve include_price choice from the form:
        include_price = request.form.get("include_price", "yes")
        
        subtotal = sum(float(item.get("total", 0)) for item in product_data)
        tax = subtotal * 0.07
        total_cost = subtotal + tax

        os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp")
        css_path = os.path.join(app.root_path, "static", "css", "order_summary.css")
        rendered = render_template(
            "order_summary.html",
            contractor=contractor,
            address=address,
            order_date=order_date,
            products=product_data,
            subtotal=subtotal,
            tax=tax,
            total_cost=total_cost,
            include_price=include_price,
            css_link=f"file://{css_path}",
        )
        import pdfkit
        try:
            options = {"enable-local-file-access": None}
            pdf = pdfkit.from_string(rendered, False, options=options, css=css_path)
            global pdf_buffer
            pdf_buffer = io.BytesIO(pdf)
            pdf_buffer.seek(0)
            # Persist PDF to a temporary file for reliability across workers
            old_path = session.pop("pdf_path", None)
            if old_path and os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except OSError:
                    pass
            address_filename = secure_filename(address) or "order_summary"
            pdf_filename = f"{address_filename}_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
            with open(pdf_path, "wb") as f:
                f.write(pdf)
            session["pdf_path"] = pdf_path
            session["last_address"] = address
            session["last_address_filename"] = address_filename
        except Exception as e:
            flash(f"PDF generation failed: {e}", "danger")
            return redirect(url_for("material_list"))

        recipient = session.get("email")
        subject_address = address or ""
        msg = Message(f"Material list- {subject_address}", recipients=[recipient])
        msg.body = "Please find attached your order summary PDF."
        msg.attach(f"{address_filename}.pdf", "application/pdf", pdf)
        try:
            mail.send(msg)
            flash("Order summary PDF sent to your email.", "success")
        except Exception as e:
            flash(f"Error sending email: {e}", "danger")

        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{address_filename}.pdf",
        )
    
    # For GET: load predetermined or saved templates
    list_option = request.args.get("list", "underground")
    load_templates_if_stale()
    templates_dir = config.TEMPLATE_DATA_DIR
    os.makedirs(templates_dir, exist_ok=True)
    custom_templates = {}
    template_folders = set()
    for root, dirs, files in os.walk(templates_dir):
        rel_dir = os.path.relpath(root, templates_dir)
        if rel_dir != ".":
            template_folders.add(rel_dir)
        for fname in files:
            if fname.endswith(".json"):
                try:
                    path = os.path.join(root, fname)
                    with open(path) as f:
                        name = os.path.splitext(fname)[0]
                        full_name = os.path.join(rel_dir, name) if rel_dir != "." else name
                        custom_templates[full_name] = json.load(f)
                except Exception:
                    pass
    list_option_lower = list_option.lower()
    project_info = {"contractor": "", "address": "", "date": ""}
    if list_option in custom_templates:
        raw_template = custom_templates[list_option]
        if isinstance(raw_template, dict):
            project_info = raw_template.get("project_info", project_info)
            raw_list = raw_template.get("products", [])
        else:
            raw_list = raw_template
        product_list = []
        for item in raw_list:
            desc = (
                item.get("Product Description")
                or item.get("description")
                or item.get("Description")
                or ""
            )
            price = (
                item.get("Last Price")
                or item.get("last_price")
                or item.get("Price per Unit")
                or 0
            )
            qty = item.get("quantity", 0)
            unit = item.get("Unit") or item.get("unit", "")
            total = item.get("total") or item.get("Total") or 0
            supply = item.get("Supply") or item.get("supply", "BPS")
            product_list.append(
                {
                    "Product Description": desc,
                    "Last Price": price,
                    "quantity": qty,
                    "Unit": unit,
                    "total": total,
                    "Supply": supply,
                }
            )
    elif list_option_lower == "underground":
        du.update_underground_prices()
        product_list = du.df_underground.to_dict("records") if du.df_underground is not None else []
    elif list_option_lower == "rough":
        du.update_rough_prices()
        product_list = du.df_rough.to_dict("records") if du.df_rough is not None else []
    elif list_option_lower == "final":
        du.update_final_prices()
        product_list = du.df_final.to_dict("records") if du.df_final is not None else []
    elif list_option_lower == "new":
        product_list = []
    else:
        product_list = []

    _cat = get_catalog_df()
    def _catalog_for(code):
        if _cat is None or _cat.empty:
            return []
        sub = _cat[_cat["Supply"] == code]
        return (
            sub.sort_values("Date", ascending=False)
            .drop_duplicates(subset=["Description"], keep="first")
            .sort_values("Description")
            .to_dict(orient="records")
        )

    supply1_products = _catalog_for("BPS")
    supply2_products = _catalog_for("S2")
    supply3_products = _catalog_for("LPS")
    supply4_products = _catalog_for("BOND")
    template_name_arg = request.args.get("template_name", "")
    if not template_name_arg and list_option_lower not in ["underground", "rough", "final", "new"]:
        template_name_arg = list_option
    full_template_name = template_name_arg
    template_folder = ""
    template_name = template_name_arg
    if template_name_arg:
        template_folder, template_name = os.path.split(template_name_arg)
        if template_folder == ".":
            template_folder = ""
    initial = {
        "listOption": list_option,
        "products": product_list,
        "projectInfo": project_info,
        "customTemplates": sorted(custom_templates.keys()),
        "templateFolders": sorted(template_folders),
        "templateName": template_name,
        "templateFolder": template_folder,
        "fullTemplateName": full_template_name,
        "catalog": {
            "supply1": supply1_products,
            "supply2": supply2_products,
            "supply3": supply3_products,
            "supply4": supply4_products,
        },
        "listUrl": url_for("material_list"),
        "downloadUrl": url_for("download_summary"),
        "saveTemplateUrl": url_for("save_template"),
    }

    return render_app("material_list", initial)

@app.route("/save_template", methods=["POST"])
@login_required
def save_template():
    template_name = request.form.get("template_name")
    product_data = request.form.get("product_data")
    project_info_str = request.form.get("project_info")
    if not template_name or not product_data:
        flash("Template name and data are required.", "danger")
        return redirect(url_for("material_list"))
    try:
        products = json.loads(product_data)
    except Exception:
        flash("Invalid product data.", "danger")
        return redirect(url_for("material_list"))
    try:
        project_info = json.loads(project_info_str) if project_info_str else {}
    except Exception:
        project_info = {}
    content = json.dumps({"project_info": project_info, "products": products})
    filename = f"data/{template_name}.json"
    # Save locally
    templates_dir = config.TEMPLATE_DATA_DIR
    filepath = os.path.join(templates_dir, f"{template_name}.json")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w") as f:
            f.write(content)
    except Exception as e:
        app.logger.error(f"Local template save failed: {e}")

    success = save_template_to_github(filename, content)
    if success:
        flash("Template saved to GitHub.", "success")
    else:
        flash("Failed to save template to GitHub.", "danger")
    return redirect(url_for("material_list"))

# -------------------------------
# Template Management Routes
# -------------------------------

@app.route("/templates")
@login_required
def templates_list():
    load_templates_if_stale()
    templates_dir = config.TEMPLATE_DATA_DIR
    os.makedirs(templates_dir, exist_ok=True)
    sort_key = request.args.get("sort", "name")
    group_by = request.args.get("group", "folder")
    entries = []
    folder_set = set()
    for root, dirs, files in os.walk(templates_dir):
        for d in dirs:
            rel_dir = os.path.relpath(os.path.join(root, d), templates_dir)
            folder_set.add(rel_dir)
        for f in files:
            if f.endswith(".json"):
                path = os.path.join(root, f)
                rel_dir = os.path.relpath(root, templates_dir)
                group = "" if rel_dir == "." else rel_dir
                name = os.path.splitext(f)[0]
                full_name = os.path.join(group, name) if group else name

                subtotal = 0.0
                item_count = 0
                try:
                    with open(path, "r") as fh:
                        content = json.load(fh)
                    products = content.get("products", []) if isinstance(content, dict) else content
                    item_count = len(products)
                    for item in products:
                        try:
                            total = item.get("total")
                            subtotal += float(total) if total is not None else float(item.get("last_price", 0)) * float(item.get("quantity", 0))
                        except (TypeError, ValueError):
                            continue
                except Exception:
                    subtotal = 0.0

                tax = subtotal * config.TAX_RATE
                total_with_tax = subtotal + tax

                entries.append({
                    "name": name,
                    "full_name": full_name,
                    "group": group,
                    "mtime": os.path.getmtime(path),
                    "item_count": item_count,
                    "total_with_tax": total_with_tax,
                    "edit_url": url_for("edit_template", name=full_name),
                    "delete_url": url_for("delete_template", name=full_name),
                    "rename_url": url_for("rename_template", name=full_name),
                    "move_url": url_for("move_template", name=full_name),
                })
    folders = sorted(folder_set)
    if sort_key == "date":
        entries.sort(key=lambda x: x["mtime"])
    else:
        entries.sort(key=lambda x: x["name"].lower())
    grouped = {}
    if group_by == "folder":
        for e in entries:
            grouped.setdefault(e["group"], []).append(e)

    initial = {
        "entries": entries,
        "grouped": grouped if group_by == "folder" else None,
        "sortKey": sort_key,
        "groupBy": group_by,
        "folders": folders,
        "createFolderUrl": url_for("create_template_folder"),
    }

    return render_app("templates", initial)


@app.route("/edit_template/<path:name>")
@login_required
def edit_template(name):
    return redirect(url_for("material_list", list=name, template_name=name))


@app.route("/api/template_preview")
@login_required
def api_template_preview():
    """Return the products inside a saved template for the preview panel."""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"products": []}), 400

    templates_dir = config.TEMPLATE_DATA_DIR
    filepath = os.path.join(templates_dir, f"{name}.json")

    if not os.path.exists(filepath):
        return jsonify({"products": []}), 404

    try:
        with open(filepath) as f:
            content = json.load(f)
        products = (
            content.get("products", [])
            if isinstance(content, dict)
            else content
        )
        return jsonify({"products": products})
    except Exception as e:
        app.logger.error(f"Template preview error: {e}")
        return jsonify({"products": [], "error": str(e)}), 500


@app.route("/api/duplicate_template", methods=["POST"])
@login_required
def api_duplicate_template():
    """Duplicate a saved template under a new name."""
    source_name = request.form.get("source_name", "").strip()
    new_name = request.form.get("new_name", "").strip()

    if not source_name or not new_name:
        return jsonify({"error": "source_name and new_name are required"}), 400

    templates_dir = config.TEMPLATE_DATA_DIR
    src_path = os.path.join(templates_dir, f"{source_name}.json")
    dst_path = os.path.join(templates_dir, f"{new_name}.json")

    if not os.path.exists(src_path):
        return jsonify({"error": "Source template not found"}), 404

    if os.path.exists(dst_path):
        return jsonify({"error": "A template with that name already exists"}), 409

    try:
        with open(src_path) as f:
            content = f.read()

        os.makedirs(os.path.dirname(dst_path), exist_ok=True)

        with open(dst_path, "w") as f:
            f.write(content)

        # Also save to GitHub
        success = save_template_to_github(f"data/{new_name}.json", content)
        if not success:
            app.logger.warning("Duplicate saved locally but GitHub sync failed.")

        return jsonify({"success": True, "new_name": new_name})
    except Exception as e:
        app.logger.error(f"Duplicate template error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/delete_template/<path:name>", methods=["POST"])
@login_required
def delete_template(name):
    templates_dir = config.TEMPLATE_DATA_DIR
    filepath = os.path.join(templates_dir, f"{name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    delete_template_from_github(f"data/{name}.json")
    flash("Template deleted.", "info")
    return redirect(request.referrer or url_for("templates_list"))


@app.route("/create_template_folder", methods=["POST"])
@login_required
def create_template_folder():
    folder_name = request.form.get("folder_name", "").strip()
    if not folder_name:
        flash("Folder name required.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    templates_dir = config.TEMPLATE_DATA_DIR
    path = os.path.join(templates_dir, folder_name)
    try:
        os.makedirs(path, exist_ok=True)
        flash("Folder created.", "success")
    except Exception as e:
        flash(f"Failed to create folder: {e}", "danger")
    return redirect(request.referrer or url_for("templates_list"))


@app.route("/rename_template/<path:name>", methods=["POST"])
@login_required
def rename_template(name):
    new_name = request.form.get("new_name")
    if not new_name:
        flash("New name required.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    templates_dir = config.TEMPLATE_DATA_DIR
    old_path = os.path.join(templates_dir, f"{name}.json")
    new_path = os.path.join(templates_dir, f"{new_name}.json")
    if not os.path.exists(old_path):
        flash("Template not found.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    try:
        with open(old_path) as f:
            content = f.read()
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        os.rename(old_path, new_path)
    except Exception as e:
        flash(f"Rename failed: {e}", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    success = save_template_to_github(f"data/{new_name}.json", content)
    if success:
        delete_template_from_github(f"data/{name}.json")
        flash("Template renamed.", "success")
    else:
        flash("Failed to update GitHub.", "danger")
    load_templates_if_stale()
    return redirect(url_for("templates_list"))


@app.route("/move_template/<path:name>", methods=["POST"])
@login_required
def move_template(name):
    target_folder = request.form.get("target_folder", "").strip()
    new_folder = request.form.get("new_folder", "").strip()
    destination = new_folder or target_folder
    templates_dir = config.TEMPLATE_DATA_DIR
    src_path = os.path.join(templates_dir, f"{name}.json")
    if not os.path.exists(src_path):
        flash("Template not found.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    base_name = os.path.basename(name)
    dest_dir = os.path.join(templates_dir, destination) if destination else templates_dir
    dest_path = os.path.join(dest_dir, f"{base_name}.json")
    try:
        os.makedirs(dest_dir, exist_ok=True)
        with open(src_path) as f:
            content = f.read()
        os.rename(src_path, dest_path)
    except Exception as e:
        flash(f"Move failed: {e}", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    new_rel_path = os.path.join(destination, base_name) if destination else base_name
    success = save_template_to_github(f"data/{new_rel_path}.json", content)
    if success:
        delete_template_from_github(f"data/{name}.json")
        flash("Template moved.", "success")
    else:
        flash("Failed to update GitHub.", "danger")
    load_templates_if_stale()
    return redirect(url_for("templates_list"))


# -------------------------------
# PDF Download Route
# -------------------------------

@app.route("/download_summary")
@login_required
def download_summary():
    """Return the last generated order summary PDF."""
    global pdf_buffer
    address_filename = session.get("last_address_filename", "order_summary")
    if pdf_buffer is not None:
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{address_filename}.pdf",
        )
    pdf_path = session.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{address_filename}.pdf",
        )

    flash("No PDF available for download.", "warning")
    return redirect(url_for("material_list"))
# -------------------------------
# Login and Logout Routes
# -------------------------------

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute;10 per hour", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        user = get_user(email)
        if not user or not user["active"]:
            flash("Unauthorized email.", "danger")
            return redirect(url_for("login"))

        code = str(random.randint(100000, 999999))
        session["login_pending"] = {
            "email": email,
            "code": code,
            "ts": time.time(),
        }

        msg = Message("Your Login Code", recipients=[email])
        msg.body = (
            f"Your Zamora Inventory login code is: {code}\n\n"
            "This code expires in 10 minutes. Do not share it."
        )
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Error sending login code: {e}")
            flash("Error sending email. Please try again later.", "danger")
            return redirect(url_for("login"))

        flash("A 6-digit login code has been sent to your email.", "info")
        return redirect(url_for("verify_code"))

    return render_app("login", {"loginUrl": url_for("login")}, nav_links=[])


@app.route("/verify_code", methods=["GET", "POST"])
def verify_code():
    pending = session.get("login_pending")
    if not pending:
        flash("No login in progress.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        entered = request.form.get("code", "").strip()
        email = pending["email"]

        if time.time() - pending["ts"] > 600:
            session.pop("login_pending", None)
            flash("Code expired, please request a new one.", "danger")
            return redirect(url_for("login"))

        if entered != pending["code"]:
            new_count = increment_failed_attempts(email)
            if new_count >= 5:
                set_user_active(email, 0)
                session.pop("login_pending", None)
                flash(
                    "Too many failed attempts. Your account has been deactivated. "
                    "Please contact an admin.",
                    "danger",
                )
                return redirect(url_for("login"))
            remaining = 5 - new_count
            flash(f"Invalid code. {remaining} attempt(s) remaining.", "danger")
            return redirect(url_for("verify_code"))

        # Success — clear pending code and open session
        session.pop("login_pending", None)
        reset_failed_attempts(email)

        user = get_user(email)
        session["email"] = email
        session["role"] = user["role"]
        session.permanent = True
        session["last_activity"] = time.time()

        flash("Login successful!", "success")
        return redirect(url_for("index"))

    return render_template("verify_code.html", email=pending["email"])


@app.route("/verify_login/<token>")
def verify_login(token):
    """Legacy magic-link route kept for backwards compatibility."""
    try:
        email = serializer.loads(token, salt="email-confirmation", max_age=600)
        user = get_user(email)
        if not user or not user["active"]:
            flash("This account is not authorised.", "danger")
            return redirect(url_for("login"))
        session["email"] = email
        session["role"] = user["role"]
        session.permanent = True
        session["last_activity"] = time.time()
        flash("Login successful!", "success")
        return redirect(url_for("index"))
    except Exception:
        flash("Invalid or expired login link.", "danger")
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# -------------------------------
# Admin Routes
# -------------------------------

@app.route("/admin/users")
@admin_required
def admin_users():
    users = list_users()
    return render_template(
        "admin_users.html",
        users=users,
        add_url=url_for("admin_add_user"),
        toggle_url=url_for("admin_toggle_user"),
        role_url=url_for("admin_set_role"),
    )


@app.route("/admin/users/add", methods=["POST"])
@admin_required
def admin_add_user():
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "user")
    if not email:
        flash("Email is required.", "danger")
    elif role not in ("user", "admin"):
        flash("Invalid role.", "danger")
    elif not add_user(email, role):
        flash(f"{email} is already in the whitelist.", "warning")
    else:
        flash(f"{email} added as {role}.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/toggle", methods=["POST"])
@admin_required
def admin_toggle_user():
    email = request.form.get("email", "").strip().lower()
    action = request.form.get("action", "")
    if not email or action not in ("activate", "deactivate"):
        flash("Invalid request.", "danger")
        return redirect(url_for("admin_users"))
    set_user_active(email, 1 if action == "activate" else 0)
    if action == "activate":
        reset_failed_attempts(email)
    flash(f"{email} {action}d.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/users/role", methods=["POST"])
@admin_required
def admin_set_role():
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "")
    if not email or role not in ("user", "admin"):
        flash("Invalid request.", "danger")
        return redirect(url_for("admin_users"))
    set_user_role(email, role)
    flash(f"{email} role set to {role}.", "success")
    return redirect(url_for("admin_users"))

# -------------------------------
# PDF Upload Routes
# -------------------------------

@app.route("/upload_pdf", methods=["GET", "POST"])
@login_required
def upload_pdf():
    """
    GET  — show the upload page (history of imported docs + upload form)
    POST — accept a PDF, parse it, save to DB, return result
    """
    _SUPPLIERS = [
        {"code": "LPS",  "label": "Lion Plumbing Supply"},
        {"code": "BPS",  "label": "Berger Plumbing Supply"},
        {"code": "S2",   "label": "Supply 2"},
        {"code": "BOND", "label": "Bond Plumbing Supply"},
    ]

    if request.method == "GET":
        invoices = list_invoices()
        initial = {
            "invoices": invoices,
            "uploadUrl": url_for("upload_pdf"),
            "deleteUrl": url_for("delete_invoice_route"),
            "confirmUrl": url_for("confirm_upload"),
            "suppliers": _SUPPLIERS,
        }
        return render_app("upload_pdf", initial)

    # ── POST: parse only — does NOT save to DB ────────────────────────────
    if "pdf_file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    pdf_file = request.files["pdf_file"]
    if not pdf_file.filename or not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "Please upload a PDF file"}), 400

    supplier = request.form.get("supplier", "LPS")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        parsed = parse_pdf(tmp_path, supplier=supplier)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"PDF parse error: {e}")
        return jsonify({"success": False, "error": "Failed to parse PDF. Check server logs."}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return jsonify({
        "success": True,
        "doc_type": parsed["doc_type"],
        "order_number": parsed["order_number"],
        "date": parsed["date"],
        "job_name": parsed["job_name"],
        "supplier": parsed["supplier"],
        "item_count": len(parsed["items"]),
        "items": parsed["items"],
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


@app.route("/confirm_upload", methods=["POST"])
@login_required
def confirm_upload():
    """
    Accepts the user-reviewed parsed data as JSON and saves it to the DB.
    Body: { "parsed": {...doc fields + items...}, "filename": "..." }
    """
    body = request.get_json(force=True, silent=True) or {}
    app.logger.info(f"confirm_upload received: {body}")
    print(f"confirm_upload received: {body}")
    parsed = body.get("parsed")
    filename = body.get("filename", "")

    if not parsed or not isinstance(parsed, dict):
        return jsonify({"success": False, "error": "No parsed data provided."}), 400

    required = {"doc_type", "order_number", "items"}
    missing = required - parsed.keys()
    if missing:
        return jsonify({"success": False, "error": f"Missing fields: {missing}"}), 400

    invoice_id = save_parsed_document(parsed, filename=filename)

    if invoice_id == -1:
        return jsonify({
            "success": False,
            "duplicate": True,
            "error": f"Document {parsed['order_number']} has already been imported.",
        }), 409

    refresh_catalog()

    return jsonify({
        "success": True,
        "invoice_id": invoice_id,
        "doc_type": parsed["doc_type"],
        "order_number": parsed["order_number"],
        "date": parsed.get("date", ""),
        "job_name": parsed.get("job_name", ""),
        "item_count": len(parsed["items"]),
    })


# -------------------------------
# Run the Application
# -------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
