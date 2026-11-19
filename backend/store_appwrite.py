# backend/store_appwrite.py
"""Accesso ai libri su Appwrite.

Il catalogo è piccolo (migliaia di libri), quindi il backend ne tiene una copia in
memoria: ricerca, filtri e ordinamento funzionano esattamente come con SQL
(store_sql.py) senza i limiti delle query di Appwrite. Ogni modifica viene scritta
subito su Appwrite e poi nella copia in memoria; la copia viene comunque ricaricata
ogni CACHE_TTL secondi, per vedere eventuali modifiche fatte da fuori (es. console).

Con più processi del backend ognuno ha la sua copia: le modifiche fatte da un processo
arrivano agli altri al ricaricamento. Su Render (un solo processo) non succede.
"""
from __future__ import annotations

import threading
import time

from appwrite.exception import AppwriteException
from fastapi import HTTPException

from backend import appwrite_client
from backend.schemas import GenereOut, LibriPage, LibroCreate, LibroOut, Stats

CACHE_TTL = 600
CAMPI = ("codice", "autore", "titolo", "editore", "anno", "premi", "collocazione", "note", "genere_id")
RICERCA = ("titolo", "autore", "editore", "codice", "collocazione", "premi", "note", "anno")


def _text_key(v: str | None):
    # come lower(trim(x)) in SQL; i NULL vengono prima (ordine crescente), come in SQLite
    return (0, "") if v is None else (1, v.strip().lower())


def _numeric_text_key(v: str | None):
    # come (length(trim(x)), trim(x)): ordine numerico per Anno/Codice salvati come testo
    if v is None:
        return (0, 0, "")
    s = v.strip()
    return (1, len(s), s)


def _contains(v: str | None, term: str) -> bool:
    return v is not None and term in v.casefold()


