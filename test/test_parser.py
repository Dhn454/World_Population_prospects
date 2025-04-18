# test/test_parser.py
import os
import pytest
from src.parser import load_population_data

def test_load_population_data():
    """
    Test that the parser loads and returns structured data.
    """
    test_file = "data/WPP2022_Demographic_Indicators.xlsx"

    if not os.path.exists(test_file):
        pytest.skip("Data file not present")

    result = load_population_data(test_file)

    assert isinstance(result, list), "Data should be a list of dictionaries"
    assert isinstance(result[0], dict), "Each row should be a dictionary"
    assert "Location" in result[0], "Each dict should contain a 'Location' key"
