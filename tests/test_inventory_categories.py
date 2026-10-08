"""Category tree under each location panel on the Inventory page.

The dashboard already returns a `category` (Grocy product group) per row;
the page groups rows by it inside each storage bucket, e.g.
Frozen -> Meat -> items, Poultry -> items. Empty groups read as
Uncategorized. Groups sort A-Z, items keep the panel sort, everything
starts collapsed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SERVICE = Path(__file__).resolve().parents[1] / "service"
sys.path.insert(0, str(SERVICE))

from app.config import settings  # noqa: E402
from app.services.grocy import GrocyClient  # noqa: E402


@pytest.fixture
def client(monkeypatch, tmp_path):
    cwd = os.getcwd()
    os.chdir(SERVICE)
    monkeypatch.setattr(settings, "data_dir", str(tmp_path), raising=False)
    monkeypatch.setattr(settings, "auth_required", False, raising=False)
    monkeypatch.setattr(settings, "grocy_base_url", "http://grocy.test", raising=False)
    monkeypatch.setattr(settings, "grocy_api_key", "test-key", raising=False)
    from fastapi.testclient import TestClient
    from app.main import app
    try:
        yield TestClient(app)
    finally:
        os.chdir(cwd)


def test_dashboard_preserves_category_per_row(client):
    """Contract the tree relies on: rows keep their Grocy product group."""
    async def fake_full_stock(self):
        return [
            {"product_id": 1, "name": "Item 1", "amount": 2.0,
             "days_remaining": 5, "storage_bucket": "frozen",
             "category": "Meat", "amount_opened": 0.0},
            {"product_id": 2, "name": "Item 3", "amount": 1.0,
             "days_remaining": 5, "storage_bucket": "frozen",
             "category": "", "amount_opened": 0.0},
        ]

    with patch.object(GrocyClient, "get_full_stock", fake_full_stock):
        r = client.get("/inventory/dashboard")
    assert r.status_code == 200
    rows = {i["name"]: i for i in r.json()["frozen"]}
    assert rows["Item 1"]["category"] == "Meat"
    assert rows["Item 3"]["category"] == ""


def test_inventory_page_groups_rows_by_category(client):
    """The page script must group each panel by category, collapsed by
    default, with an Uncategorized fallback for empty groups."""
    with patch.object(type(settings), "is_configured", lambda self: True):
        r = client.get("/ui/inventory")
    assert r.status_code == 200
    assert "Uncategorized" in r.text
    assert "data-category" in r.text
    assert "inv_cat_collapsed" in r.text
