# backend/appwrite_client.py
"""Collegamento ad Appwrite (TablesDB).

Configurazione in .env (o nelle variabili d'ambiente del server):
    APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY

Ogni biblioteca è un database Appwrite con le tabelle "libri" e "generi"
(creati da scripts/migra_appwrite.py). Il nome del database è il nome della biblioteca.
"""
from __future__ import annotations

import os
import threading
import time

from appwrite.client import Client
from appwrite.query import Query
from appwrite.services.account import Account
from appwrite.services.tables_db import TablesDB

ENV = ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY")
DATABASES_TTL = 60  # secondi: l'elenco delle biblioteche cambia di rado

_lock = threading.Lock()
_tables: TablesDB | None = None
_databases: tuple[float, list[tuple[str, str]]] | None = None


def configured() -> bool:
    return all(os.getenv(k) for k in ENV)


def tables() -> TablesDB:
    global _tables
    with _lock:
        if _tables is None:
            client = (Client()
                      .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
                      .set_project(os.environ["APPWRITE_PROJECT_ID"])
                      .set_key(os.environ["APPWRITE_API_KEY"]))
            _tables = TablesDB(client)
        return _tables


def _base_client() -> Client:
    return Client().set_endpoint(os.environ["APPWRITE_ENDPOINT"]).set_project(os.environ["APPWRITE_PROJECT_ID"])


# --- utenti -------------------------------------------------------------------------------
# I dati restituiti sono dict semplici: {"id", "name", "email", "labels", "created_at", "prefs"}.

def _user_dict(u) -> dict:
    prefs = getattr(u.prefs, "data", None) or {}
    return {"id": u.id, "name": u.name, "email": u.email, "labels": list(u.labels or []),
            "created_at": u.createdat, "prefs": dict(prefs)}


def login(email: str, password: str) -> tuple[str, dict]:
    """Crea una sessione Appwrite; restituisce (secret della sessione, utente)."""
    # con la API key Appwrite restituisce anche il "secret" della sessione
    keyed = Account(_base_client().set_key(os.environ["APPWRITE_API_KEY"]))
    session = keyed.create_email_password_session(email, password)
    return session.secret, user_for_session(session.secret)


def user_for_session(secret: str) -> dict:
    """Utente della sessione (errore 401 di Appwrite se la sessione non è valida o è scaduta)."""
    return _user_dict(Account(_base_client().set_session(secret)).get())


def logout(secret: str) -> None:
    Account(_base_client().set_session(secret)).delete_session("current")


def update_prefs(secret: str, prefs: dict) -> dict:
    """Sostituisce tutte le preferenze dell'utente della sessione; restituisce l'utente aggiornato."""
    return _user_dict(Account(_base_client().set_session(secret)).update_prefs(prefs))


def list_databases() -> list[tuple[str, str]]:
    """[(id, nome)] dei database del progetto, ordinati per id."""
    global _databases
    with _lock:
        if _databases and time.monotonic() - _databases[0] < DATABASES_TTL:
            return _databases[1]
    res = tables().list([Query.limit(100)])
    items = sorted((d.id, d.name) for d in res.databases)
    with _lock:
        _databases = (time.monotonic(), items)
    return items


def rename_database(database_id: str, nome: str) -> None:
    global _databases
    tables().update(database_id, name=nome)
    with _lock:
        _databases = None


def fetch_all(database_id: str, table_id: str) -> list[dict]:
    """Tutte le righe di una tabella (dati delle colonne, senza i campi interni $...)."""
    out: list[dict] = []
    last = None
    while True:
        q = [Query.limit(1000)]
        if last:
            q.append(Query.cursor_after(last))
        res = tables().list_rows(database_id, table_id, q, total=False)
        if not res.rows:
            return out
        out.extend(dict(r.data) for r in res.rows)
        last = res.rows[-1].id
