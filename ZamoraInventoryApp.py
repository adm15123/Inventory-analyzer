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
)
import io
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import time
import json
import base64
import requests
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import os
import uuid
from werkzeug.utils import secure_filename

from lion_matcher import match_to_lion
from sku_matcher import judge_same_product

# Additional imports for login functionality
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from functools import wraps

# -------------------------------
# Application Configuration
# -------------------------------

import config
import data_utils as du

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.config["SESSION_PERMANENT"] = config.SESSION_PERMANENT
app.config["PERMANENT_SESSION_LIFETIME"] = config.PERMANENT_SESSION_LIFETIME
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
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
ALLOWED_EMAILS = [
    "aliant.delgado@yahoo.com",
    "aliant.delgado17@gmail.com",
    "zamoraplumbing01@gmail.com",
    "aliant.delgado01@yahoo.com"
]
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
    # Skip timeout check for login, verification, and static assets.
    if request.endpoint in ('login', 'verify_login', 'static'):
        return

    if "email" in session:
        # Bypass inactivity timeout for the Zamora Plumbing account.
        if session.get("email") == "zamoraplumbing01@gmail.com":
            return
        last_activity = session.get("last_activity", time.time())
        if time.time() - last_activity > 18000000:  # 30 minutes inactivity
            session.pop("email", None)
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

# -------------------------------
# Utility Functions (delegated to data_utils)
# -------------------------------

preprocess_text_for_search = du.preprocess_text_for_search
load_default_file = du.load_default_file
load_supply2_file = du.load_supply2_file
load_supply3_file = du.load_supply3_file
load_underground_list = du.load_underground_list
load_rough_list = du.load_rough_list
load_final_list = du.load_final_list
get_current_dataframe = du.get_current_dataframe
update_underground_prices = du.update_underground_prices
update_rough_prices = du.update_rough_prices
update_final_prices = du.update_final_prices

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
def load_templates_from_github():
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
# Load data on startup
load_default_file()
load_supply2_file()
load_supply3_file()
load_underground_list()
load_rough_list()
load_final_list()
load_templates_from_github()


# -------------------------------
# Routes for Main Functionality (Protected by login_required)
# -------------------------------

# Main Menu – note: the file upload functionality has been removed.
@app.route("/")
@login_required
def index():
    return render_template("index.html")  # A simple main menu template

