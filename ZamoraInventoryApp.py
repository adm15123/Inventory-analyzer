<<<<<<< HEAD
from flask import Flask, render_template, request, jsonify
import pandas as pd
import re
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

df = None  # Global DataFrame

def allowed_file(filename):
    """Check if file is an allowed type."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_text_for_search(text):
    """Preprocess the text temporarily by removing special characters and converting to lowercase."""
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(text)).lower()

@app.route("/")
def home():
    """Render the main page."""
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload."""
    global df
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        try:
            df = pd.read_excel(file_path)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            return jsonify({"message": "File uploaded successfully!", "filename": filename}), 200
        except Exception as e:
            return jsonify({"error": f"Failed to process Excel file: {e}"}), 500

    return jsonify({"error": "Invalid file type"}), 400

@app.route("/search", methods=["GET"])
def search_description():
    """Search the description column for matches."""
    global df
    if df is None:
        return jsonify({"error": "No file uploaded"}), 400

    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    try:
        preprocessed_query = preprocess_text_for_search(query)
        keywords = preprocessed_query.split()

        results = df[
            df["Description"].apply(lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords))
        ]

        return results.to_json(orient="records"), 200
    except Exception as e:
        return jsonify({"error": f"Failed to search: {e}"}), 500

@app.route("/view_all", methods=["GET"])
def view_all_content():
    """Return all rows from the Excel file."""
    global df
    if df is None:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        return df.to_json(orient="records"), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load all content: {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
=======
import io
import re
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file
)
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flash messages

# Global variable to hold the uploaded DataFrame
df = None

def preprocess_text_for_search(text):
    """Remove special characters and convert text to lowercase."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Landing page: Upload an Excel file and navigate to other features.
    """
    global df
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No file selected")
            return redirect(request.url)
        try:
            # Read the Excel file into a DataFrame
            df = pd.read_excel(file)
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            flash("Excel file loaded successfully!")
            return redirect(url_for('view_all'))
        except Exception as e:
            flash(f"Error loading file: {e}")
            return redirect(request.url)
    return render_template('index.html')

@app.route('/view_all')
def view_all():
    """
    View all content in the uploaded Excel file.
    """
    global df
    if df is None:
        flash("Please upload an Excel file first.")
        return redirect(url_for('index'))
    # Convert the DataFrame to an HTML table
    table_html = df.to_html(classes='table table-striped', index=False)
    return render_template('view_all.html', table=table_html)

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Search the DataFrame’s 'Description' column for a query.
    """
    global df
    if df is None:
        flash("Please upload an Excel file first.")
        return redirect(url_for('index'))
    
    results = None
    query = ''
    if request.method == 'POST':
        query = request.form.get('query')
        if not query:
            flash("Please enter a search term.")
        else:
            preprocessed_query = preprocess_text_for_search(query)
            keywords = preprocessed_query.split()
            # Filter rows where every keyword appears in the description
            results = df[df['Description'].apply(
                lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords)
            )]
            if results.empty:
                flash("No matching results found.")
    table_html = results.to_html(classes='table table-striped', index=False) if results is not None else None
    return render_template('search.html', table=table_html, query=query)

@app.route('/graph')
def graph():
    """
    Generate a graph of Price per Unit over time for a given description.
    The description is passed as a query parameter.
    """
    global df
    description = request.args.get('description')
    if df is None or not description:
        flash("Data or description not provided.")
        return redirect(url_for('index'))
    
    # Filter data for the selected description
    filtered_data = df[df['Description'] == description]
    if filtered_data.empty:
        flash("No data available for the selected description.")
        return redirect(url_for('view_all'))
    
    filtered_data = filtered_data.dropna(subset=['Date']).sort_values(by='Date')
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(filtered_data['Date'], filtered_data['Price per Unit'], marker='o')
    ax.set_title(f"Prices Over Time for '{description}'")
    ax.set_xlabel("Date")
    ax.set_ylabel("Price per Unit")
    ax.grid(True)
    
    # Save plot to a BytesIO object and return as PNG
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    plt.close(fig)
    output.seek(0)
    return send_file(output, mimetype='image/png')

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    """
    Analyze price changes for items across a custom date range.
    """
    global df
    results = None
    if df is None:
        flash("Please upload an Excel file first.")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            start_date = pd.to_datetime(request.form.get('start_date'))
            end_date = pd.to_datetime(request.form.get('end_date'))
            filtered_data = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            if filtered_data.empty:
                flash("No items found within the selected date range.")
            else:
                # Group by Description and Month (as a period) and compare monthly averages
                grouped = filtered_data.groupby(['Description', filtered_data['Date'].dt.to_period('M')])
                result_records = []
                groups_keys = list(grouped.groups.keys())
                for (desc, month) in groups_keys:
                    group = grouped.get_group((desc, month))
                    avg_price = group['Price per Unit'].mean()
                    next_month = month + 1
                    if (desc, next_month) in grouped.groups:
                        next_group = grouped.get_group((desc, next_month))
                        next_avg_price = next_group['Price per Unit'].mean()
                        if avg_price != next_avg_price:
                            result_records.extend(group.to_dict('records'))
                            result_records.extend(next_group.to_dict('records'))
                if not result_records:
                    flash("No price changes found in the selected range.")
                else:
                    results = pd.DataFrame(result_records)
        except Exception as e:
            flash(f"Error analyzing price changes: {e}")
    
    table_html = results.to_html(classes='table table-striped', index=False) if results is not None else None
    return render_template('analyze.html', table=table_html)

if __name__ == '__main__':
    app.run(debug=True)
>>>>>>> a5b8c81 (Initial commit - Upload ZamoraInventoryAnalyzer)
