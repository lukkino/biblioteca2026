# backend/models.py
"""Modelli mappati sulle tabelle esistenti di Biblioteca.db3 (nomi colonna invariati)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Genere(Base):
    __tablename__ = "Genere"

    id: Mapped[int] = mapped_column("Genere_Id", Integer, primary_key=True, autoincrement=True)
    descrizione: Mapped[str | None] = mapped_column("Genere_Descrizione", String(100))


class Libro(Base):
    __tablename__ = "Biblioteca"

    id: Mapped[int] = mapped_column("Libro_Id", Integer, primary_key=True, autoincrement=True)
    codice: Mapped[str | None] = mapped_column("CodiceLibro", Text)
    autore: Mapped[str | None] = mapped_column("Autore", Text)
    titolo: Mapped[str | None] = mapped_column("Titolo", Text)
    editore: Mapped[str | None] = mapped_column("Editore", Text)
    anno: Mapped[str | None] = mapped_column("Anno", Text)
    premi: Mapped[str | None] = mapped_column("Premi", Text)
    collocazione: Mapped[str | None] = mapped_column("Collocazione", Text)
    note: Mapped[str | None] = mapped_column("Note", Text)
    # Nel DB storico non c'e' un vincolo FK: alcuni libri puntano a generi eliminati.
    genere_id: Mapped[int | None] = mapped_column(
        "Genere_Id", Integer, ForeignKey("Genere.Genere_Id"), nullable=True
    )

    genere: Mapped[Genere | None] = relationship(lazy="joined")
