from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import re
import os
import io
import matplotlib.pyplot as plt
from werkzeug.utils import secure_filename
from datetime import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# Set the base directory to the directory of this file
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secure flash messages

# Allowed file extension for uploads
ALLOWED_EXTENSIONS = {"xlsx"}

# Define the upload folder (absolute path)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global DataFrame variable
df = None

# Define the default Excel file name and its path within the uploads folder
EXCEL_FILENAME = "Final_Extracted_Data_Fixed_Logic4.xlsx"
DEFAULT_FILE = os.path.join(UPLOAD_FOLDER, EXCEL_FILENAME)

def allowed_file(filename):
    """Check if the uploaded file is an allowed type (.xlsx)."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_text_for_search(text):
    """Preprocess text by removing special characters and converting to lowercase."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(text)).lower()

def load_default_file():
    """Load the default Excel file from the uploads folder on startup."""
    global df
    if os.path.exists(DEFAULT_FILE):
        try:
            df = pd.read_excel(DEFAULT_FILE, engine="openpyxl")
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            print("✅ Default file loaded successfully!")
        except Exception as e:
            print(f"❌ Error loading default file: {e}")
    else:
        print("⚠ No default Excel file found in the uploads folder. Please upload a file.")

# Attempt to load the default file when the app starts
load_default_file()

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Landing page: Upload an Excel file and navigate to other features.
    (Renamed from 'home' to 'index' so that template calls to url_for("index") work.)
    """
    global df
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            try:
                file.save(file_path)
            except Exception as e:
                flash(f"❌ Error saving file: {e}")
                return redirect(request.url)

            try:
                df = pd.read_excel(file_path, engine="openpyxl")
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                flash("✅ Excel file loaded successfully!")
                return redirect(url_for("view_all"))
            except Exception as e:
                flash(f"❌ Error loading file: {e}")
                return redirect(request.url)
        else:
            flash("File type not allowed. Please upload a .xlsx file.")
            return redirect(request.url)
    return render_template("index.html")

@app.route("/view_all", methods=["GET"])
def view_all():
    """View all content in the uploaded Excel file with a clickable 'Graph' box next to each row."""
    global df
    if df is None:
        flash("⚠ Please upload an Excel file first.")
        return redirect(url_for("index"))
    
    # Create a copy of the DataFrame so we don't modify the global df
    df_temp = df.copy()
    
    # If the columns 'Date' and 'Description' exist, insert a new column "Graph"
    if "Date" in df_temp.columns and "Description" in df_temp.columns:
        date_index = list(df_temp.columns).index("Date")
        df_temp.insert(
            date_index + 1,
            "Graph",
            df_temp["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc)}">Graph</a>'
            )
        )
    
    # Generate the HTML table. Use escape=False so that HTML in the "Graph" column is rendered.
    table_html = df_temp.to_html(classes="table table-striped", index=False, escape=False)
    return render_template("view_all.html", table=table_html)

@app.route("/search", methods=["GET", "POST"])
def search():
    """Search the DataFrame’s 'Description' column for a query and include a Graph column."""
    global df
    if df is None:
        flash("⚠ Please upload an Excel file first.")
        return redirect(url_for("index"))
    
    results = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query")
        if not query:
            flash("⚠ Please enter a search term.")
        else:
            preprocessed_query = preprocess_text_for_search(query)
            keywords = preprocessed_query.split()
            results = df[df["Description"].apply(
                lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords)
            )]
            if results.empty:
                flash("⚠ No matching results found.")
    
    if results is not None and not results.empty:
        # Insert a Graph column right after the Date column
        if "Date" in results.columns and "Description" in results.columns:
            date_index = list(results.columns).index("Date")
            results.insert(date_index + 1, "Graph", results["Description"].apply(
                lambda desc: f'<a class="btn btn-secondary" href="{url_for("product_detail", description=desc)}">Graph</a>'
            ))
        table_html = results.to_html(classes="table table-striped", index=False, escape=False)
    else:
        table_html = None
    return render_template("search.html", table=table_html, query=query)

@app.route("/graph")
def graph():
    """Generate a graph of Price per Unit over time for a given description."""
    global df
    description = request.args.get("description")
    
    if df is None or not description:
        flash("⚠ Data or description not provided.")
        return redirect(url_for("index"))
    
    filtered_data = df[df["Description"] == description]
    if filtered_data.empty:
        flash("⚠ No data available for the selected description.")
        return redirect(url_for("view_all"))
    
    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(filtered_data["Date"], filtered_data["Price per Unit"], marker="o")
    ax.set_title(f"Prices Over Time for '{description}'")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price per Unit")
    ax.grid(True)
    
    # Save the plot to a BytesIO object and return it as PNG
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.close(fig)
    output.seek(0)
    return send_file(output, mimetype="image/png")

@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Analyze price changes for items across a custom date range."""
    global df
    results = None
    if df is None:
        flash("⚠ Please upload an Excel file first.")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        try:
            start_date = pd.to_datetime(request.form.get("start_date"))
            end_date = pd.to_datetime(request.form.get("end_date"))
            filtered_data = df[(df["Date"] >= start_date) & (df["Date"] <= end_date)]
            
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
    return render_template("analyze.html", table=table_html)

@app.route("/product_detail", methods=["GET"])
def product_detail():
    """
    Displays a page for a specific product with:
      - A graph (rendered by the /graph endpoint)
      - A table with Date and Price per Unit for that product (sorted by Date).
    """
    global df
    description = request.args.get("description")
    if df is None or not description:
        flash("⚠ Please provide a product description.")
        return redirect(url_for("index"))
    
    filtered_data = df[df["Description"] == description]
    if filtered_data.empty:
        flash("⚠ No data available for the selected product.")
        return redirect(url_for("view_all"))
    
    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    # Create an HTML table for Date and Price per Unit columns
    table_html = filtered_data[['Date', 'Price per Unit']].to_html(classes="table table-striped", index=False)
    return render_template("product_detail.html", description=description, table=table_html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