@app.route("/view_all", methods=["GET"])
@login_required
def view_all():
    """View all content from the selected supply's Excel file."""
    supply = request.args.get("supply", "supply1")

    current_df = get_current_dataframe(supply)
    if current_df is None:
        flash("⚠ Please ensure the Excel file for the selected supply is available.")
        return redirect(url_for("index"))

    df_temp = current_df.copy()
    if "Date" in df_temp.columns:
        df_temp["Date"] = df_temp["Date"].dt.strftime("%Y-%m-%d")
    if "Date" in df_temp.columns and "Description" in df_temp.columns:
        date_index = list(df_temp.columns).index("Date")
        df_temp.insert(
            date_index + 1,
            "Graph",
            df_temp["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc, supply=supply, ref="view_all")}">Graph</a>'
            )
        )
        # Ensure column order is consistent
        desired_order = [
            "Item Number",
            "Description",
            "Price per Unit",
            "Unit",
            "Invoice No.",
            "Date",
            "Graph",
        ]
        existing_columns = [c for c in desired_order if c in df_temp.columns]
        df_temp = df_temp[existing_columns]
    table_html = df_temp.to_html(table_id="data-table", classes="table table-striped", index=False, escape=False)
    table_html = table_html.replace('<table ', '<table data-page-length="50" ')
    return render_template(
        "view_all.html",
        table=table_html,
        supply=supply,
    )

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """
    Search the selected supply’s 'Description' column for a query.
    """
    supply = request.args.get("supply", "supply1")
    page = request.args.get("page", 1, type=int)
    per_page = None
    current_df = get_current_dataframe(supply)
    if current_df is None:
        flash("⚠ Please ensure the Excel file for the selected supply is available.")
        return redirect(url_for("index"))
    
    results = None
    query = request.form.get("query") if request.method == "POST" else request.args.get("query", "")
    if request.method == "POST" or query:
        if request.method == "POST":
            supply = request.form.get("supply", "supply1")
            current_df = get_current_dataframe(supply)
        if not query:
            flash("⚠ Please enter a search term.")
        else:
            preprocessed_query = preprocess_text_for_search(query)
            keywords = preprocessed_query.split()
            results = current_df[current_df["Description"].apply(
                lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords)
            )]
            if results.empty:
                flash("⚠ No matching results found.")
    
    if results is not None and not results.empty:
        if supply == "all":
            page_df = results
            table_html = page_df.to_html(
                table_id="data-table", classes="table table-striped", index=False, escape=False
            )
            table_html = table_html.replace('<table ', '<table data-page-length="20" ')
            next_page = prev_page = None
        else:
            if "Date" in results.columns:
                results["Date"] = results["Date"].dt.strftime("%Y-%m-%d")
            if "Date" in results.columns and "Description" in results.columns:
                date_index = list(results.columns).index("Date")
                results.insert(
                    date_index + 1,
                    "Graph",
                    results["Description"].apply(
                        lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc, supply=supply, ref="search", query=query)}">Graph</a>'
                    ),
                )
                desired_order = [
                    "Item Number",
                    "Description",
                    "Price per Unit",
                    "Unit",
                    "Invoice No.",
                    "Date",
                    "Graph",
                ]
                existing_cols = [c for c in desired_order if c in results.columns]
                results = results[existing_cols]
            if per_page:
                page_df = du.paginate_dataframe(results, page, per_page)
            else:
                page_df = results
            table_html = page_df.to_html(
                table_id="data-table", classes="table table-striped", index=False, escape=False
            )
            table_html = table_html.replace('<table ', '<table data-page-length="20" ')
            next_page = page + 1 if per_page and len(results) > page * per_page else None
            prev_page = page - 1 if per_page and page > 1 else None
    else:
        table_html = None
        next_page = prev_page = None
    return render_template(
        "search.html",
        table=table_html,
        query=query,
        supply=supply,
        next_page=next_page,
        prev_page=prev_page,
        page=page,
    )


@app.route("/api/search", methods=["GET"])
@login_required
def api_search():
    supply = request.args.get("supply", "supply1")
    query = request.args.get("query", "")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", type=int)
    current_df = get_current_dataframe(supply)
    if current_df is None or not query:
        return jsonify({"data": [], "next_page": None, "prev_page": None})
    preprocessed_query = preprocess_text_for_search(query)
    keywords = preprocessed_query.split()
    results = current_df[current_df["Description"].apply(
        lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords)
    )]

    if supply != "all" and "Date" in results.columns and "Description" in results.columns:
        date_index = list(results.columns).index("Date")
        results = results.copy()
        results.insert(
            date_index + 1,
            "Graph",
            results["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc, supply=supply, ref="search", query=query)}">Graph</a>'
            ),
        )
        desired_order = [
            "Item Number",
            "Description",
            "Price per Unit",
            "Unit",
            "Invoice No.",
            "Date",
            "Graph",
        ]
        existing_cols = [c for c in desired_order if c in results.columns]
        results = results[existing_cols]
    if supply != "all" and "Date" in results.columns:
        results["Date"] = results["Date"].dt.strftime("%Y-%m-%d")

    if per_page:
        page_df = du.paginate_dataframe(results, page, per_page)
    else:
        page_df = results

    json_data = json.loads(page_df.to_json(orient="records"))
    next_page = page + 1 if per_page and len(results) > page * per_page else None
    prev_page = page - 1 if per_page and page > 1 else None
    return jsonify({"data": json_data, "next_page": next_page, "prev_page": prev_page})
    
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
    current_df = get_current_dataframe(supply)
    description = request.args.get("description")
    
    if current_df is None or not description:
        flash("⚠ Data or description not provided.")
        return redirect(url_for("index"))
    
    # Use a case-insensitive, trimmed partial match:
    filtered_data = current_df[current_df["Description"].str.lower().str.strip().str.contains(description.lower().strip(), na=False)]
    if filtered_data.empty:
        flash("⚠ No data available for the selected description.")
        return redirect(url_for("view_all", supply=supply))
    
    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(filtered_data["Date"], filtered_data["Price per Unit"], marker="o")
    ax.set_title(f"Prices Over Time for '{description}'")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price per Unit")
    ax.grid(True)
    
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.close(fig)
    output.seek(0)
    return send_file(output, mimetype="image/png")

