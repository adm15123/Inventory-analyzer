import pandas as pd
import re
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

def preprocess_text_for_search(text):
    """Preprocess the text temporarily by removing special characters and converting to lowercase."""
    return re.sub(r'[^a-zA-Z0-9\s]', '', str(text)).lower()

def load_excel():
    """Load the Excel file manually via a file dialog."""
    global df
    file_path = filedialog.askopenfilename(
        title="Select an Excel File",
        filetypes=(("Excel Files", "*.xlsx"), ("All Files", "*.*"))
    )
    if not file_path:
        return

    try:
        df = pd.read_excel(file_path)
        # Ensure the Date column is converted to datetime
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        messagebox.showinfo("Success", "Excel file loaded successfully!")
    except Exception as e:
        df = None
        messagebox.showerror("Error", f"Failed to load Excel file: {e}")

def search_description(event=None):
    """Search the description column for matches and display results."""
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

        results = df[
            df['Description'].apply(
                lambda desc: all(keyword in preprocess_text_for_search(desc) for keyword in keywords)
            )
        ]

        for row in tree.get_children():
            tree.delete(row)

        for _, row in results.iterrows():
            tree.insert("", "end", values=row.tolist())

    except Exception as e:
        messagebox.showerror("Error", f"Failed to search: {e}")

def view_all_content():
    """Load all rows from the Excel file into the table."""
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

def on_mouse_scroll(event):
    """Custom mouse scrolling to make it faster."""
    if event.delta > 0:  # Scroll up
        tree.yview_scroll(-3, "units")
    else:  # Scroll down
        tree.yview_scroll(3, "units")

def copy_to_clipboard(event=None):
    """Copy the selected description to the clipboard without showing a notification."""
    selected_item = tree.focus()  # Get the currently selected item
    if not selected_item:
        return  # Do nothing if no row is selected

    values = tree.item(selected_item, 'values')
    if values:
        description = values[1]  # Assuming the description is the second column
        app.clipboard_clear()
        app.clipboard_append(description)
        app.update()