class AppwriteStore:
    def __init__(self, database_id: str):
        self.dbid = database_id
        self._lock = threading.RLock()
        self._libri: dict[int, dict] | None = None
        self._generi: dict[int, str | None] = {}
        self._loaded_at = 0.0

    # --- copia in memoria -------------------------------------------------------------

    def _reload(self) -> None:
        generi = {r["genere_id"]: r.get("descrizione") for r in appwrite_client.fetch_all(self.dbid, "generi")}
        libri = {}
        for r in appwrite_client.fetch_all(self.dbid, "libri"):
            libri[r["libro_id"]] = {"id": r["libro_id"], **{k: r.get(k) for k in CAMPI}}
        self._generi, self._libri, self._loaded_at = generi, libri, time.monotonic()

    def _data(self) -> dict[int, dict]:
        with self._lock:
            if self._libri is None or time.monotonic() - self._loaded_at > CACHE_TTL:
                self._reload()
            return self._libri

    def invalidate(self) -> None:
        with self._lock:
            self._libri = None

    def _out(self, row: dict) -> LibroOut:
        return LibroOut(**row, genere=self._generi.get(row["genere_id"]))

    def _sort_key(self, sort: str):
        if sort in ("anno", "codice"):
            return lambda r: _numeric_text_key(r[sort])
        if sort == "id":
            return lambda r: r["id"]
        if sort == "genere":
            return lambda r: _text_key(self._generi.get(r["genere_id"]))
        field = sort if sort in ("titolo", "autore", "editore", "collocazione") else "titolo"
        return lambda r: _text_key(r[field])

    def _check_genere(self, genere_id: int | None) -> None:
        if genere_id is not None and genere_id not in self._generi:
            raise HTTPException(422, "Genere inesistente")

    def _get(self, libro_id: int) -> dict:
        row = self._data().get(libro_id)
        if row is None:
            raise HTTPException(404, "Libro non trovato")
        return row

    # --- letture ----------------------------------------------------------------------

    def count(self) -> int:
        return len(self._data())

    def list_generi(self) -> list[GenereOut]:
        rows = list(self._data().values())
        conta: dict[int | None, int] = {}
        for r in rows:
            conta[r["genere_id"]] = conta.get(r["genere_id"], 0) + 1
        out = [GenereOut(id=g, descrizione=d, totale=conta.get(g, 0)) for g, d in self._generi.items()]
        out.sort(key=lambda g: g.id)
        out.sort(key=lambda g: (g.descrizione is not None, g.descrizione or ""))
        return out

    def stats(self) -> Stats:
        rows = list(self._data().values())
        return Stats(
            totale_libri=len(rows),
            totale_autori=len({r["autore"] for r in rows if r["autore"] is not None}),
            totale_generi=len(self._generi),
            senza_genere=sum(1 for r in rows if r["genere_id"] not in self._generi),
        )

    def list_libri(self, *, q, autore, titolo, editore, anno, genere_id, sort, order, page, page_size) -> LibriPage:
        rows = list(self._data().values())

        if q:
            for term in q.split():
                t = term.casefold()
                rows = [r for r in rows if any(_contains(r[f], t) for f in RICERCA)]
        for field, value in (("autore", autore), ("titolo", titolo), ("editore", editore)):
            if value:
                t = value.strip().casefold()
                rows = [r for r in rows if _contains(r[field], t)]
        if anno:
            rows = [r for r in rows if r["anno"] == anno.strip()]
        if genere_id == -1:
            rows = [r for r in rows if r["genere_id"] not in self._generi]
        elif genere_id is not None:
            rows = [r for r in rows if r["genere_id"] == genere_id]

        # a parità di chiave, ordine per id crescente (sort stabile, anche con reverse)
        rows.sort(key=lambda r: r["id"])
        rows.sort(key=self._sort_key(sort), reverse=order == "desc")

        start = (page - 1) * page_size
        items = [self._out(r) for r in rows[start:start + page_size]]
        return LibriPage(items=items, total=len(rows), page=page, page_size=page_size)

    def get_libro(self, libro_id: int) -> LibroOut:
        return self._out(self._get(libro_id))

    # --- scritture --------------------------------------------------------------------

    def create_libro(self, data: LibroCreate) -> LibroOut:
        with self._lock:
            libri = self._data()
            self._check_genere(data.genere_id)
            values = data.model_dump()
            for _ in range(3):
                new_id = max(libri, default=0) + 1
                try:
                    appwrite_client.tables().create_row(
                        self.dbid, "libri", str(new_id), {"libro_id": new_id, **values})
                    break
                except AppwriteException as e:
                    if e.code != 409:  # 409 = id già usato (es. libro aggiunto da fuori): ricarico e riprovo
                        raise
                    self._reload()
                    libri = self._libri
            else:
                raise HTTPException(409, "Impossibile assegnare un nuovo codice al libro, riprova")
            row = libri[new_id] = {"id": new_id, **values}
            return self._out(row)

    def update_libro(self, libro_id: int, data) -> LibroOut:
        with self._lock:
            row = self._get(libro_id)
            self._check_genere(data.genere_id)
            values = data.model_dump()
            try:
                appwrite_client.tables().update_row(self.dbid, "libri", str(libro_id), values)
            except AppwriteException as e:
                if e.code == 404:
                    self._libri.pop(libro_id, None)
                    raise HTTPException(404, "Libro non trovato") from None
                raise
            row.update(values)
            return self._out(row)

    def delete_libro(self, libro_id: int) -> None:
        with self._lock:
            self._get(libro_id)
            try:
                appwrite_client.tables().delete_row(self.dbid, "libri", str(libro_id))
            except AppwriteException as e:
                if e.code != 404:
                    raise
            self._libri.pop(libro_id, None)


_stores: dict[str, AppwriteStore] = {}
_stores_lock = threading.Lock()


def store_for(database_id: str) -> AppwriteStore:
    with _stores_lock:
        s = _stores.get(database_id)
        if s is None:
            s = _stores[database_id] = AppwriteStore(database_id)
        return s


def reset_stores() -> None:
    with _stores_lock:
        _stores.clear()
