from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Load Excel File
df = pd.read_excel("inventory.xlsx")  # Ensure you have an inventory.xlsx file

@app.route("/")
def home():
    return render_template("index.html", table=df.to_html(classes="table"))

@app.route("/search", methods=["POST"])
def search():
    query = request.form["query"]
    results = df[df["Description"].str.contains(query, case=False, na=False)]
    return render_template("index.html", table=results.to_html(classes="table"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