def graph_description_prices():
    """Graph prices for all items with the same description."""
    selected_item = tree.focus()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select a row first.")
        return

    values = tree.item(selected_item, 'values')
    if not values:
        return

    description = values[1]  # Assuming the description is the second column

    try:
        filtered_data = df[df['Description'] == description]
        if filtered_data.empty:
            messagebox.showinfo("No Data", "No data available for the selected description.")
            return

        filtered_data = filtered_data.dropna(subset=['Date'])
        filtered_data = filtered_data.sort_values(by='Date')

        # Create a new window for the graph and table
        graph_table_window = tk.Toplevel(app)
        graph_table_window.title(f"Prices and Data for '{description}'")
        graph_table_window.geometry("1200x600")

        # Create a frame for the graph
        graph_frame = tk.Frame(graph_table_window)
        graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Plot the graph
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(filtered_data['Date'], filtered_data['Price per Unit'], marker='o')
        ax.set_title(f"Prices Over Time for '{description}'", fontsize=14)
        ax.set_xlabel("Date", fontsize=12)
        ax.set_ylabel("Price per Unit", fontsize=12)
        ax.grid()

        canvas = FigureCanvasTkAgg(fig, master=graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Create a frame for the table
        table_frame = tk.Frame(graph_table_window)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        table_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        table_tree = ttk.Treeview(table_frame, columns=['Date', 'Price per Unit'], show='headings', yscrollcommand=table_scrollbar.set)
        table_tree.heading('Date', text='Date')
        table_tree.heading('Price per Unit', text='Price per Unit')
        table_tree.column('Date', anchor='w', width=200)
        table_tree.column('Price per Unit', anchor='w', width=200)

        for _, row in filtered_data.iterrows():
            table_tree.insert('', 'end', values=(row['Date'].strftime('%Y-%m-%d'), row['Price per Unit']))

        table_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        table_scrollbar.config(command=table_tree.yview)

    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate graph: {e}")

def analyze_price_changes():
    """Analyze price changes for items across a custom date range."""
    if df is None:
        messagebox.showwarning("Data Error", "Please load an Excel file first.")
        return

    def search_by_date():
        try:
            start_date = pd.to_datetime(start_date_entry.get_date())
            end_date = pd.to_datetime(end_date_entry.get_date())

            filtered_data = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

            if filtered_data.empty:
                messagebox.showinfo("No Data", "No items found within the selected date range.")
                return

            grouped = filtered_data.groupby(['Description', filtered_data['Date'].dt.to_period('M')])
            result = []

            for (desc, month), group in grouped:
                avg_price = group['Price per Unit'].mean()
                for next_month in grouped.groups.keys():
                    if next_month[0] == desc and next_month[1] == month + 1:
                        next_group = grouped.get_group(next_month)
                        next_avg_price = next_group['Price per Unit'].mean()
                        if avg_price != next_avg_price:
                            result.extend(group.to_dict('records'))
                            result.extend(next_group.to_dict('records'))

            if not result:
                messagebox.showinfo("No Price Changes", "No items found with price changes in the selected range.")
                return

            # Display results in a new window
            result_window = tk.Toplevel(compare_window)
            result_window.title("Price Change Analysis")
            result_window.geometry("800x600")

            result_tree = ttk.Treeview(result_window, columns=['Description', 'Date', 'Price per Unit', 'Invoice No.'], show='headings')
            result_tree.heading('Description', text='Description')
            result_tree.heading('Date', text='Date')
            result_tree.heading('Price per Unit', text='Price per Unit')
            result_tree.heading('Invoice No.', text='Invoice No.')

            for item in result:
                result_tree.insert('', 'end', values=(item['Description'], item['Date'].strftime('%Y-%m-%d'), item['Price per Unit'], item['Invoice No.']))

            result_tree.pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to analyze price changes: {e}")

    compare_window = tk.Toplevel(app)
    compare_window.title("Compare Items by Date Range")
    compare_window.geometry("400x200")

    tk.Label(compare_window, text="Start Date:").pack(pady=5)
    start_date_entry = DateEntry(compare_window, width=12, background='darkblue', foreground='white', borderwidth=2)
    start_date_entry.pack(pady=5)

    tk.Label(compare_window, text="End Date:").pack(pady=5)
    end_date_entry = DateEntry(compare_window, width=12, background='darkblue', foreground='white', borderwidth=2)
    end_date_entry.pack(pady=5)

    search_button = tk.Button(compare_window, text="Search", command=search_by_date)
    search_button.pack(pady=10)

def show_context_menu(event):
    """Show the right-click context menu."""
    context_menu.post(event.x_root, event.y_root)

# Initialize the app
app = tk.Tk()
app.title("Zamora Plumbing Corp Material Analyzer")
app.geometry("1200x800")  # Set a larger window size

font_settings = ("Arial", 14)

# Load Button
load_button = tk.Button(app, text="Load Excel File", command=load_excel, font=font_settings)
load_button.pack(pady=10)

# Search Box
search_frame = tk.Frame(app)
search_frame.pack(pady=10)

search_label = tk.Label(search_frame, text="Search Description:", font=font_settings)
search_label.pack(side=tk.LEFT, padx=5)

search_box = tk.Entry(search_frame, font=font_settings, width=60)  # Wider search box
search_box.pack(side=tk.LEFT, padx=5)

search_button = tk.Button(search_frame, text="Search", command=search_description, font=font_settings)
search_button.pack(side=tk.LEFT, padx=5)

search_box.bind("<Return>", search_description)

# View All Content Button (Always Visible)
view_all_button = tk.Button(app, text="View All Content", command=view_all_content, font=font_settings)
view_all_button.pack(pady=10)

# Analyze Price Changes Button
analyze_button = tk.Button(app, text="Analyze Price Changes", command=analyze_price_changes, font=font_settings)
analyze_button.pack(pady=10)

# Results Frame
results_frame = tk.Frame(app)
results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Scrollbar for Treeview
scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Results Table
columns = ["Item Number", "Description", "Price per Unit", "Unit", "Invoice No.", "Date"]
tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=20, yscrollcommand=scrollbar.set)

style = ttk.Style()
style.configure("Treeview.Heading", font=("Arial", 14))
style.configure("Treeview", font=("Arial", 12))

column_widths = {
    "Item Number": 120,
    "Description": 400,
    "Price per Unit": 120,
    "Unit": 100,
    "Invoice No.": 120,
    "Date": 120,
}
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=column_widths[col], anchor="w")

tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=tree.yview)

# Bind mouse scroll to the Treeview
tree.bind("<MouseWheel>", on_mouse_scroll)

# Context Menu for Copy and Graph
context_menu = tk.Menu(app, tearoff=0)
context_menu.add_command(label="Copy Description", command=copy_to_clipboard)
context_menu.add_command(label="Graph Prices", command=graph_description_prices)

# Bind right-click to the Treeview
tree.bind("<Button-3>", show_context_menu)

# Global variables
df = None

# Run the app
app.mainloop()
