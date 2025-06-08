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

app.config["MAIL_SERVER"] = config.MAIL_SERVER
app.config["MAIL_PORT"] = config.MAIL_PORT
app.config["MAIL_USE_TLS"] = config.MAIL_USE_TLS
app.config["MAIL_USERNAME"] = config.MAIL_USERNAME
app.config["MAIL_PASSWORD"] = config.MAIL_PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = config.MAIL_DEFAULT_SENDER

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
ALLOWED_EMAILS = config.ALLOWED_EMAILS

# Buffer to temporarily store generated order summary PDFs
pdf_buffer: io.BytesIO | None = None

# -------------------------------
# Global Before-Request Handler (Session Timeout)
# -------------------------------

@app.before_request
def check_session_timeout():
    # Skip timeout check for login, verification, and static assets.
    if request.endpoint in ('login', 'verify_login', 'static'):
        return

    if "email" in session:
        last_activity = session.get("last_activity", time.time())
        if time.time() - last_activity > 1800:  # 30 minutes inactivity
            session.pop("email", None)
            flash("Session expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for("login"))
        session["last_activity"] = time.time()

# -------------------------------
# Login Helper Functions
# -------------------------------

def is_logged_in():
    if "email" in session:
        last_activity = session.get("last_activity", time.time())
        if time.time() - last_activity > 1800:
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

    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    os.makedirs(templates_dir, exist_ok=True)

    api_url = f"https://api.github.com/repos/{repo}/contents/templates"
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
        table_html = page_df.to_html(table_id="data-table", classes="table table-striped", index=False, escape=False)
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

    if "Date" in results.columns and "Description" in results.columns:
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
    if "Date" in results.columns:
        results["Date"] = results["Date"].dt.strftime("%Y-%m-%d")

    if per_page:
        page_df = du.paginate_dataframe(results, page, per_page)
    else:
        page_df = results

    json_data = json.loads(page_df.to_json(orient="records"))
    next_page = page + 1 if per_page and len(results) > page * per_page else None
    prev_page = page - 1 if per_page and page > 1 else None
    return jsonify({"data": json_data, "next_page": next_page, "prev_page": prev_page})

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
        )
        import pdfkit
        try:
            pdf = pdfkit.from_string(rendered, False)
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
        return redirect(url_for("material_list"))
    
    # For GET: load predetermined or saved templates
    list_option = request.args.get("list", "underground")
    load_templates_from_github()
    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    custom_templates = {}
    for fname in os.listdir(templates_dir):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(templates_dir, fname)) as f:
                    custom_templates[os.path.splitext(fname)[0]] = json.load(f)
            except Exception:
                pass
    list_option_lower = list_option.lower()
    if list_option in custom_templates:
        raw_list = custom_templates[list_option]
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
            product_list.append(
                {
                    "Product Description": desc,
                    "Last Price": price,
                    "quantity": qty,
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
    template_name = request.args.get("template_name", "")
    if not template_name and list_option_lower not in ["underground", "rough", "final", "new"]:
        template_name = list_option
    return render_template(
        "material_list.html",
        product_list=product_list,
        list_option=list_option,
        custom_templates=list(custom_templates.keys()),
        supply1_products=supply1_products,
        supply2_products=supply2_products,
        template_name=template_name,
    )

@app.route("/save_template", methods=["POST"])
@login_required
def save_template():
    template_name = request.form.get("template_name")
    product_data = request.form.get("product_data")
    if not template_name or not product_data:
        flash("Template name and data are required.", "danger")
        return redirect(url_for("material_list"))
    filename = f"templates/{template_name}.json"
    # Save locally
    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    try:
        with open(os.path.join(templates_dir, f"{template_name}.json"), "w") as f:
            f.write(product_data)
    except Exception as e:
        app.logger.error(f"Local template save failed: {e}")

    success = save_template_to_github(filename, product_data)
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
    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    os.makedirs(templates_dir, exist_ok=True)
    names = [os.path.splitext(f)[0] for f in os.listdir(templates_dir) if f.endswith(".json")]
    return render_template("templates_list.html", template_names=names)


@app.route("/edit_template/<name>")
@login_required
def edit_template(name):
    return redirect(url_for("material_list", list=name, template_name=name))


@app.route("/delete_template/<name>", methods=["POST"])
@login_required
def delete_template(name):
    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    filepath = os.path.join(templates_dir, f"{name}.json")
    if os.path.exists(filepath):
        os.remove(filepath)
    delete_template_from_github(f"templates/{name}.json")
    flash("Template deleted.", "info")
    return redirect(request.referrer or url_for("templates_list"))


@app.route("/rename_template/<name>", methods=["POST"])
@login_required
def rename_template(name):
    new_name = request.form.get("new_name")
    if not new_name:
        flash("New name required.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    templates_dir = os.path.join(config.UPLOAD_FOLDER, "templates")
    old_path = os.path.join(templates_dir, f"{name}.json")
    new_path = os.path.join(templates_dir, f"{new_name}.json")
    if not os.path.exists(old_path):
        flash("Template not found.", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    try:
        with open(old_path) as f:
            content = f.read()
        os.rename(old_path, new_path)
    except Exception as e:
        flash(f"Rename failed: {e}", "danger")
        return redirect(request.referrer or url_for("templates_list"))
    success = save_template_to_github(f"templates/{new_name}.json", content)
    if success:
        delete_template_from_github(f"templates/{name}.json")
        flash("Template renamed.", "success")
    else:
        flash("Failed to update GitHub.", "danger")
    load_templates_from_github()
    return redirect(url_for("templates_list"))

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
        email = request.form.get("email")
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
