# backend/schemas.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GenereOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descrizione: str | None
    totale: int = 0


class LibroBase(BaseModel):
    # lunghezze massime = dimensioni delle colonne su Appwrite (scripts/migra_appwrite.py)
    codice: str | None = Field(default=None, max_length=50)
    autore: str | None = Field(default=None, max_length=255)
    titolo: str = Field(min_length=1, max_length=500)
    editore: str | None = Field(default=None, max_length=255)
    anno: str | None = Field(default=None, max_length=20)
    premi: str | None = Field(default=None, max_length=500)
    collocazione: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=2000)
    genere_id: int | None = None

    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("titolo")
    @classmethod
    def _titolo_non_vuoto(cls, v: str) -> str:
        if not v:
            raise ValueError("Il titolo e' obbligatorio")
        return v


class LibroCreate(LibroBase):
    pass


class LibroUpdate(LibroBase):
    pass


class LibroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    codice: str | None
    autore: str | None
    titolo: str | None
    editore: str | None
    anno: str | None
    premi: str | None
    collocazione: str | None
    note: str | None
    genere_id: int | None
    genere: str | None = None


class LibriPage(BaseModel):
    items: list[LibroOut]
    total: int
    page: int
    page_size: int


class BibliotecaOut(BaseModel):
    id: str
    nome: str
    disponibile: bool
    sorgente: str          # nome del file (mai l'URL completo con password)
    totale_libri: int | None = None


class BibliotecaRename(BaseModel):
    nome: str = Field(min_length=1, max_length=60)

    @field_validator("nome", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class Stats(BaseModel):
    totale_libri: int
    totale_autori: int
    totale_generi: int
    senza_genere: int
