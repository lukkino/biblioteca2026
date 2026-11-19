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
from backend import auth  # noqa: E402
from tests.fake_appwrite import FakeAuth, FakeTablesDB  # noqa: E402

FAKE = FakeTablesDB()
FAKE.load_sqlite("db_tre", "Online", TMP / "uno.db3")
appwrite_client._tables = FAKE

AUTH = FakeAuth()
AUTH.add_user("maria@example.com", "password-giusta", "Maria")
AUTH.add_user("estraneo@example.com", "password-giusta", "Estraneo", labels=())
appwrite_client.login = AUTH.login
appwrite_client.user_for_session = AUTH.user_for_session
appwrite_client.logout = AUTH.logout

c = TestClient(app)  # client con accesso fatto, usato dai test sui libri
assert c.post("/api/auth/login", json={"email": "maria@example.com", "password": "password-giusta"}).status_code == 200
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


@pytest.fixture
def anon():
    auth._fails.clear()
    yield TestClient(app)
    auth._fails.clear()


def test_senza_login_niente_dati(anon):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/auth/me").status_code == 401
    for url in ["/api/biblioteche", f"{SQL}/libri", f"{AW}/libri", f"{AW}/libri/72", f"{AW}/stats", f"{AW}/generi"]:
        assert anon.get(url).status_code == 401, url
    assert anon.post(f"{AW}/libri", json={"titolo": "x"}).status_code == 401
    assert anon.delete(f"{AW}/libri/72").status_code == 401
    assert anon.patch("/api/biblioteche/uno", json={"nome": "x"}).status_code == 401
    # cookie inventato
    anon.cookies.set(auth.COOKIE, "inventato")
    assert anon.get(f"{AW}/libri").status_code == 401


def test_login_e_logout(anon):
    r = anon.post("/api/auth/login", json={"email": " Maria@Example.com ", "password": "password-giusta"})
    assert r.status_code == 200 and r.json() == {"name": "Maria", "email": "maria@example.com"}
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert anon.get("/api/auth/me").json()["name"] == "Maria"
    assert anon.get(f"{AW}/stats").status_code == 200
    assert anon.post("/api/auth/logout").status_code == 204
    assert anon.get(f"{AW}/stats").status_code == 401
    assert anon.post("/api/auth/logout").status_code == 204  # di nuovo: nessun errore


def test_login_sbagliato(anon):
    r = anon.post("/api/auth/login", json={"email": "maria@example.com", "password": "sbagliata"})
    assert r.status_code == 401 and "password" in r.json()["detail"]
    r = anon.post("/api/auth/login", json={"email": "nessuno@example.com", "password": "x"})
    assert r.status_code == 401
    # utente del progetto ma senza l'etichetta "biblioteca": non entra
    r = anon.post("/api/auth/login", json={"email": "estraneo@example.com", "password": "password-giusta"})
    assert r.status_code == 403
    assert not any(u["email"] == "estraneo@example.com" for u in AUTH.sessions.values())  # sessione chiusa


def test_errore_configurazione_non_e_password_errata(anon, monkeypatch):
    from appwrite.exception import AppwriteException

    def senza_permessi(*a):
        raise AppwriteException("missing scopes", 401, "general_unauthorized_scope")

    monkeypatch.setattr(appwrite_client, "login", senza_permessi)
    r = anon.post("/api/auth/login", json={"email": "maria@example.com", "password": "password-giusta"})
    assert r.status_code == 503
    assert not any(auth._fails.values())  # non conta come tentativo sbagliato


def test_troppi_tentativi(anon):
    for _ in range(auth.MAX_FAILS_EMAIL):
        assert anon.post("/api/auth/login", json={"email": "maria@example.com", "password": "no"}).status_code == 401
    # ora anche la password giusta è bloccata per un po'
    r = anon.post("/api/auth/login", json={"email": "maria@example.com", "password": "password-giusta"})
    assert r.status_code == 429


def test_sessione_revocata(anon):
    anon.post("/api/auth/login", json={"email": "maria@example.com", "password": "password-giusta"})
    AUTH.sessions.clear()        # es. sessione eliminata dalla console Appwrite
    auth._sessions.clear()       # (scaduta anche la cache del backend)
    assert anon.get(f"{AW}/stats").status_code == 401
    # il client principale deve rientrare per i test successivi
    assert c.post("/api/auth/login", json={"email": "maria@example.com", "password": "password-giusta"}).status_code == 200


@pytest.mark.skipif(not (ROOT / "frontend" / "dist" / "index.html").is_file(), reason="frontend non compilato")
def test_sito_servito_dal_backend(anon):
    r = anon.get("/")
    assert r.status_code == 200 and '<div id="root">' in r.text and r.headers["cache-control"] == "no-cache"
    assert anon.get("/qualsiasi/pagina").text == r.text            # le pagine dell'app tornano index.html
    asset = next((ROOT / "frontend" / "dist" / "assets").glob("*.js")).name
    assert anon.get(f"/assets/{asset}").status_code == 200
    assert anon.get("/api/inesistente").status_code == 404          # le API sbagliate restano 404
    assert anon.get("/../.env").status_code in (200, 404) and "APPWRITE" not in anon.get("/../.env").text
    assert anon.get("/%2e%2e/%2e%2e/.env").text == r.text           # niente file fuori da dist


def test_no_wal():
    # il vecchio programma richiede il journal classico: l'app non deve attivare WAL
    c.get(f"{SQL}/libri")
    with open(TMP / "uno.db3", "rb") as f:
        assert f.read(20)[18] == 1
