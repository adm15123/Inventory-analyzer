from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import pandas as pd
import re
import os
import io
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import time
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Additional imports for login functionality
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from functools import wraps

# -------------------------------
# Application Configuration
# -------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.secret_key = "your_secret_key"

# Session Timeout Configuration
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

# Allowed file extension (not used for upload anymore)
ALLOWED_EXTENSIONS = {"xlsx"}

# Define the upload folder (used only for reading pre‑uploaded files)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define filenames and paths for both supplies
EXCEL_FILENAME = "Final_Extracted_Data_Fixed_Logic4.xlsx"  # Supply 1 file
DEFAULT_FILE = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)

SUPPLY2_FILENAME = "Supply2.xlsx"  # Supply 2 file
DEFAULT_SUPPLY2_FILE = os.path.join(UPLOAD_FOLDER, SUPPLY2_FILENAME)

# Global DataFrames for each supply
df = None         # Data for supply 1
df_supply2 = None # Data for supply 2
df_underground = None # Data for the underground list
df_rough = None   # Rough list
df_final = None   # Final list
# -------------------------------
# Flask-Mail and Login Configuration
# -------------------------------

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
# Utility Functions
# -------------------------------

def preprocess_text_for_search(text):
    """Preprocess text by removing special characters and converting to lowercase."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(text)).lower()

def load_default_file():
    """Load the default Excel file (Supply 1) from the uploads folder on startup."""
    global df
    if os.path.exists(DEFAULT_FILE):
        try:
            df = pd.read_excel(DEFAULT_FILE, engine="openpyxl")
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            if "Description" in df.columns:
                df["Description"] = df["Description"].astype(str).str.strip()
            if "Price per Unit" in df.columns:
                df["Price per Unit"] = pd.to_numeric(
                    df["Price per Unit"].astype(str).str.replace(',', '', regex=False),
                 errors='coerce'
                 )
            print("✅ Default supply1 file loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading supply1 file: {e}")
    else:
        print("⚠ No default supply1 file found in the uploads folder.")

def load_supply2_file():
    """Load the Supply 2 Excel file from the uploads folder on startup."""
    global df_supply2
    if os.path.exists(DEFAULT_SUPPLY2_FILE):
        try:
            df_supply2 = pd.read_excel(DEFAULT_SUPPLY2_FILE, engine="openpyxl")
            if "Date" in df_supply2.columns:
                df_supply2["Date"] = pd.to_datetime(df_supply2["Date"], errors="coerce")
            if "Description" in df_supply2.columns:
                df_supply2["Description"] = df_supply2["Description"].astype(str).str.strip()
            if "Price per Unit" in df_supply2.columns:
                df_supply2["Price per Unit"] = pd.to_numeric(
                    df_supply2["Price per Unit"].astype(str).str.replace(',', '', regex=False),
                 errors='coerce' 
                 )
            print("✅ Default supply2 file loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading supply2 file: {e}")
    else:
        print("⚠ No default supply2 file found in the uploads folder.")

def load_underground_list():
    """Load the predetermined product list from the uploads folder."""
    global df_underground
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "underground_list.xlsx")
    if os.path.exists(file_path):
        try:
            df_underground = pd.read_excel(file_path, engine="openpyxl")
            # Ensure the column "Product Description" exists and is cleaned.
            if "Product Description" in df_underground.columns:
                df_underground["Product Description"] = df_underground["Product Description"].astype(str).str.strip()
            print("✅ Underground list loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading underground list: {e}")
    else:
        print("⚠ No underground list found in the uploads folder.")

def load_rough_list():
    global df_rough
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "rough_list.xlsx")
    if os.path.exists(file_path):
        try:
            df_rough = pd.read_excel(file_path, engine="openpyxl")
            if "Product Description" in df_rough.columns:
                df_rough["Product Description"] = df_rough["Product Description"].astype(str).str.strip()
            print("✅ Rough list loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading rough list: {e}")
    else:
        print("⚠ No rough list found in the uploads folder.")

def load_final_list():
    global df_final
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], "final_list.xlsx")
    if os.path.exists(file_path):
        try:
            df_final = pd.read_excel(file_path, engine="openpyxl")
            if "Product Description" in df_final.columns:
                df_final["Product Description"] = df_final["Product Description"].astype(str).str.strip()
            print("✅ Final list loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading final list: {e}")
    else:
        print("⚠ No final list found in the uploads folder.")
# Load both files on startup
load_default_file()
load_supply2_file()
load_underground_list()
load_rough_list()
load_final_list()

def get_current_dataframe(supply):
    """Return the DataFrame for the specified supply."""
    if supply == "supply2":
        return df_supply2
    else:
        return df

def update_list_prices(df_list):
    global df
    if df_list is not None and df is not None:
        def get_last_price(desc):
            matches = df[df["Description"].astype(str).str.lower().str.strip() == desc.lower().strip()]
            return matches["Price per Unit"].max() if not matches.empty else 0
        df_list["Last Price"] = df_list["Product Description"].apply(get_last_price)

def update_underground_prices():
    global df_underground
    update_list_prices(df_underground)

def update_rough_prices():
    global df_rough
    update_list_prices(df_rough)

def update_final_prices():
    global df_final
    update_list_prices(df_final)


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
    if "Date" in df_temp.columns and "Description" in df_temp.columns:
        date_index = list(df_temp.columns).index("Date")
        df_temp.insert(
            date_index + 1,
            "Graph",
            df_temp["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc, supply=supply, ref="view_all")}">Graph</a>'
            )
        )
    table_html = df_temp.to_html(classes="table table-striped", index=False, escape=False)
    return render_template("view_all.html", table=table_html, supply=supply)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """
    Search the selected supply’s 'Description' column for a query.
    """
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    if current_df is None:
        flash("⚠ Please ensure the Excel file for the selected supply is available.")
        return redirect(url_for("index"))
    
    results = None
    query = ""
    if request.method == "POST":
        supply = request.form.get("supply", "supply1")
        current_df = get_current_dataframe(supply)
        query = request.form.get("query")
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
        if "Date" in results.columns and "Description" in results.columns:
            date_index = list(results.columns).index("Date")
            results.insert(date_index + 1, "Graph", results["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc, supply=supply, ref="search", query=query)}">Graph</a>'
            ))
        table_html = results.to_html(classes="table table-striped", index=False, escape=False)
    else:
        table_html = None
    return render_template("search.html", table=table_html, query=query, supply=supply)

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
    
    table_html = results.to_html(classes="table table-striped", index=False) if results is not None else None
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
    table_html = filtered_data[['Date', 'Price per Unit']].to_html(classes="table table-striped", index=False)
    ref = request.args.get("ref", "view_all")  # defaults to view_all if not provided
    query = request.args.get("query", "")       # Get the search query if available
    return render_template("product_detail.html", description=description, table=table_html, supply=supply, ref=ref, query=query)

@app.route("/material_list", methods=["GET", "POST"])
@login_required
def material_list():
    global df_underground, df_rough, df_final
    if request.method == "POST":
        # Process the submitted order:
        contractor = request.form.get("contractor")
        address = request.form.get("address")
        order_date = request.form.get("date")
        import json
        product_data_json = request.form.get("product_data")
        try:
            product_data = json.loads(product_data_json) if product_data_json else []
        except Exception as e:
            flash("Error processing product data.", "danger")
            return redirect(url_for("material_list"))
        
        # Calculate total cost from product_data (each item should have quantity and last_price)
        total_cost = sum(float(item.get("total", 0)) for item in product_data)
        
        # Render an order summary HTML template for PDF generation
        rendered = render_template("order_summary.html",
                                   contractor=contractor,
                                   address=address,
                                   order_date=order_date,
                                   products=product_data,
                                   total_cost=total_cost)
        import pdfkit
        try:
            pdf = pdfkit.from_string(rendered, False)
        except Exception as e:
            flash(f"PDF generation failed: {e}", "danger")
            return redirect(url_for("material_list"))
        
        # Email the PDF to the logged-in user
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
    
    # For GET: Determine which predetermined list to load based on a query parameter "list"
    list_option = request.args.get("list", "underground").lower()
    if list_option == "underground":
        update_underground_prices()
        product_list = df_underground.to_dict('records') if df_underground is not None else []
    elif list_option == "rough":
        update_rough_prices()
        product_list = df_rough.to_dict('records') if df_rough is not None else []
    elif list_option == "final":
        update_final_prices()
        product_list = df_final.to_dict('records') if df_final is not None else []
    elif list_option == "new":
        product_list = []  # start with an empty list
    else:
        product_list = []  # default to empty if unknown option
    
    # Pass the chosen option to the template so the UI can reflect the current selection.
    return render_template("material_list.html", product_list=product_list, list_option=list_option)

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
