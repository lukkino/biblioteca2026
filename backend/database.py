# backend/database.py
"""Connessione ai DB delle biblioteche.

Da dove arriva l'elenco delle biblioteche, in ordine di priorità:

1. `biblioteche.json` nella cartella principale, se esiste:

    [
      {"id": "biblioteca1", "nome": "Casa",       "file": "Biblioteca.db3"},
      {"id": "biblioteca2", "nome": "Parrocchia", "appwrite": "biblioteca2"}
    ]

   - `id`   identificativo fisso usato negli URL (non cambiarlo dopo)
   - `nome` nome mostrato nell'app (modificabile anche dall'app)
   - `file` file SQLite, relativo alla cartella principale, oppure
     `url`  URL SQLAlchemy, es. per Supabase: "${DATABASE_URL_CASA}" (le variabili
            ${...} vengono lette da .env, cosi' le password non stanno nel JSON), oppure
     `appwrite` id del database Appwrite

2. Appwrite, se APPWRITE_ENDPOINT/PROJECT_ID/API_KEY sono configurati: ogni database
   del progetto è una biblioteca (id = id del database, nome = nome del database,
   rinominabile dall'app). È la modalità usata online, dove non ci sono file locali.

3. Una sola biblioteca: DATABASE_URL da .env oppure `Biblioteca.db3`.

I file SQLite sono usati anche dal vecchio programma: per questo NON si attiva la
modalita' WAL e un file mancante non viene mai creato (connessione mode=rw).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from backend import appwrite_client

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Base(DeclarativeBase):
    pass


def config_path() -> Path:
    return Path(os.getenv("BIBLIOTECHE_CONFIG") or ROOT / "biblioteche.json")


@dataclass
class Biblioteca:
    id: str
    nome: str
    file: str | None = None
    url: str | None = None
    appwrite: str | None = None  # id del database Appwrite

    @property
    def sqlite_path(self) -> Path | None:
        if self.file:
            p = Path(self.file)
            return p if p.is_absolute() else ROOT / p
        return None

    @property
    def disponibile(self) -> bool:
        if self.appwrite:
            return appwrite_client.configured()
        p = self.sqlite_path
        return p.is_file() if p else bool(self.resolved_url)

    @property
    def resolved_url(self) -> str | None:
        return os.path.expandvars(self.url) if self.url else None

    @property
    def descrizione_sorgente(self) -> str:
        # da mostrare all'utente: mai l'URL completo (puo' contenere password)
        if self.appwrite:
            return "Appwrite"
        return self.file or "database remoto"


_lock = threading.Lock()
_engines: dict[str, Engine] = {}
CAMPI_CONFIG = ("id", "nome", "file", "url", "appwrite")


def sorgente_elenco() -> str:
    """'file' (biblioteche.json), 'appwrite' (database del progetto) oppure 'default'."""
    if config_path().is_file():
        return "file"
    if appwrite_client.configured():
        return "appwrite"
    return "default"


def load_biblioteche() -> list[Biblioteca]:
    sorgente = sorgente_elenco()
    if sorgente == "file":
        data = json.loads(config_path().read_text(encoding="utf-8"))
        return [Biblioteca(**{k: v for k, v in d.items() if k in CAMPI_CONFIG}) for d in data]
    if sorgente == "appwrite":
        return [Biblioteca(id=i, nome=n, appwrite=i) for i, n in appwrite_client.list_databases()]
    url = os.getenv("DATABASE_URL")
    if url:
        return [Biblioteca(id="biblioteca1", nome="Biblioteca", url=url)]
    return [Biblioteca(id="biblioteca1", nome="Biblioteca", file="Biblioteca.db3")]


def rename_biblioteca(items: list[Biblioteca], b: Biblioteca, nome: str) -> None:
    b.nome = nome
    if sorgente_elenco() == "appwrite":
        appwrite_client.rename_database(b.appwrite, nome)
    else:
        save_biblioteche(items)


def save_biblioteche(items: list[Biblioteca]) -> None:
    p = config_path()
    data = [{k: v for k, v in vars(b).items() if v is not None} for b in items]
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(p)  # scrittura atomica


def get_biblioteca(bid: str) -> Biblioteca:
    for b in load_biblioteche():
        if b.id == bid:
            return b
    raise HTTPException(404, f"Biblioteca '{bid}' non configurata")


def _make_engine(b: Biblioteca) -> Engine:
    path = b.sqlite_path
    if path:
        uri = f"{path.as_uri()}?mode=rw"  # rw: non crea il file se manca
        # NullPool: nessuna connessione resta aperta sul file tra una richiesta e l'altra,
        # cosi' il vecchio programma non trova mai il file occupato dall'app.
        return create_engine(
            "sqlite://",
            creator=lambda: sqlite3.connect(uri, uri=True, check_same_thread=False, timeout=10),
            poolclass=NullPool,
        )
    return create_engine(b.resolved_url, pool_pre_ping=True)


def engine_for(b: Biblioteca) -> Engine:
    with _lock:
        eng = _engines.get(b.id)
        if eng is None:
            eng = _engines[b.id] = _make_engine(b)
        return eng


def check_disponibile(b: Biblioteca) -> None:
    if not b.disponibile:
        sorgente = "Appwrite non configurato" if b.appwrite else f"{b.descrizione_sorgente} non trovato"
        raise HTTPException(503, f"Il database della biblioteca '{b.nome}' non è disponibile ({sorgente})")


def get_session(b: Biblioteca) -> Session:
    return sessionmaker(bind=engine_for(b), autoflush=False)()
