import pandas as pd
import os
from typing import Optional
from config import (
    DEFAULT_FILE,
    DEFAULT_SUPPLY2_FILE,
    DEFAULT_SUPPLY3_FILE,
    UPLOAD_FOLDER,
)
# Global DataFrames
df: Optional[pd.DataFrame] = None
df_supply2: Optional[pd.DataFrame] = None
df_supply3: Optional[pd.DataFrame] = None
df_underground: Optional[pd.DataFrame] = None
df_rough: Optional[pd.DataFrame] = None
df_final: Optional[pd.DataFrame] = None


def preprocess_text_for_search(text: str) -> str:
    """Preprocess text by removing special characters and converting to lowercase."""
    import re
    return re.sub(r"[^a-zA-Z0-9\s]", "", str(text)).lower()


def load_default_file():
    global df
    if os.path.exists(DEFAULT_FILE):
        df = pd.read_excel(DEFAULT_FILE, engine="openpyxl")
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        if "Description" in df.columns:
            df["Description"] = df["Description"].astype(str).str.strip()
        if "Price per Unit" in df.columns:
            df["Price per Unit"] = pd.to_numeric(
                df["Price per Unit"].astype(str).str.replace(',', '', regex=False),
                errors="coerce",
            )


def load_supply2_file():
    global df_supply2
    if os.path.exists(DEFAULT_SUPPLY2_FILE):
        df_supply2 = pd.read_excel(DEFAULT_SUPPLY2_FILE, engine="openpyxl")
        if "Date" in df_supply2.columns:
            df_supply2["Date"] = pd.to_datetime(df_supply2["Date"], errors="coerce")
        if "Description" in df_supply2.columns:
            df_supply2["Description"] = df_supply2["Description"].astype(str).str.strip()
        if "Price per Unit" in df_supply2.columns:
            df_supply2["Price per Unit"] = pd.to_numeric(
                df_supply2["Price per Unit"].astype(str).str.replace(',', '', regex=False),
                errors="coerce",
            )


def load_supply3_file():
    global df_supply3
    if os.path.exists(DEFAULT_SUPPLY3_FILE):
        df_supply3 = pd.read_excel(DEFAULT_SUPPLY3_FILE, engine="openpyxl")
        if "Date" in df_supply3.columns:
            df_supply3["Date"] = pd.to_datetime(df_supply3["Date"], errors="coerce")
        if "Description" in df_supply3.columns:
            df_supply3["Description"] = df_supply3["Description"].astype(str).str.strip()
        if "Price per Unit" in df_supply3.columns:
            df_supply3["Price per Unit"] = pd.to_numeric(
                df_supply3["Price per Unit"].astype(str).str.replace(',', '', regex=False),
                errors="coerce",
            )


def load_predetermined_list(filename: str) -> Optional[pd.DataFrame]:
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        df_list = pd.read_excel(file_path, engine="openpyxl")
        if "Product Description" in df_list.columns:
            df_list["Product Description"] = df_list["Product Description"].astype(str).str.strip()
        return df_list
    return None


def load_underground_list():
    global df_underground
    df_underground = load_predetermined_list("underground_list.xlsx")


def load_rough_list():
    global df_rough
    df_rough = load_predetermined_list("rough_list.xlsx")


def load_final_list():
    global df_final
    df_final = load_predetermined_list("final_list.xlsx")


def get_current_dataframe(supply: str) -> Optional[pd.DataFrame]:
    if supply == "supply2":
        return df_supply2
    if supply == "supply3":
        return df_supply3
    return df


def update_list_prices(df_list: Optional[pd.DataFrame]):
    global df
    if df_list is not None and df is not None:
        last_prices = (
            df.groupby(df["Description"].str.lower().str.strip())["Price per Unit"].max()
        )
        df_list["Last Price"] = (
            df_list["Product Description"].str.lower().str.strip().map(last_prices).fillna(0)
        )


def update_underground_prices():
    global df_underground
    update_list_prices(df_underground)


def update_rough_prices():
    global df_rough
    update_list_prices(df_rough)


def update_final_prices():
    global df_final
    update_list_prices(df_final)


def paginate_dataframe(data: pd.DataFrame, page: int, per_page: int) -> pd.DataFrame:
    start = (page - 1) * per_page
    end = start + per_page
    return data.iloc[start:end]
