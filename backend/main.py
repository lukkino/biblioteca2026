# backend/main.py
"""API REST della Biblioteca.  Avvio:  uvicorn backend.main:app --reload --port 8000"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import requests
from appwrite.exception import AppwriteException
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from backend import auth
from backend.auth import require_user
from backend.database import (
    Biblioteca, check_disponibile, get_biblioteca, get_session, load_biblioteche, rename_biblioteca,
)
from backend.schemas import (
    BibliotecaOut, BibliotecaRename, GenereOut, LibriPage, LibroCreate, LibroOut, LibroUpdate, Stats,
)
from backend.store_appwrite import store_for
from backend.store_sql import SqlStore

log = logging.getLogger("biblioteca")

app = FastAPI(title="Biblioteca API", version="0.4.0")
# tutte le API dei libri sono per una biblioteca: /api/b/{bid}/libri, /api/b/{bid}/generi, ...
# e richiedono il login (se Appwrite è configurato)
router = APIRouter(prefix="/api/b/{bid}", dependencies=[Depends(require_user)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppwriteException)
@app.exception_handler(requests.RequestException)
def _appwrite_error(_request, exc):
    log.exception("Errore Appwrite", exc_info=exc)
    return JSONResponse({"detail": "Il database online (Appwrite) non risponde, riprova tra poco"}, status_code=503)


def get_store(bid: str):
    """Dipendenza FastAPI: accesso ai libri della biblioteca `bid` (parametro di percorso)."""
    b = get_biblioteca(bid)
    check_disponibile(b)
    if b.appwrite:
        yield store_for(b.appwrite)
        return
    db = get_session(b)
    try:
        yield SqlStore(db)
    finally:
        db.close()


def _totale_libri(b: Biblioteca) -> int:
    if b.appwrite:
        return store_for(b.appwrite).count()
    with get_session(b) as db:
        return SqlStore(db).count()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/biblioteche", response_model=list[BibliotecaOut], dependencies=[Depends(require_user)])
def list_biblioteche():
    out = []
    for b in load_biblioteche():
        totale = None
        disponibile = b.disponibile
        if disponibile:
            try:
                totale = _totale_libri(b)
            except (SQLAlchemyError, AppwriteException, requests.RequestException):
                disponibile = False  # file non leggibile / non e' un DB biblioteca / Appwrite non risponde
        out.append(BibliotecaOut(
            id=b.id, nome=b.nome, disponibile=disponibile, sorgente=b.descrizione_sorgente, totale_libri=totale,
        ))
    return out


@app.patch("/api/biblioteche/{bid}", response_model=BibliotecaOut, dependencies=[Depends(require_user)])
def patch_biblioteca(bid: str, data: BibliotecaRename):
    items = load_biblioteche()
    b = next((x for x in items if x.id == bid), None)
    if b is None:
        raise HTTPException(404, f"Biblioteca '{bid}' non configurata")
    if any(x.nome.casefold() == data.nome.casefold() for x in items if x.id != bid):
        raise HTTPException(422, "Esiste già una biblioteca con questo nome")
    rename_biblioteca(items, b, data.nome)
    return next(x for x in list_biblioteche() if x.id == bid)


@router.get("/generi", response_model=list[GenereOut])
def list_generi(store=Depends(get_store)):
    return store.list_generi()


@router.get("/stats", response_model=Stats)
def stats(store=Depends(get_store)):
    return store.stats()


@router.get("/libri", response_model=LibriPage)
def list_libri(
    q: str | None = Query(None, description="Ricerca libera su titolo, autore, editore, codice, collocazione, premi, note"),
    autore: str | None = None,
    titolo: str | None = None,
    editore: str | None = None,
    anno: str | None = None,
    genere_id: int | None = Query(None, description="-1 = senza genere / genere non valido"),
    sort: str = "titolo",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    store=Depends(get_store),
):
    return store.list_libri(
        q=q, autore=autore, titolo=titolo, editore=editore, anno=anno, genere_id=genere_id,
        sort=sort, order=order, page=page, page_size=page_size,
    )


@router.get("/libri/{libro_id}", response_model=LibroOut)
def get_libro(libro_id: int, store=Depends(get_store)):
    return store.get_libro(libro_id)


@router.post("/libri", response_model=LibroOut, status_code=201)
def create_libro(data: LibroCreate, store=Depends(get_store)):
    return store.create_libro(data)


@router.put("/libri/{libro_id}", response_model=LibroOut)
def update_libro(libro_id: int, data: LibroUpdate, store=Depends(get_store)):
    return store.update_libro(libro_id, data)


@router.delete("/libri/{libro_id}", status_code=204)
def delete_libro(libro_id: int, store=Depends(get_store)):
    store.delete_libro(libro_id)
    return Response(status_code=204)


app.include_router(router)
app.include_router(auth.router)


# --- sito (frontend compilato) --------------------------------------------------------------
# In produzione (Render) lo stesso server serve anche il frontend: stesso indirizzo per sito e
# API, così il cookie di accesso funziona senza configurazioni CORS. In sviluppo il frontend
# gira con Vite (porta 5173) e questa parte resta inattiva finché non esiste frontend/dist.
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if (DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        file = (DIST / path).resolve()
        if path and file.is_file() and DIST in file.parents:
            return FileResponse(file)  # es. favicon
        # index.html mai in cache: dopo un aggiornamento il browser prende subito la versione nuova
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
