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
