# backend/main.py
"""API REST della Biblioteca.  Avvio:  uvicorn backend.main:app --reload --port 8000"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.database import get_db, get_session, load_biblioteche, save_biblioteche
from backend.models import Genere, Libro
from backend.schemas import (
    BibliotecaOut, BibliotecaRename, GenereOut, LibriPage, LibroCreate, LibroOut, LibroUpdate, Stats,
)

app = FastAPI(title="Biblioteca API", version="0.2.0")
# tutte le API dei libri sono per una biblioteca: /api/b/{bid}/libri, /api/b/{bid}/generi, ...
router = APIRouter(prefix="/api/b/{bid}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _text_key(col):
    # ignora spazi iniziali/finali e maiuscole (nel DB ci sono titoli che iniziano con uno spazio)
    return [func.lower(func.trim(col))]


def _numeric_text_key(col):
    # Anno/Codice sono TEXT: prima per lunghezza poi per testo = ordine numerico, portabile SQLite/Postgres
    return [func.length(func.trim(col)), func.trim(col)]


SORT_FIELDS = {
    "titolo": _text_key(Libro.titolo),
    "autore": _text_key(Libro.autore),
    "editore": _text_key(Libro.editore),
    "anno": _numeric_text_key(Libro.anno),
    "codice": _numeric_text_key(Libro.codice),
    "collocazione": _text_key(Libro.collocazione),
    "genere": _text_key(Genere.descrizione),
    "id": [Libro.id],
}


def _to_out(libro: Libro) -> LibroOut:
    data = {k: getattr(libro, k) for k in LibroOut.model_fields if k != "genere"}
    return LibroOut(**data, genere=libro.genere.descrizione if libro.genere else None)


def _check_genere(db: Session, genere_id: int | None) -> None:
    if genere_id is not None and db.get(Genere, genere_id) is None:
        raise HTTPException(422, "Genere inesistente")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/biblioteche", response_model=list[BibliotecaOut])
def list_biblioteche():
    out = []
    for b in load_biblioteche():
        totale = None
        disponibile = b.disponibile
        if disponibile:
            try:
                with get_session(b) as db:
                    totale = db.scalar(select(func.count(Libro.id))) or 0
            except SQLAlchemyError:
                disponibile = False  # file presente ma non leggibile / non e' un DB biblioteca
        out.append(BibliotecaOut(
            id=b.id, nome=b.nome, disponibile=disponibile, sorgente=b.descrizione_sorgente, totale_libri=totale,
        ))
    return out


@app.patch("/api/biblioteche/{bid}", response_model=BibliotecaOut)
def rename_biblioteca(bid: str, data: BibliotecaRename):
    items = load_biblioteche()
    b = next((x for x in items if x.id == bid), None)
    if b is None:
        raise HTTPException(404, f"Biblioteca '{bid}' non configurata")
    if any(x.nome.casefold() == data.nome.casefold() for x in items if x.id != bid):
        raise HTTPException(422, "Esiste già una biblioteca con questo nome")
    b.nome = data.nome
    save_biblioteche(items)
    return next(x for x in list_biblioteche() if x.id == bid)


@router.get("/generi", response_model=list[GenereOut])
def list_generi(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Genere, func.count(Libro.id))
        .outerjoin(Libro, Libro.genere_id == Genere.id)
        .group_by(Genere.id)
        .order_by(Genere.descrizione)
    ).all()
    return [GenereOut(id=g.id, descrizione=g.descrizione, totale=n) for g, n in rows]


@router.get("/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)):
    return Stats(
        totale_libri=db.scalar(select(func.count(Libro.id))) or 0,
        totale_autori=db.scalar(select(func.count(func.distinct(Libro.autore)))) or 0,
        totale_generi=db.scalar(select(func.count(Genere.id))) or 0,
        senza_genere=db.scalar(
            select(func.count(Libro.id))
            .outerjoin(Genere, Libro.genere_id == Genere.id)
            .where(Genere.id.is_(None))
        ) or 0,
    )


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
    db: Session = Depends(get_db),
):
    stmt = select(Libro).outerjoin(Genere, Libro.genere_id == Genere.id)

    if q:
        for term in q.split():
            like = f"%{term}%"
            stmt = stmt.where(or_(
                Libro.titolo.ilike(like), Libro.autore.ilike(like), Libro.editore.ilike(like),
                Libro.codice.ilike(like), Libro.collocazione.ilike(like), Libro.premi.ilike(like),
                Libro.note.ilike(like), Libro.anno.ilike(like),
            ))
    if autore:
        stmt = stmt.where(Libro.autore.ilike(f"%{autore.strip()}%"))
    if titolo:
        stmt = stmt.where(Libro.titolo.ilike(f"%{titolo.strip()}%"))
    if editore:
        stmt = stmt.where(Libro.editore.ilike(f"%{editore.strip()}%"))
    if anno:
        stmt = stmt.where(Libro.anno == anno.strip())
    if genere_id == -1:
        stmt = stmt.where(Genere.id.is_(None))
    elif genere_id is not None:
        stmt = stmt.where(Libro.genere_id == genere_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    keys = SORT_FIELDS.get(sort, SORT_FIELDS["titolo"])
    ordering = [k.desc() if order == "desc" else k.asc() for k in keys]
    stmt = stmt.order_by(*ordering, Libro.id).offset((page - 1) * page_size).limit(page_size)

    libri = db.scalars(stmt).unique().all()
    return LibriPage(items=[_to_out(x) for x in libri], total=total, page=page, page_size=page_size)


@router.get("/libri/{libro_id}", response_model=LibroOut)
def get_libro(libro_id: int, db: Session = Depends(get_db)):
    libro = db.get(Libro, libro_id)
    if not libro:
        raise HTTPException(404, "Libro non trovato")
    return _to_out(libro)


@router.post("/libri", response_model=LibroOut, status_code=201)
def create_libro(data: LibroCreate, db: Session = Depends(get_db)):
    _check_genere(db, data.genere_id)
    libro = Libro(**data.model_dump())
    db.add(libro)
    db.commit()
    db.refresh(libro)
    return _to_out(libro)


@router.put("/libri/{libro_id}", response_model=LibroOut)
def update_libro(libro_id: int, data: LibroUpdate, db: Session = Depends(get_db)):
    libro = db.get(Libro, libro_id)
    if not libro:
        raise HTTPException(404, "Libro non trovato")
    _check_genere(db, data.genere_id)
    for k, v in data.model_dump().items():
        setattr(libro, k, v)
    db.commit()
    db.refresh(libro)
    return _to_out(libro)


@router.delete("/libri/{libro_id}", status_code=204)
def delete_libro(libro_id: int, db: Session = Depends(get_db)):
    libro = db.get(Libro, libro_id)
    if not libro:
        raise HTTPException(404, "Libro non trovato")
    db.delete(libro)
    db.commit()
    return Response(status_code=204)


app.include_router(router)