@app.route("/graph_data")
@login_required
def graph_data():
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    description = request.args.get("description")
    if current_df is None or not description:
        return jsonify({"dates": [], "prices": []})
    filtered_data = current_df[current_df["Description"].str.lower().str.strip().str.contains(description.lower().strip(), na=False)]
    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    dates = filtered_data["Date"].dt.strftime("%Y-%m-%d").tolist()
    prices = filtered_data["Price per Unit"].tolist()
    return jsonify({"dates": dates, "prices": prices})

@app.route("/analyze", methods=["GET", "POST"])
@login_required
def analyze():
    """
    Analyze price changes for items across a custom date range from the selected supply.
    """
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    if current_df is None:
        flash("⚠ Please ensure the Excel file for the selected supply is available.")
        return redirect(url_for("index"))
    
    results = None
    if request.method == "POST":
        try:
            start_date = pd.to_datetime(request.form.get("start_date"))
            end_date = pd.to_datetime(request.form.get("end_date"))
            supply = request.form.get("supply", "supply1")
            current_df = get_current_dataframe(supply)
            filtered_data = current_df[(current_df["Date"] >= start_date) & (current_df["Date"] <= end_date)]
            
            if filtered_data.empty:
                flash("⚠ No items found within the selected date range.")
            else:
                grouped = filtered_data.groupby(["Description", filtered_data["Date"].dt.to_period("M")])
                result_records = []
                groups_keys = list(grouped.groups.keys())
                
                for (desc, month) in groups_keys:
                    group = grouped.get_group((desc, month))
                    avg_price = group["Price per Unit"].mean()
                    next_month = month + 1
                    if (desc, next_month) in grouped.groups:
                        next_group = grouped.get_group((desc, next_month))
                        next_avg_price = next_group["Price per Unit"].mean()
                        if avg_price != next_avg_price:
                            result_records.extend(group.to_dict("records"))
                            result_records.extend(next_group.to_dict("records"))
                
                if not result_records:
                    flash("⚠ No price changes found in the selected range.")
                else:
                    results = pd.DataFrame(result_records)
        except Exception as e:
            flash(f"❌ Error analyzing price changes: {e}")
    
    table_html = results.to_html(table_id="data-table", classes="table table-striped", index=False) if results is not None else None
    if table_html:
        table_html = table_html.replace('<table ', '<table data-page-length="20" ')
    return render_template("analyze.html", table=table_html, supply=supply)

