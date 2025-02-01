from flask import Flask, render_template, request, jsonify
import pandas as pd
import re
import os

app = Flask(__name__)

df = None  # Global dataframe variable

def preprocess_text_for_search(text):
    """Preprocess the text by removing special characters and converting to lowercase."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and store in DataFrame."""
    global df
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        df = pd.read_excel(file)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {e}"}), 500

@app.route('/search', methods=['GET'])
def search_description():
    """Search for a description in the dataset."""
    global df
    if df is None:
        return jsonify({"error": "No file loaded"}), 400

    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({"error": "Search query is empty"}), 400

    try:
        preprocessed_query = preprocess_text_for_search(query)
        keywords = preprocessed_query.split()
        results = df[df['Description'].apply(lambda desc: all(
            keyword in preprocess_text_for_search(desc) for keyword in keywords
        ))]

        return results.to_json(orient='records')
    except Exception as e:
        return jsonify({"error": f"Failed to search: {e}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
