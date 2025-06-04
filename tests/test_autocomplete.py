import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ZamoraInventoryApp import app


def test_autocomplete_endpoint():
    client = app.test_client()
    resp = client.get('/autocomplete?term=a')
    assert resp.status_code == 302 or resp.status_code == 200
