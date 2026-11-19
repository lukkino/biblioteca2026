# backend/store_sql.py
"""Accesso ai libri su un database SQL (file .db3 SQLite o PostgreSQL/Supabase)."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import Genere, Libro
from backend.schemas import GenereOut, LibriPage, LibroCreate, LibroOut, Stats


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


class SqlStore:
    def __init__(self, db: Session):
        self.db = db

    def _check_genere(self, genere_id: int | None) -> None:
        if genere_id is not None and self.db.get(Genere, genere_id) is None:
            raise HTTPException(422, "Genere inesistente")

    def _get(self, libro_id: int) -> Libro:
        libro = self.db.get(Libro, libro_id)
        if not libro:
            raise HTTPException(404, "Libro non trovato")
        return libro

    def count(self) -> int:
        return self.db.scalar(select(func.count(Libro.id))) or 0

    def list_generi(self) -> list[GenereOut]:
        rows = self.db.execute(
            select(Genere, func.count(Libro.id))
            .outerjoin(Libro, Libro.genere_id == Genere.id)
            .group_by(Genere.id)
            .order_by(Genere.descrizione)
        ).all()
        return [GenereOut(id=g.id, descrizione=g.descrizione, totale=n) for g, n in rows]

    def stats(self) -> Stats:
        db = self.db
        return Stats(
            totale_libri=self.count(),
            totale_autori=db.scalar(select(func.count(func.distinct(Libro.autore)))) or 0,
            totale_generi=db.scalar(select(func.count(Genere.id))) or 0,
            senza_genere=db.scalar(
                select(func.count(Libro.id))
                .outerjoin(Genere, Libro.genere_id == Genere.id)
                .where(Genere.id.is_(None))
            ) or 0,
        )

    def list_libri(self, *, q, autore, titolo, editore, anno, genere_id, sort, order, page, page_size) -> LibriPage:
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

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        keys = SORT_FIELDS.get(sort, SORT_FIELDS["titolo"])
        ordering = [k.desc() if order == "desc" else k.asc() for k in keys]
        stmt = stmt.order_by(*ordering, Libro.id).offset((page - 1) * page_size).limit(page_size)

        libri = self.db.scalars(stmt).unique().all()
        return LibriPage(items=[_to_out(x) for x in libri], total=total, page=page, page_size=page_size)

    def get_libro(self, libro_id: int) -> LibroOut:
        return _to_out(self._get(libro_id))

    def create_libro(self, data: LibroCreate) -> LibroOut:
        self._check_genere(data.genere_id)
        libro = Libro(**data.model_dump())
        self.db.add(libro)
        self.db.commit()
        self.db.refresh(libro)
        return _to_out(libro)

    def update_libro(self, libro_id: int, data) -> LibroOut:
        libro = self._get(libro_id)
        self._check_genere(data.genere_id)
        for k, v in data.model_dump().items():
            setattr(libro, k, v)
        self.db.commit()
        self.db.refresh(libro)
        return _to_out(libro)

    def delete_libro(self, libro_id: int) -> None:
        self.db.delete(self._get(libro_id))
        self.db.commit()
