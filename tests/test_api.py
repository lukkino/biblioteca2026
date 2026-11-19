import os, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tmp = Path(tempfile.mkdtemp()) / "test.db3"
shutil.copy(ROOT / "Biblioteca.db3", tmp)
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}"

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402

c = TestClient(app)


def test_list_and_stats():
    s = c.get("/api/stats").json()
    assert s["totale_libri"] == 6463
    r = c.get("/api/libri", params={"page_size": 10}).json()
    assert r["total"] == 6463 and len(r["items"]) == 10


def test_search():
    r = c.get("/api/libri", params={"q": "flatlandia"}).json()
    assert any(b["titolo"] == "Flatlandia" for b in r["items"])
    r2 = c.get("/api/libri", params={"q": "abbott flatlandia"}).json()
    assert r2["total"] >= 1
    g = c.get("/api/libri", params={"genere_id": -1}).json()
    assert g["total"] == 121


def test_crud():
    r = c.post("/api/libri", json={"titolo": "  Test Libro ", "autore": "Rossi Mario", "genere_id": 13})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["titolo"] == "Test Libro" and b["genere"] == "Romanzi"
    r = c.put(f"/api/libri/{b['id']}", json={**b, "anno": "2026", "genere_id": 7})
    assert r.json()["anno"] == "2026"
    assert c.post("/api/libri", json={"titolo": ""}).status_code == 422
    assert c.post("/api/libri", json={"titolo": "x", "genere_id": 999}).status_code == 422
    assert c.delete(f"/api/libri/{b['id']}").status_code == 204
    assert c.get(f"/api/libri/{b['id']}").status_code == 404
