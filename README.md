# Biblioteca 2026

Web app per consultare e gestire il catalogo della biblioteca di casa (~6.500 libri).

- **Frontend**: React 19 + Vite + Tailwind CSS + componenti shadcn/ui
- **Backend**: FastAPI + SQLAlchemy 2 (Python)
- **Database**: SQLite locale (`Biblioteca.db3`), predisposto per il passaggio a Supabase/PostgreSQL

## Funzionalità

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

> ⚠️ L'app scrive **direttamente** su `Biblioteca.db3`: conviene tenerne una copia di sicurezza.

## Struttura

```
backend/
  database.py      connessione al DB (legge DATABASE_URL da .env)
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

| Metodo | Percorso | Descrizione |
|---|---|---|
| GET | `/api/libri` | Elenco con `q`, `genere_id` (`-1` = senza genere), `sort`, `order`, `page`, `page_size` |
| GET | `/api/libri/{id}` | Dettaglio di un libro |
| POST | `/api/libri` | Inserisce un libro |
| PUT | `/api/libri/{id}` | Modifica un libro |
| DELETE | `/api/libri/{id}` | Elimina un libro |
| GET | `/api/generi` | Generi con il numero di libri |
| GET | `/api/stats` | Totali (libri, autori, generi, libri senza genere) |
| GET | `/api/health` | Controllo che il backend sia attivo |

## Passaggio a Supabase

1. Creare su Supabase le tabelle `Biblioteca` e `Genere` con gli stessi nomi di colonna del DB SQLite
   e importarvi i dati.
2. Copiare `.env.example` in `.env` e impostare `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
   ```
3. Riavviare il backend. Il frontend non richiede modifiche.

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
