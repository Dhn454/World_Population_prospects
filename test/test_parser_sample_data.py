import pandas as pd
from io import BytesIO

def test_load_population_data_with_mock(monkeypatch):
    """
    Use a mock DataFrame to simulate Excel parsing.
    """
    # Mock DataFrame
    data = {"Location": ["World"], "Year": [2022], "PopTotal": [7900]}
    mock_df = pd.DataFrame(data)

    # Patch pd.read_excel to return mock_df instead
    monkeypatch.setattr("src.parser.pd.read_excel", lambda *args, **kwargs: mock_df)

    from src.parser import load_population_data
    result = load_population_data("fakefile.xlsx")

    assert result[0]["PopTotal"] == 7900
