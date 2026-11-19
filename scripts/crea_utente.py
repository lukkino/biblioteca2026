"""Crea (o abilita) un utente che può entrare nella Biblioteca.

Uso, da un terminale nella cartella principale del progetto:
    .venv\\Scripts\\python scripts\\crea_utente.py

Chiede email, nome e password (la password non viene mostrata mentre la scrivi).
- Se l'utente non esiste lo crea su Appwrite con l'etichetta "biblioteca".
- Se esiste già, gli aggiunge l'etichetta e, se vuoi, cambia la password.
Per togliere l'accesso a qualcuno: console Appwrite → Auth → utente → togli l'etichetta
"biblioteca" (oppure blocca/elimina l'utente).
"""
import getpass
import os
import sys
from pathlib import Path

from appwrite.client import Client
from appwrite.exception import AppwriteException
from appwrite.id import ID
from appwrite.query import Query
from appwrite.services.users import Users
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
LABEL = "biblioteca"


def chiedi_password() -> str:
    while True:
        p1 = getpass.getpass("Password (almeno 8 caratteri, non viene mostrata): ")
        if len(p1) < 8:
            print("  Troppo corta, riprova.")
            continue
        if getpass.getpass("Ripeti la password: ") != p1:
            print("  Le due password non coincidono, riprova.")
            continue
        return p1


def main() -> None:
    load_dotenv(ROOT / ".env")
    if not all(os.getenv(k) for k in ("APPWRITE_ENDPOINT", "APPWRITE_PROJECT_ID", "APPWRITE_API_KEY")):
        sys.exit("Mancano le impostazioni di Appwrite in .env")
    users = Users(Client()
                  .set_endpoint(os.environ["APPWRITE_ENDPOINT"])
                  .set_project(os.environ["APPWRITE_PROJECT_ID"])
                  .set_key(os.environ["APPWRITE_API_KEY"]))

    email = input("Email: ").strip().lower()
    if "@" not in email:
        sys.exit("Email non valida")

    found = users.list([Query.equal("email", email)]).users
    if found:
        u = found[0]
        print(f"L'utente {u.email} ({u.name}) esiste già.")
        if input("Vuoi cambiargli la password? [s/N] ").strip().lower() == "s":
            users.update_password(u.id, chiedi_password())
            print("Password aggiornata.")
    else:
        nome = input("Nome (es. Maria): ").strip()
        try:
            u = users.create(ID.unique(), email=email, password=chiedi_password(), name=nome or None)
        except AppwriteException as e:
            sys.exit(f"Appwrite non ha accettato l'utente: {e.message}")
        print(f"Utente {email} creato.")

    labels = sorted(set(u.labels or []) | {LABEL})
    users.update_labels(u.id, labels)
    print(f"Fatto: {email} può entrare nella Biblioteca.")


if __name__ == "__main__":
    main()