@app.route("/product_detail", methods=["GET"])
@login_required
def product_detail():
    """
    Display a page for a specific product (from the selected supply) with:
      - A graph (rendered by the /graph endpoint)
      - A table with Date and Price per Unit for that product (sorted by Date).
    """
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    description = request.args.get("description")
    if current_df is None or not description:
        flash("⚠ Please provide a product description.")
        return redirect(url_for("index"))
    
    # Use case-insensitive, trimmed comparison for matching.
    filtered_data = current_df[current_df["Description"].str.lower().str.strip() == description.lower().strip()]
    if filtered_data.empty:
        flash("⚠ No data available for the selected product.")
        return redirect(url_for("view_all", supply=supply))
    
    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    if "Date" in filtered_data.columns:
        filtered_data["Date"] = filtered_data["Date"].dt.strftime("%Y-%m-%d")
    table_html = filtered_data[['Date', 'Price per Unit']].to_html(table_id="data-table", classes="table table-striped", index=False)
    table_html = table_html.replace('<table ', '<table data-page-length="20" ')
    ref = request.args.get("ref", "view_all")  # defaults to view_all if not provided
    query = request.args.get("query", "")       # Get the search query if available
    return render_template("product_detail.html", description=description, table=table_html, supply=supply, ref=ref, query=query)

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
            pdf_filename = f"order_summary_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
            with open(pdf_path, "wb") as f:
                f.write(pdf)
            session["pdf_path"] = pdf_path
        except Exception as e:
            flash(f"PDF generation failed: {e}", "danger")
            return redirect(url_for("material_list"))
        
        recipient = session.get("email")
        msg = Message("Your Order Summary", recipients=[recipient])
        msg.body = "Please find attached your order summary PDF."
        msg.attach("order_summary.pdf", "application/pdf", pdf)
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
            download_name="order_summary.pdf",
        )
    
    # For GET: load predetermined or saved templates
    list_option = request.args.get("list", "underground")
    load_templates_from_github()
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
            product_list.append(
                {
                    "Product Description": desc,
                    "Last Price": price,
                    "quantity": qty,
                    "Unit": unit,
                    "total": total,
                }
            )
    elif list_option_lower == "underground":
        update_underground_prices()
        product_list = du.df_underground.to_dict("records") if du.df_underground is not None else []
    elif list_option_lower == "rough":
        update_rough_prices()
        product_list = du.df_rough.to_dict("records") if du.df_rough is not None else []
    elif list_option_lower == "final":
        update_final_prices()
        product_list = du.df_final.to_dict("records") if du.df_final is not None else []
    elif list_option_lower == "new":
        product_list = []
    else:
        product_list = []

    supply1_products = du.df.to_dict("records") if du.df is not None else []
    supply2_products = du.df_supply2.to_dict("records") if du.df_supply2 is not None else []
    supply3_products = du.df_supply3.to_dict("records") if du.df_supply3 is not None else []
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
    return render_template(
        "material_list.html",
        product_list=product_list,
        list_option=list_option,
        custom_templates=list(custom_templates.keys()),
        template_folders=sorted(template_folders),
        supply1_products=supply1_products,
        supply2_products=supply2_products,
        supply3_products=supply3_products,
        template_name=template_name,
        template_folder=template_folder,
        full_template_name=full_template_name,
        project_info=project_info,
    )

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
    load_templates_from_github()
    templates_dir = config.TEMPLATE_DATA_DIR
    os.makedirs(templates_dir, exist_ok=True)
    sort_key = request.args.get("sort", "name")
    group_by = request.args.get("group", "none")
    entries = []
    for root, _, files in os.walk(templates_dir):
        for f in files:
            if f.endswith(".json"):
                path = os.path.join(root, f)
                rel_dir = os.path.relpath(root, templates_dir)
                group = "" if rel_dir == "." else rel_dir
                name = os.path.splitext(f)[0]
                full_name = os.path.join(group, name) if group else name
                entries.append({
                    "name": name,
                    "full_name": full_name,
                    "group": group,
                    "mtime": os.path.getmtime(path),
                })
    if sort_key == "date":
        entries.sort(key=lambda x: x["mtime"])
    else:
        entries.sort(key=lambda x: x["name"].lower())
    if group_by == "folder":
        grouped = {}
        for e in entries:
            grouped.setdefault(e["group"], []).append(e)
        return render_template(
            "templates_list.html",
            grouped_templates=grouped,
            sort_key=sort_key,
            group_by=group_by,
        )
    return render_template(
        "templates_list.html",
        template_entries=entries,
        sort_key=sort_key,
        group_by=group_by,
    )


