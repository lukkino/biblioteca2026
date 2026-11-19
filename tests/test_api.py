import json, os, shutil, tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp())
shutil.copy(ROOT / "Biblioteca.db3", TMP / "uno.db3")
CONFIG = TMP / "biblioteche.json"
CONFIG.write_text(json.dumps([
    {"id": "uno", "nome": "Casa", "file": str(TMP / "uno.db3")},
    {"id": "due", "nome": "Parrocchia", "file": str(TMP / "manca.db3")},
    {"id": "tre", "nome": "Online", "appwrite": "db_tre"},
]), encoding="utf-8")
os.environ["BIBLIOTECHE_CONFIG"] = str(CONFIG)
# credenziali finte: i test non devono mai parlare con l'Appwrite vero
os.environ.update(APPWRITE_ENDPOINT="http://appwrite.invalid/v1", APPWRITE_PROJECT_ID="test", APPWRITE_API_KEY="test")

from fastapi.testclient import TestClient  # noqa: E402
from backend import appwrite_client, database  # noqa: E402
from backend.main import app  # noqa: E402
from backend.store_appwrite import reset_stores  # noqa: E402
from tests.fake_appwrite import FakeTablesDB  # noqa: E402

FAKE = FakeTablesDB()
FAKE.load_sqlite("db_tre", "Online", TMP / "uno.db3")
appwrite_client._tables = FAKE

c = TestClient(app)
SQL, AW = "/api/b/uno", "/api/b/tre"
BOTH = pytest.mark.parametrize("B", [SQL, AW], ids=["sqlite", "appwrite"])


@BOTH
def test_list_and_stats(B):
    s = c.get(f"{B}/stats").json()
    assert s["totale_libri"] == 6463
    r = c.get(f"{B}/libri", params={"page_size": 10}).json()
    assert r["total"] == 6463 and len(r["items"]) == 10


@BOTH
def test_search(B):
    r = c.get(f"{B}/libri", params={"q": "flatlandia"}).json()
    assert any(b["titolo"] == "Flatlandia" for b in r["items"])
    r2 = c.get(f"{B}/libri", params={"q": "abbott flatlandia"}).json()
    assert r2["total"] >= 1
    g = c.get(f"{B}/libri", params={"genere_id": -1}).json()
    assert g["total"] == 121


@BOTH
def test_crud(B):
    r = c.post(f"{B}/libri", json={"titolo": "  Test Libro ", "autore": "Rossi Mario", "genere_id": 13})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["titolo"] == "Test Libro" and b["genere"] == "Romanzi"
    assert c.get(f"{B}/libri", params={"q": "test libro rossi"}).json()["total"] == 1
    r = c.put(f"{B}/libri/{b['id']}", json={**b, "anno": "2026", "genere_id": 7})
    assert r.json()["anno"] == "2026"
    assert c.get(f"{B}/libri/{b['id']}").json()["genere_id"] == 7
    assert c.post(f"{B}/libri", json={"titolo": ""}).status_code == 422
    assert c.post(f"{B}/libri", json={"titolo": "x", "genere_id": 999}).status_code == 422
    assert c.put(f"{B}/libri/999999", json={"titolo": "x"}).status_code == 404
    assert c.delete(f"{B}/libri/{b['id']}").status_code == 204
    assert c.get(f"{B}/libri/{b['id']}").status_code == 404
    assert c.delete(f"{B}/libri/{b['id']}").status_code == 404
    assert c.get(f"{B}/stats").json()["totale_libri"] == 6463


def test_crud_scrive_su_appwrite():
    b = c.post(f"{AW}/libri", json={"titolo": "Solo online", "genere_id": 13}).json()
    row = FAKE.rows[("db_tre", "libri")][str(b["id"])]
    assert row["titolo"] == "Solo online" and row["libro_id"] == b["id"]
    c.put(f"{AW}/libri/{b['id']}", json={"titolo": "Solo online 2"})
    assert row["titolo"] == "Solo online 2" and row["genere_id"] is None
    c.delete(f"{AW}/libri/{b['id']}")
    assert str(b["id"]) not in FAKE.rows[("db_tre", "libri")]


@pytest.mark.parametrize("sort", ["titolo", "autore", "editore", "anno", "codice", "collocazione", "genere", "id"])
@pytest.mark.parametrize("order", ["asc", "desc"])
def test_stessi_risultati_sqlite_e_appwrite(sort, order):
    # Appwrite (in memoria, Python) deve restituire esattamente le stesse pagine di SQLite
    for params in ({}, {"q": "il"}, {"q": "mondadori 19"}, {"genere_id": 13}, {"genere_id": -1}, {"anno": "1990"}):
        p = {**params, "sort": sort, "order": order, "page_size": 200, "page": 2}
        a, b = c.get(f"{SQL}/libri", params=p).json(), c.get(f"{AW}/libri", params=p).json()
        assert a == b, (params, sort, order)


def test_stessi_generi_e_stats():
    assert c.get(f"{SQL}/generi").json() == c.get(f"{AW}/generi").json()
    assert c.get(f"{SQL}/stats").json() == c.get(f"{AW}/stats").json()


def test_biblioteche():
    lst = c.get("/api/biblioteche").json()
    assert [(x["id"], x["disponibile"], x["totale_libri"]) for x in lst] == [
        ("uno", True, 6463), ("due", False, None), ("tre", True, 6463)]
    assert lst[2]["sorgente"] == "Appwrite"
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


def test_elenco_da_appwrite(monkeypatch):
    # senza biblioteche.json le biblioteche sono i database del progetto Appwrite
    monkeypatch.setenv("BIBLIOTECHE_CONFIG", str(TMP / "non-esiste.json"))
    monkeypatch.setattr(appwrite_client, "_databases", None)
    assert database.sorgente_elenco() == "appwrite"
    lst = c.get("/api/biblioteche").json()
    assert [(x["id"], x["nome"], x["totale_libri"]) for x in lst] == [("db_tre", "Online", 6463)]
    assert c.get("/api/b/db_tre/stats").json()["totale_libri"] == 6463
    r = c.patch("/api/biblioteche/db_tre", json={"nome": "Parrocchia"})
    assert r.status_code == 200 and r.json()["nome"] == "Parrocchia"
    assert FAKE.databases["db_tre"] == "Parrocchia"  # rinomina salvata su Appwrite
    FAKE.databases["db_tre"] = "Online"
    monkeypatch.setattr(appwrite_client, "_databases", None)


def test_appwrite_non_risponde(monkeypatch):
    from appwrite.exception import AppwriteException

    def guasto(*a, **k):
        raise AppwriteException("Server Error", 500)

    reset_stores()
    monkeypatch.setattr(FAKE, "list_rows", guasto)
    r = c.get(f"{AW}/libri")
    assert r.status_code == 503 and "Appwrite" in r.json()["detail"]
    tre = next(x for x in c.get("/api/biblioteche").json() if x["id"] == "tre")
    assert tre["disponibile"] is False
    monkeypatch.undo()
    reset_stores()
    assert c.get(f"{AW}/libri").status_code == 200


def test_no_wal():
    # il vecchio programma richiede il journal classico: l'app non deve attivare WAL
    c.get(f"{SQL}/libri")
    with open(TMP / "uno.db3", "rb") as f:
        assert f.read(20)[18] == 1
