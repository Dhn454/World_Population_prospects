# src/parser.py
import pandas as pd
from typing import List, Dict

def load_population_data(filepath: str) -> List[Dict]:
    """
    Loads population data from the UN WPP XLSX file.

    Parameters:
    - filepath (str): Path to the Excel file.

    Returns:
    - List[Dict]: Parsed records in list-of-dictionaries format.
    """
    df = pd.read_excel(filepath, sheet_name="Data", engine="openpyxl")
    return df.to_dict(orient="records")
