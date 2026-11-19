"""Finto TablesDB di Appwrite, in memoria, per i test (solo i metodi usati dal backend)."""
import json
import sqlite3
from types import SimpleNamespace as NS

from appwrite.exception import AppwriteException


class FakeTablesDB:
    def __init__(self):
        self.databases: dict[str, str] = {}               # id -> nome
        self.rows: dict[tuple[str, str], dict[str, dict]] = {}  # (db, tabella) -> {row_id: dati}

    def load_sqlite(self, dbid: str, nome: str, path) -> None:
        self.databases[dbid] = nome
        con = sqlite3.connect(path)
        self.rows[(dbid, "generi")] = {
            str(i): {"genere_id": i, "descrizione": d} for i, d in con.execute("select * from Genere")}
        cols = "Libro_Id, CodiceLibro, Autore, Titolo, Editore, Anno, Premi, Collocazione, Note, Genere_Id"
        keys = ["libro_id", "codice", "autore", "titolo", "editore", "anno", "premi", "collocazione", "note", "genere_id"]
        self.rows[(dbid, "libri")] = {
            str(r[0]): dict(zip(keys, r)) for r in con.execute(f"select {cols} from Biblioteca")}
        con.close()

    def _table(self, dbid, tid):
        if (dbid, tid) not in self.rows:
            raise AppwriteException("Table not found", 404)
        return self.rows[(dbid, tid)]

    # --- database ---
    def list(self, queries=None, search=None, total=None):
        return NS(databases=[NS(id=i, name=n) for i, n in self.databases.items()], total=len(self.databases))

    def update(self, database_id, name=None, **_):
        self.databases[database_id] = name

    # --- righe ---
    def list_rows(self, database_id, table_id, queries=None, total=None, **_):
        table = self._table(database_id, table_id)
        q = {d["method"]: d.get("values", []) for d in map(json.loads, queries or [])}
        ids = list(table)
        if "cursorAfter" in q:
            ids = ids[ids.index(q["cursorAfter"][0]) + 1:]
        ids = ids[: q.get("limit", [25])[0]]
        return NS(rows=[NS(id=i, data=dict(table[i])) for i in ids], total=len(table))

    def create_row(self, database_id, table_id, row_id, data, **_):
        table = self._table(database_id, table_id)
        if row_id in table:
            raise AppwriteException("Row already exists", 409)
        table[row_id] = dict(data)

    def update_row(self, database_id, table_id, row_id, data=None, **_):
        table = self._table(database_id, table_id)
        if row_id not in table:
            raise AppwriteException("Row not found", 404)
        table[row_id].update(data or {})

    def delete_row(self, database_id, table_id, row_id, **_):
        table = self._table(database_id, table_id)
        if row_id not in table:
            raise AppwriteException("Row not found", 404)
        del table[row_id]