@app.route("/edit_template/<path:name>")
@login_required
def edit_template(name):
    return redirect(url_for("material_list", list=name, template_name=name))


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
    load_templates_from_github()
    return redirect(url_for("templates_list"))


# -------------------------------
# Convert to Lion Route
# -------------------------------

@app.route("/convert_to_lion", methods=["GET", "POST"])
@login_required
def convert_to_lion():
    """Convert a supply list to Lion's catalog."""
    # Ensure we have the latest templates from GitHub
    load_templates_from_github()

    # Local Excel templates live under uploads/templates
    excel_templates_dir = os.path.join(app.config["UPLOAD_FOLDER"], "templates")
    os.makedirs(excel_templates_dir, exist_ok=True)
    excel_templates = [
        f for f in os.listdir(excel_templates_dir) if f.lower().endswith(".xlsx")
    ]

    # JSON templates (saved to GitHub) are stored under the configured data dir
    json_templates_dir = config.TEMPLATE_DATA_DIR
    os.makedirs(json_templates_dir, exist_ok=True)
    json_templates = []
    for root, _, files in os.walk(json_templates_dir):
        for f in files:
            if f.lower().endswith(".json"):
                rel_dir = os.path.relpath(root, json_templates_dir)
                name = os.path.splitext(f)[0]
                full_name = os.path.join(rel_dir, name) if rel_dir != "." else name
                json_templates.append(full_name)

    template_names = excel_templates + json_templates

    table_html = None
    download_filename: str | None = None
    download_pdf: str | None = None
    grand_total: float | None = None

    if request.method == "POST":
        uploaded_file = request.files.get("file")
        selected_template = request.form.get("template")
        product_data_json = request.form.get("product_data")
        supply_path = None

        if product_data_json:
            try:
                product_data = json.loads(product_data_json)
            except Exception as e:
                flash(f"Invalid product data: {e}", "danger")
                return redirect(url_for("material_list"))
            temp_df = pd.DataFrame(product_data)
            temp_df.rename(
                columns={
                    "description": "Description",
                    "Product Description": "Description",
                    "quantity": "Quantity",
                    "last_price": "Price per Unit",
                    "price": "Price",
                },
                inplace=True,
            )
            supply_path = os.path.join(
                app.config["UPLOAD_FOLDER"], f"{uuid.uuid4().hex}_from_material.xlsx"
            )
            temp_df.to_excel(supply_path, index=False)
        elif uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            supply_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            uploaded_file.save(supply_path)
        elif selected_template:
            if selected_template.lower().endswith(".json"):
                template_path = os.path.join(json_templates_dir, selected_template)
                try:
                    with open(template_path) as f:
                        template_data = json.load(f)
                    temp_df = pd.DataFrame(template_data)
                    temp_df.rename(
                        columns={
                            "description": "Description",
                            "quantity": "Quantity",
                            "last_price": "Price per Unit",
                            "price": "Price",
                        },
                        inplace=True,
                    )
                    supply_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], f"{uuid.uuid4().hex}_template.xlsx"
                    )
                    temp_df.to_excel(supply_path, index=False)
                except Exception as e:
                    flash(f"Error loading template: {e}", "danger")
                    return redirect(url_for("convert_to_lion"))
            else:
                supply_path = os.path.join(excel_templates_dir, selected_template)
        else:
            # Default to Supply 1 data if nothing was provided
            supply_path = config.DEFAULT_FILE

        lion_catalog = config.DEFAULT_SUPPLY3_FILE
        download_filename = f"lion_result_{uuid.uuid4().hex}.xlsx"
        output_path = os.path.join(app.config["UPLOAD_FOLDER"], download_filename)

        try:
            result_df = match_to_lion(supply_path, lion_catalog, output_path)
            grand_total = float(result_df["Total"].sum())
            table_html = (
                result_df.to_html(
                    table_id="data-table",
                    classes="table table-striped",
                    index=False,
                ).replace('<table ', '<table data-page-length="20" ')
            )

            # Generate PDF version of the results
            os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp")
            css_path = os.path.join(app.root_path, "static", "css", "order_summary.css")
            rendered_pdf = render_template(
                "lion_summary.html",
                rows=result_df.to_dict("records"),
                grand_total=grand_total,
                css_link=f"file://{css_path}",
            )
            import pdfkit
            try:
                options = {"enable-local-file-access": None}
                pdf_bytes = pdfkit.from_string(
                    rendered_pdf, False, options=options, css=css_path
                )
                download_pdf = f"lion_result_{uuid.uuid4().hex}.pdf"
                pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], download_pdf)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)
            except Exception as e:
                flash(f"PDF generation failed: {e}", "danger")
        except Exception as e:
            flash(f"Error converting file: {e}", "danger")

    return render_template(
        "convert_to_lion.html",
        templates=template_names,
        table=table_html,
        download_filename=download_filename,
        download_pdf=download_pdf,
        grand_total=grand_total,
    )


