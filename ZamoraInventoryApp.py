from flask import Flask
import pandas as pd
import re
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "Zamora Inventory Analyzer is Running!"

def preprocess_text_for_search(text):
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

def load_excel():
    global df
    file_path = filedialog.askopenfilename(
        title="Select an Excel File",
        filetypes=(("Excel Files", "*.xlsx"), ("All Files", "*.*"))
    )
    if not file_path:
        return
    try:
        df = pd.read_excel(file_path)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        messagebox.showinfo("Success", "Excel file loaded successfully!")
    except Exception as e:
        df = None
        messagebox.showerror("Error", f"Failed to load Excel file: {e}")

def search_description(event=None):
    if df is None:
        messagebox.showwarning("Data Error", "Please load an Excel file first.")
        return
    query = search_box.get()
    if not query:
        messagebox.showwarning("Input Error", "Please enter a search term.")
        return
    try:
        preprocessed_query = preprocess_text_for_search(query)
        keywords = preprocessed_query.split()
        results = df[df['Description'].apply(lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords))]
        for row in tree.get_children():
            tree.delete(row)
        for _, row in results.iterrows():
            tree.insert("", "end", values=row.tolist())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to search: {e}")

def view_all_content():
    if df is None:
        messagebox.showwarning("Data Error", "Please load an Excel file first.")
        return
    try:
        for row in tree.get_children():
            tree.delete(row)
        for _, row in df.iterrows():
            tree.insert("", "end", values=row.tolist())
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load all content: {e}")

# Initialize the Tkinter GUI
if __name__ == "__main__":
    tk_app = tk.Tk()
    tk_app.title("Zamora Plumbing Corp Material Analyzer")
    tk_app.geometry("1200x800")
    
    load_button = tk.Button(tk_app, text="Load Excel File", command=load_excel)
    load_button.pack(pady=10)
    
    search_frame = tk.Frame(tk_app)
    search_frame.pack(pady=10)
    search_label = tk.Label(search_frame, text="Search Description:")
    search_label.pack(side=tk.LEFT, padx=5)
    search_box = tk.Entry(search_frame, width=60)
    search_box.pack(side=tk.LEFT, padx=5)
    search_button = tk.Button(search_frame, text="Search", command=search_description)
    search_button.pack(side=tk.LEFT, padx=5)
    search_box.bind("<Return>", search_description)
    
    view_all_button = tk.Button(tk_app, text="View All Content", command=view_all_content)
    view_all_button.pack(pady=10)
    
    results_frame = tk.Frame(tk_app)
    results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    columns = ["Item Number", "Description", "Price per Unit", "Unit", "Invoice No.", "Date"]
    tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=20, yscrollcommand=scrollbar.set)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="w")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=tree.yview)
    
    df = None
    
    tk_app.mainloop()
    
    app.run(host='0.0.0.0', port=10000)
