import pytest
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ZamoraInventoryApp import preprocess_text_for_search

def test_preprocess_text_for_search():
    assert preprocess_text_for_search('Hello World!') == 'hello world'
    assert preprocess_text_for_search('123-ABC') == '123abc'
    assert preprocess_text_for_search('Spaces   and\tTabs') == 'spaces   and\ttabs'
