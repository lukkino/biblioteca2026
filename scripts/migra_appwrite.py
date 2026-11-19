"""Migra una biblioteca da un file SQLite (.db3 del vecchio programma) ad Appwrite.

Uso (dalla cartella principale del progetto):
    .venv\\Scripts\\python scripts\\migra_appwrite.py Biblioteca.db3 biblioteca1 "Casa"

- Crea, se mancano, il database <id> e le tabelle "libri" e "generi".
- Copia libri e generi mantenendo gli ID originali (ID riga = Libro_Id / Genere_Id),
  quindi si può rilanciare: le righe esistenti vengono aggiornate, non duplicate.
- Il file .db3 viene solo letto, mai modificato.
- Alla fine confronta i conteggi e alcuni libri campione con l'originale.

Legge APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID e APPWRITE_API_KEY da .env.
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.query import Query
from appwrite.services.tables_db import TablesDB
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
BATCH = 100  # limite di Appwrite per le operazioni in blocco

# (chiave, dimensione) delle colonne di testo dei libri; dimensioni ampie rispetto ai dati attuali
LIBRI_TESTO = [
    ("codice", 50),
    ("autore", 255),
    ("titolo", 500),
    ("editore", 255),
    ("anno", 20),
    ("premi", 500),
    ("collocazione", 100),
    ("note", 2000),
]
SQL_LIBRI = {
    "codice": "CodiceLibro", "autore": "Autore", "titolo": "Titolo", "editore": "Editore",
    "anno": "Anno", "premi": "Premi", "collocazione": "Collocazione", "note": "Note",
}


def client() -> TablesDB:
    load_dotenv(ROOT / ".env")
    missing = [k for k in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY") if not os.getenv(k)]
    if missing:
        sys.exit(f"Mancano in .env: {', '.join(missing)}")
    c = (Client()
         .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
         .set_project(os.environ["APPWRITE_PROJECT_ID"])
         .set_key(os.environ["APPWRITE_API_KEY"]))
    return TablesDB(c)


def exists(fn, *args) -> bool:
    try:
        fn(*args)
        return True
    except AppwriteException as e:
        if e.code == 404:
            return False
        raise


def status(obj) -> str:
    s = obj.status
    return getattr(s, "value", s)


def wait_columns(db: TablesDB, dbid: str, tid: str, keys: list[str]) -> None:
    for _ in range(120):
        states = {k: status(db.get_column(dbid, tid, k)) for k in keys}
        bad = {k: s for k, s in states.items() if s == "failed"}
        if bad:
            sys.exit(f"Creazione colonne fallita in {tid}: {bad}")
        if all(s == "available" for s in states.values()):
            return
        time.sleep(1)
    sys.exit(f"Timeout in attesa delle colonne di {tid}")


def wait_indexes(db: TablesDB, dbid: str, tid: str, keys: list[str]) -> None:
    for _ in range(120):
        states = {k: status(db.get_index(dbid, tid, k)) for k in keys}
        if any(s == "failed" for s in states.values()):
            sys.exit(f"Creazione indici fallita in {tid}: {states}")
        if all(s == "available" for s in states.values()):
            return
        time.sleep(1)
    sys.exit(f"Timeout in attesa degli indici di {tid}")


def ensure_structure(db: TablesDB, dbid: str, nome: str) -> None:
    from appwrite.enums.tables_db_index_type import TablesDBIndexType

    if not exists(db.get, dbid):
        db.create(dbid, nome)
        print(f"Creato database {dbid} ({nome})")

    # Nessun permesso: solo il backend (con la API key) può leggere e scrivere.
    if not exists(db.get_table, dbid, "generi"):
        db.create_table(dbid, "generi", "Generi", permissions=[], row_security=False)
        print("Creata tabella generi")
    want = {"genere_id": lambda: db.create_integer_column(dbid, "generi", "genere_id", True),
            "descrizione": lambda: db.create_varchar_column(dbid, "generi", "descrizione", 255, False)}
    for key, make in want.items():
        if not exists(db.get_column, dbid, "generi", key):
            make()
    wait_columns(db, dbid, "generi", list(want))

    if not exists(db.get_table, dbid, "libri"):
        db.create_table(dbid, "libri", "Libri", permissions=[], row_security=False)
        print("Creata tabella libri")
    want = {"libro_id": lambda: db.create_integer_column(dbid, "libri", "libro_id", True),
            "genere_id": lambda: db.create_integer_column(dbid, "libri", "genere_id", False)}
    for key, size in LIBRI_TESTO:
        want[key] = (lambda k=key, s=size: db.create_varchar_column(dbid, "libri", k, s, False))
    for key, make in want.items():
        if not exists(db.get_column, dbid, "libri", key):
            make()
    wait_columns(db, dbid, "libri", list(want))

    indexes = {
        ("libri", "idx_libro_id"): (TablesDBIndexType.UNIQUE, ["libro_id"]),
        ("libri", "idx_genere_id"): (TablesDBIndexType.KEY, ["genere_id"]),
        ("generi", "idx_genere_id"): (TablesDBIndexType.UNIQUE, ["genere_id"]),
    }
    for (tid, key), (kind, cols) in indexes.items():
        if not exists(db.get_index, dbid, tid, key):
            db.create_index(dbid, tid, key, kind, cols)
    for tid in ("libri", "generi"):
        wait_indexes(db, dbid, tid, [k for (t, k) in indexes if t == tid])
    print("Struttura pronta")


def read_sqlite(path: Path):
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    generi = [{"$id": str(r["Genere_Id"]), "genere_id": r["Genere_Id"], "descrizione": r["Genere_Descrizione"]}
              for r in con.execute("select * from Genere order by Genere_Id")]
    libri = []
    for r in con.execute("select * from Biblioteca order by Libro_Id"):
        row = {"$id": str(r["Libro_Id"]), "libro_id": r["Libro_Id"], "genere_id": r["Genere_Id"]}
        for key, col in SQL_LIBRI.items():
            row[key] = r[col]
        libri.append(row)
    con.close()
    return generi, libri


def upload(db: TablesDB, dbid: str, tid: str, rows: list[dict]) -> None:
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        for attempt in range(5):
            try:
                db.upsert_rows(dbid, tid, chunk)
                break
            except AppwriteException as e:
                if attempt == 4 or (e.code and e.code < 500 and e.code != 429):
                    raise
                time.sleep(2 * (attempt + 1))
        print(f"  {tid}: {min(i + BATCH, len(rows))}/{len(rows)}")


def fetch_all(db: TablesDB, dbid: str, tid: str) -> dict[str, dict]:
    out, last = {}, None
    while True:
        q = [Query.limit(1000), Query.order_asc("$id")]
        if last:
            q.append(Query.cursor_after(last))
        res = db.list_rows(dbid, tid, q, total=False)
        rows = [{**r.data, "$id": r.id} for r in res.rows]
        if not rows:
            return out
        for r in rows:
            out[r["$id"]] = r
        last = rows[-1]["$id"]


def verify(db: TablesDB, dbid: str, generi: list[dict], libri: list[dict]) -> bool:
    ok = True
    for tid, src in (("generi", generi), ("libri", libri)):
        remote = fetch_all(db, dbid, tid)
        diff = []
        for row in src:
            r = remote.get(row["$id"])
            if r is None:
                diff.append((row["$id"], "mancante"))
                continue
            for k, v in row.items():
                if k != "$id" and r.get(k) != v:
                    diff.append((row["$id"], k, v, r.get(k)))
        extra = set(remote) - {row["$id"] for row in src}
        print(f"Verifica {tid}: originale {len(src)}, Appwrite {len(remote)}, "
              f"differenze {len(diff)}, righe in più {len(extra)}")
        for d in diff[:10]:
            print("   ", d)
        ok = ok and not diff
    return ok


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", help="file .db3 da migrare")
    p.add_argument("id", help="id della biblioteca (diventa l'id del database Appwrite)")
    p.add_argument("nome", help="nome della biblioteca")
    a = p.parse_args()

    path = (ROOT / a.file) if not Path(a.file).is_absolute() else Path(a.file)
    if not path.exists():
        sys.exit(f"File non trovato: {path}")
    generi, libri = read_sqlite(path)
    print(f"Letti da {path.name}: {len(libri)} libri, {len(generi)} generi")

    db = client()
    ensure_structure(db, a.id, a.nome)
    upload(db, a.id, "generi", generi)
    upload(db, a.id, "libri", libri)
    sys.exit(0 if verify(db, a.id, generi, libri) else 1)


if __name__ == "__main__":
    main()
