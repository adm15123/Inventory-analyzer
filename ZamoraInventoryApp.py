from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
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
@@ -320,69 +320,108 @@ def graph():
    
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
    """Return JSON data for interactive graphing."""
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    description = request.args.get("description")
    if current_df is None or not description:
        return jsonify({"error": "Invalid request"}), 400

    filtered_data = current_df[current_df["Description"].str.lower().str.strip().str.contains(description.lower().strip(), na=False)]
    if filtered_data.empty:
        return jsonify({"error": "No data"}), 404

    filtered_data = filtered_data.dropna(subset=["Date"]).sort_values(by="Date")
    data = {
        "dates": filtered_data["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "prices": filtered_data["Price per Unit"].tolist(),
    }
    return jsonify(data)

@app.route("/autocomplete")
@login_required
def autocomplete():
    term = request.args.get("term", "").lower()
    supply = request.args.get("supply", "supply1")
    current_df = get_current_dataframe(supply)
    suggestions = []
    if current_df is not None and term:
        try:
            descriptions = current_df["Description"].dropna().astype(str)
            suggestions = descriptions[descriptions.str.lower().str.contains(term)].unique().tolist()[:10]
        except Exception:
            suggestions = []
    return jsonify(suggestions)

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
            if start_date > end_date:
                flash("Start date must be before end date.", "danger")
                return redirect(url_for("analyze", supply=supply))
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
@@ -411,50 +450,57 @@ def product_detail():
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
    global df_underground, df_rough, df_final, df
    if request.method == "POST":
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

        if not contractor or not address or not order_date:
            flash("All project information fields are required.", "danger")
            return redirect(url_for("material_list"))
        if not product_data:
            flash("Please add at least one product.", "danger")
            return redirect(url_for("material_list"))
        
        # Retrieve include_price choice from the form:
        include_price = request.form.get("include_price", "yes")
        
        total_cost = sum(float(item.get("total", 0)) for item in product_data)
        
        # Pass the include_price flag to the order summary template:
        rendered = render_template("order_summary.html",
                                   contractor=contractor,
                                   address=address,
                                   order_date=order_date,
                                   products=product_data,
                                   total_cost=total_cost,
                                   include_price=include_price)
        import pdfkit
        try:
            pdf = pdfkit.from_string(rendered, False)
        except Exception as e:
            flash(f"PDF generation failed: {e}", "danger")
            return redirect(url_for("material_list"))
        
        recipient = session.get("email")
        msg = Message("Your Order Summary", recipients=[recipient])
        msg.body = "Please find attached your order summary PDF."
        msg.attach("order_summary.pdf", "application/pdf", pdf)
