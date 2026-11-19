import json, os, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp())
shutil.copy(ROOT / "Biblioteca.db3", TMP / "uno.db3")
CONFIG = TMP / "biblioteche.json"
CONFIG.write_text(json.dumps([
    {"id": "uno", "nome": "Casa", "file": str(TMP / "uno.db3")},
    {"id": "due", "nome": "Parrocchia", "file": str(TMP / "manca.db3")},
]), encoding="utf-8")
os.environ["BIBLIOTECHE_CONFIG"] = str(CONFIG)

from fastapi.testclient import TestClient  # noqa: E402
from backend.main import app  # noqa: E402

c = TestClient(app)
B = "/api/b/uno"


def test_list_and_stats():
    s = c.get(f"{B}/stats").json()
    assert s["totale_libri"] == 6463
    r = c.get(f"{B}/libri", params={"page_size": 10}).json()
    assert r["total"] == 6463 and len(r["items"]) == 10


def test_search():
    r = c.get(f"{B}/libri", params={"q": "flatlandia"}).json()
    assert any(b["titolo"] == "Flatlandia" for b in r["items"])
    r2 = c.get(f"{B}/libri", params={"q": "abbott flatlandia"}).json()
    assert r2["total"] >= 1
    g = c.get(f"{B}/libri", params={"genere_id": -1}).json()
    assert g["total"] == 121


def test_crud():
    r = c.post(f"{B}/libri", json={"titolo": "  Test Libro ", "autore": "Rossi Mario", "genere_id": 13})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["titolo"] == "Test Libro" and b["genere"] == "Romanzi"
    r = c.put(f"{B}/libri/{b['id']}", json={**b, "anno": "2026", "genere_id": 7})
    assert r.json()["anno"] == "2026"
    assert c.post(f"{B}/libri", json={"titolo": ""}).status_code == 422
    assert c.post(f"{B}/libri", json={"titolo": "x", "genere_id": 999}).status_code == 422
    assert c.delete(f"{B}/libri/{b['id']}").status_code == 204
    assert c.get(f"{B}/libri/{b['id']}").status_code == 404


def test_biblioteche():
    lst = c.get("/api/biblioteche").json()
    assert [(x["id"], x["disponibile"], x["totale_libri"]) for x in lst] == [("uno", True, 6463), ("due", False, None)]
    # biblioteca senza file: errore chiaro e il file NON viene creato
    r = c.get("/api/b/due/libri")
    assert r.status_code == 503 and "Parrocchia" in r.json()["detail"]
    assert not (TMP / "manca.db3").exists()
    assert c.get("/api/b/inesistente/libri").status_code == 404


def test_rename():
    r = c.patch("/api/biblioteche/uno", json={"nome": "  Casa Mamma "})
    assert r.status_code == 200 and r.json()["nome"] == "Casa Mamma"
    assert json.loads(CONFIG.read_text(encoding="utf-8"))[0]["nome"] == "Casa Mamma"
    assert c.patch("/api/biblioteche/uno", json={"nome": "parrocchia"}).status_code == 422  # duplicato
    assert c.patch("/api/biblioteche/uno", json={"nome": "  "}).status_code == 422
    c.patch("/api/biblioteche/uno", json={"nome": "Casa"})


def test_no_wal():
    # il vecchio programma richiede il journal classico: l'app non deve attivare WAL
    c.get(f"{B}/libri")
    with open(TMP / "uno.db3", "rb") as f:
        assert f.read(20)[18] == 1
