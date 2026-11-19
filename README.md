# Biblioteca 2026

Web app per consultare e gestire il catalogo della biblioteca di casa (~6.500 libri).

- **Frontend**: React 19 + Vite + Tailwind CSS + componenti shadcn/ui
- **Backend**: FastAPI + SQLAlchemy 2 (Python)
- **Database**: SQLite locale (`Biblioteca.db3`), predisposto per il passaggio a Supabase/PostgreSQL

## Funzionalità

- Più biblioteche (es. Casa e Parrocchia), ognuna con il proprio database, scelte dal menu in alto
- Elenco paginato (25 / 50 / 100 per pagina) con ordinamento cliccando sulle colonne
- Ricerca libera su titolo, autore, editore, anno, codice, collocazione, premi e note
  (più parole = devono comparire tutte)
- Filtro per genere con il numero di libri, più il filtro "Senza genere"
- Inserimento, modifica ed eliminazione (con conferma) dei libri
- Tema chiaro/scuro e layout per smartphone

## Requisiti

- Python 3.12+ (sviluppato con 3.14)
- Node.js 20.19+ (sviluppato con 24)
- Il file di database `Biblioteca.db3` nella cartella principale del progetto

> Il database **non è incluso nel repository** perché contiene dati personali.
> Va copiato a mano nella cartella principale prima di avviare l'app.

## Installazione

```powershell
# Backend (dalla cartella principale)
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt

# Frontend
cd frontend
npm install
```

## Avvio

Servono due terminali.

```powershell
# 1. Backend → http://localhost:8000  (documentazione API: http://localhost:8000/docs)
.venv\Scripts\uvicorn backend.main:app --reload --port 8000

# 2. Frontend → http://localhost:5173
cd frontend
npm run dev
```

Il frontend inoltra le chiamate `/api/*` al backend sulla porta 8000 (proxy configurato in `frontend/vite.config.js`).

> ⚠️ L'app scrive **direttamente** sui file `.db3`: conviene tenerne una copia di sicurezza.

## Più biblioteche

Le biblioteche sono elencate in `biblioteche.json` nella cartella principale
(escluso dal repository; c'è un esempio in `biblioteche.example.json`):

```json
[
  { "id": "biblioteca1", "nome": "Casa",       "file": "Biblioteca.db3" },
  { "id": "biblioteca2", "nome": "Parrocchia", "file": "Parrocchia.db3" }
]
```

- **`id`**: identificativo fisso, usato negli indirizzi delle API. Non va cambiato.
- **`nome`**: il nome mostrato nell'app. Si può cambiare anche dall'app (matita accanto al nome).
- **`file`**: il database SQLite, con la stessa struttura di `Biblioteca.db3`.

Per **aggiungere una biblioteca** basta aggiungere una voce e copiare il file `.db3` nella cartella.
Finché il file non c'è, l'app mostra la biblioteca come "non disponibile" (il file non viene mai creato
vuoto). Se `biblioteche.json` non esiste, l'app usa solo `Biblioteca.db3`.

**Compatibilità con il vecchio programma:** i file `.db3` restano nel formato originale. L'app non
cambia la struttura delle tabelle, non attiva la modalità WAL e non tiene il file aperto tra
un'operazione e l'altra, così il vecchio programma può continuare a usarli. Meglio comunque non
modificare lo stesso libro contemporaneamente dai due programmi.

## Struttura

```
biblioteche.json   elenco delle biblioteche e dei loro database (locale, non versionato)
backend/
  database.py      connessione ai DB delle biblioteche (legge biblioteche.json e .env)
  models.py        mappatura delle tabelle esistenti Biblioteca e Genere
  schemas.py       validazione dei dati in ingresso/uscita (Pydantic)
  main.py          endpoint REST
frontend/
  src/api/libri.js tutte le chiamate al backend
  src/App.jsx      pagina principale (tabella, ricerca, filtri, paginazione)
  src/components/  finestra inserimento/modifica e componenti UI
tests/
  test_api.py      test del backend (lavorano su una copia del DB)
```

## API

`{bid}` è l'`id` della biblioteca in `biblioteche.json`.

| Metodo | Percorso | Descrizione |
|---|---|---|
| GET | `/api/biblioteche` | Biblioteche configurate, con disponibilità e numero di libri |
| PATCH | `/api/biblioteche/{bid}` | Rinomina una biblioteca (`{"nome": "..."}`) |
| GET | `/api/b/{bid}/libri` | Elenco con `q`, `genere_id` (`-1` = senza genere), `sort`, `order`, `page`, `page_size` |
| GET | `/api/b/{bid}/libri/{id}` | Dettaglio di un libro |
| POST | `/api/b/{bid}/libri` | Inserisce un libro |
| PUT | `/api/b/{bid}/libri/{id}` | Modifica un libro |
| DELETE | `/api/b/{bid}/libri/{id}` | Elimina un libro |
| GET | `/api/b/{bid}/generi` | Generi con il numero di libri |
| GET | `/api/b/{bid}/stats` | Totali (libri, autori, generi, libri senza genere) |
| GET | `/api/health` | Controllo che il backend sia attivo |

## Passaggio a Supabase

1. Creare su Supabase le tabelle `Biblioteca` e `Genere` con gli stessi nomi di colonna del DB SQLite
   e importarvi i dati (un database, o uno schema, per ogni biblioteca).
2. Mettere l'indirizzo con la password in `.env`:
   ```
   DATABASE_URL_CASA=postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
   ```
3. In `biblioteche.json` sostituire `"file"` con `"url"`, che fa riferimento alla variabile:
   ```json
   { "id": "biblioteca1", "nome": "Casa", "url": "${DATABASE_URL_CASA}" }
   ```
4. Riavviare il backend. Il frontend non richiede modifiche.

Il file `.env` è escluso dal repository: non va mai pubblicato.

## Sviluppo

```powershell
# Test del backend (richiedono Biblioteca.db3)
.venv\Scripts\pip install pytest httpx
.venv\Scripts\python -m pytest tests

# Controlli e build del frontend
cd frontend
npm run lint
npm run build
```
