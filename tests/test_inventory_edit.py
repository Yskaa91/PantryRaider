"""Rename a product from the Inventory page edit modal.

PATCH /inventory/edit/{id} accepts a name alongside category/best-by;
the modal carries a Name field prefilled with the current name.
Blank names are ignored, never written.
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


def test_edit_endpoint_passes_name_through(client):
    seen = {}

    async def fake_edit(self, product_id, category=None,
                        best_before_date=None, name=None):
        seen.update(product_id=product_id, category=category,
                    best_before_date=best_before_date, name=name)
        return {"product_id": product_id}

    with patch.object(GrocyClient, "edit_product", fake_edit):
        r = client.patch("/inventory/edit/7", json={"name": "Oat Milk"})
    assert r.status_code == 200
    assert seen == {"product_id": 7, "category": None,
                    "best_before_date": None, "name": "Oat Milk"}


def test_edit_endpoint_ignores_blank_name(client):
    seen = {}

    async def fake_edit(self, product_id, category=None,
                        best_before_date=None, name=None):
        seen["name"] = name
        return {"product_id": product_id}

    with patch.object(GrocyClient, "edit_product", fake_edit):
        r = client.patch("/inventory/edit/7", json={"name": "   "})
    assert r.status_code == 200
    assert seen["name"] is None


def test_edit_modal_carries_name_field(client):
    with patch.object(type(settings), "is_configured", lambda self: True):
        r = client.get("/ui/inventory")
    assert r.status_code == 200
    assert 'id="editName"' in r.text