@app.route("/download_lion/<filename>")
@login_required
def download_lion(filename: str):
    """Send a previously generated Lion conversion workbook to the client."""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        flash("Requested file not found.", "warning")
        return redirect(url_for("convert_to_lion"))
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/download_lion_pdf/<filename>")
@login_required
def download_lion_pdf(filename: str):
    """Send a previously generated Lion conversion PDF to the client."""
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(filepath):
        flash("Requested file not found.", "warning")
        return redirect(url_for("convert_to_lion"))
    return send_file(filepath, as_attachment=True, download_name=filename)

# -------------------------------
# PDF Download Route
# -------------------------------

@app.route("/download_summary")
@login_required
def download_summary():
    """Return the last generated order summary PDF."""
    global pdf_buffer
    if pdf_buffer is not None:
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="order_summary.pdf",
        )
    pdf_path = session.get("pdf_path")
    if pdf_path and os.path.exists(pdf_path):
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="order_summary.pdf",
        )

    flash("No PDF available for download.", "warning")
    return redirect(url_for("material_list"))
# -------------------------------
# Login and Logout Routes
# -------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        code = request.form.get("code", "").strip()

        # Allow direct code-based login without requiring the email field.
        if code:
            if code == "7199":
                session["email"] = "zamoraplumbing01@gmail.com"
                session["last_activity"] = time.time()
                flash("Login successful!", "success")
                return redirect(url_for("index"))
            flash("Invalid code.", "danger")
            return redirect(url_for("login"))

        if email in ALLOWED_EMAILS:
            token = serializer.dumps(email, salt="email-confirmation")
            login_url = url_for("verify_login", token=token, _external=True)
            msg = Message("Your Login Link", recipients=[email])
            msg.body = f"Click the link to log in: {login_url}"
            try:
                mail.send(msg)
            except Exception as e:
                app.logger.error(f"Error sending email: {e}")
                flash("Error sending email. Please try again later.", "danger")
                return redirect(url_for("login"))
            flash("A login link has been sent to your email.", "info")
            return redirect(url_for("index"))
        else:
            flash("Unauthorized email.", "danger")
    return render_template("login.html")

@app.route("/verify_login/<token>")
def verify_login(token):
    try:
        email = serializer.loads(token, salt="email-confirmation", max_age=600)
        session["email"] = email
        session.permanent = True
        session["last_activity"] = time.time()
        flash("Login successful!", "success")
        return redirect(url_for("index"))
    except Exception as e:
        flash("Invalid or expired login link.", "danger")
        return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.pop("email", None)
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# -------------------------------
# Run the Application
# -------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
