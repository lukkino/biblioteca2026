# backend/database.py
"""Connessione ai DB delle biblioteche.

Ogni biblioteca (es. "Casa", "Parrocchia") ha il suo database, elencato in
`biblioteche.json` nella cartella principale:

    [
      {"id": "biblioteca1", "nome": "Casa",       "file": "Biblioteca.db3"},
      {"id": "biblioteca2", "nome": "Parrocchia", "file": "Parrocchia.db3"}
    ]

- `id`   identificativo fisso usato negli URL (non cambiarlo dopo)
- `nome` nome mostrato nell'app (modificabile anche dall'app)
- `file` file SQLite, relativo alla cartella principale, oppure
  `url`  URL SQLAlchemy, es. per Supabase: "${DATABASE_URL_CASA}" (le variabili
         ${...} vengono lette da .env, cosi' le password non stanno nel JSON)

Se `biblioteche.json` non esiste si usa una sola biblioteca: DATABASE_URL da .env
oppure `Biblioteca.db3`.

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

    @property
    def sqlite_path(self) -> Path | None:
        if self.file:
            p = Path(self.file)
            return p if p.is_absolute() else ROOT / p
        return None

    @property
    def disponibile(self) -> bool:
        p = self.sqlite_path
        return p.is_file() if p else bool(self.resolved_url)

    @property
    def resolved_url(self) -> str | None:
        return os.path.expandvars(self.url) if self.url else None

    @property
    def descrizione_sorgente(self) -> str:
        # da mostrare all'utente: mai l'URL completo (puo' contenere password)
        return self.file or "database remoto"


_lock = threading.Lock()
_engines: dict[str, Engine] = {}


def load_biblioteche() -> list[Biblioteca]:
    p = config_path()
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        return [Biblioteca(**{k: v for k, v in d.items() if k in ("id", "nome", "file", "url")}) for d in data]
    url = os.getenv("DATABASE_URL")
    if url:
        return [Biblioteca(id="biblioteca1", nome="Biblioteca", url=url)]
    return [Biblioteca(id="biblioteca1", nome="Biblioteca", file="Biblioteca.db3")]


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


def get_db(bid: str):
    """Dipendenza FastAPI: sessione sul DB della biblioteca `bid` (parametro di percorso)."""
    b = get_biblioteca(bid)
    if not b.disponibile:
        raise HTTPException(
            503, f"Il database della biblioteca '{b.nome}' non è disponibile ({b.descrizione_sorgente} non trovato)"
        )
    db = sessionmaker(bind=engine_for(b), autoflush=False)()
    try:
        yield db
    finally:
        db.close()


def get_session(b: Biblioteca) -> Session:
    return sessionmaker(bind=engine_for(b), autoflush=False)()
