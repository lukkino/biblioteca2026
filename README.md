# Biblioteca 2026

Web app per consultare e gestire il catalogo della biblioteca di casa (~6.500 libri).

- **Frontend**: React 19 + Vite + Tailwind CSS + componenti shadcn/ui
- **Backend**: FastAPI + SQLAlchemy 2 (Python)
- **Database**: online su [Appwrite](https://appwrite.io) (un database per biblioteca); in alternativa
  file SQLite locali (`.db3` del vecchio programma) o Supabase/PostgreSQL

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
- Un progetto Appwrite con le chiavi in `.env` (vedi [Database online](#database-online-appwrite)),
  oppure il file `Biblioteca.db3` nella cartella principale

> I dati **non sono inclusi nel repository** perché sono personali: né i file `.db3`, né `.env` con le chiavi.

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

## Database online (Appwrite)

Ogni biblioteca è un **database** del progetto Appwrite, con le tabelle `libri` e `generi`.
Il nome del database è il nome della biblioteca mostrato nell'app (si cambia anche dall'app).

1. In `.env` (copiato da `.env.example`):
   ```
   APPWRITE_ENDPOINT=https://fra.cloud.appwrite.io/v1
   APPWRITE_PROJECT_ID=<id progetto>
   APPWRITE_API_KEY=<chiave con scopes Database e users.read/write>
   ```
2. Migrare una biblioteca dal file del vecchio programma (crea database e tabelle se mancano,
   mantiene gli ID dei libri, si può rilanciare senza creare doppioni, verifica il risultato):
   ```powershell
   .venv\Scripts\python scripts\migra_appwrite.py Biblioteca.db3 biblioteca1 "Casa"
   ```
3. Senza `biblioteche.json`, l'app mostra automaticamente tutte le biblioteche presenti su Appwrite.

Il backend tiene in memoria una copia del catalogo (pochi MB): ricerca e ordinamento sono istantanei
e identici alla versione SQLite. Ogni modifica è scritta subito su Appwrite; la copia si ricarica
comunque ogni 10 minuti. La chiave API resta solo sul backend: il browser non parla mai con Appwrite.

### Accesso (login)

Con Appwrite configurato l'app chiede email e password. Possono entrare solo gli utenti di Appwrite
con l'etichetta **`biblioteca`**: avere un account nel progetto non basta.

- **Creare un utente** (o abilitarne uno esistente, o cambiargli la password), da un terminale:
  ```powershell
  .venv\Scripts\python scripts\crea_utente.py
  ```
  La password si scrive lì e non viene mostrata.
- **Togliere l'accesso**: console Appwrite → Auth → utente → togliere l'etichetta `biblioteca`
  (oppure bloccare o eliminare l'utente). Le sessioni già aperte smettono di funzionare entro 5 minuti;
  per chiuderle subito, eliminarle dalla scheda Sessions dell'utente.
- Il backend apre la sessione Appwrite e la conserva in un cookie `httpOnly` (180 giorni);
  il browser non riceve mai la chiave API.
- Dopo 10 password sbagliate per la stessa email il login si blocca per 15 minuti.

La chiave API deve avere gli scopes: tutta la categoria **Database**, `users.read`, `users.write`
e `sessions.write`.

Senza Appwrite configurato (solo file `.db3` locali) il login è disattivato.

## Pubblicazione su Render

L'app online è **un solo servizio web**: il `Dockerfile` compila il frontend e FastAPI serve sia il
sito sia le API dallo stesso indirizzo (così il cookie di accesso funziona senza configurazioni CORS).
La configurazione è in `render.yaml`.

1. Su [render.com](https://render.com) → **New → Blueprint** → collegare GitHub e scegliere questo repository.
2. Render legge `render.yaml` e chiede il valore di **`APPWRITE_API_KEY`** (la stessa chiave del file `.env`).
3. **Deploy**. A ogni push su `main` Render ripubblica da solo.

Con il piano gratuito il servizio si sospende dopo 15 minuti senza visite: la prima apertura
successiva richiede circa un minuto.

Per provare in locale la versione "di produzione" (un solo server sulla porta 8000):
```powershell
cd frontend; npm run build; cd ..
.venv\Scripts\uvicorn backend.main:app --port 8000
```

## Più biblioteche con file locali

In alternativa ad Appwrite, le biblioteche si possono elencare in `biblioteche.json` nella cartella
principale (escluso dal repository; c'è un esempio in `biblioteche.example.json`). Se il file esiste,
ha la precedenza su Appwrite:

```json
[
  { "id": "biblioteca1", "nome": "Casa",       "file": "Biblioteca.db3" },
  { "id": "biblioteca2", "nome": "Parrocchia", "file": "Parrocchia.db3" }
]
```

- **`id`**: identificativo fisso, usato negli indirizzi delle API. Non va cambiato.
- **`nome`**: il nome mostrato nell'app. Si può cambiare anche dall'app (matita accanto al nome).
- **`file`**: il database SQLite, con la stessa struttura di `Biblioteca.db3`
  (oppure `"appwrite": "<id database>"` per una biblioteca su Appwrite).

> ⚠️ Con i file `.db3` l'app scrive **direttamente** sui file: conviene tenerne una copia di sicurezza.

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
  auth.py          login, logout e controllo della sessione (utenti Appwrite)
  database.py      elenco delle biblioteche (biblioteche.json, Appwrite o default) e connessioni SQL
  appwrite_client.py  collegamento ad Appwrite
  store_appwrite.py   libri su Appwrite (copia in memoria + scritture su Appwrite)
  store_sql.py     libri su SQLite/PostgreSQL
  models.py        mappatura delle tabelle esistenti Biblioteca e Genere
  schemas.py       validazione dei dati in ingresso/uscita (Pydantic)
  main.py          endpoint REST
scripts/
  migra_appwrite.py  migrazione di una biblioteca da .db3 ad Appwrite
  crea_utente.py     crea o abilita un utente che può entrare
frontend/
  src/api/libri.js tutte le chiamate al backend
  src/App.jsx      pagina principale (tabella, ricerca, filtri, paginazione)
  src/components/  finestra inserimento/modifica e componenti UI
tests/
  test_api.py      test del backend su una copia del DB, sia SQLite sia Appwrite simulato
  fake_appwrite.py Appwrite finto in memoria (i test non toccano mai l'Appwrite vero)
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
| POST | `/api/auth/login` | Accesso (`{"email", "password"}`), imposta il cookie di sessione |
| POST | `/api/auth/logout` | Uscita |
| GET | `/api/auth/me` | Utente collegato (`null` se il login è disattivato) |
| GET | `/api/health` | Controllo che il backend sia attivo (unica API senza login) |

Con il login attivo tutte le altre API rispondono `401` senza una sessione valida.

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

## Versioni e novità

La versione dell'app ha un'unica fonte: `"version"` in `frontend/package.json` (attuale: **1.0.0**).
Si vede sotto la pagina e nella pagina di accesso; il backend la restituisce in `/api/health`.

- **Storico**: `frontend/src/data/releases.js`, dal rilascio più recente, con testi semplici per chi usa
  l'app. Si apre cliccando su versione e data in fondo alla pagina.
- **Popup "Novità"**: dopo un rilascio compare una volta per utente, con le novità dalle versioni non
  ancora viste. L'ultima versione vista è salvata nelle preferenze dell'utente su Appwrite
  (`last_seen_version`), quindi vale su tutti i dispositivi. Chi è stato creato dopo il rilascio non lo vede.

Per un nuovo rilascio:
1. aumentare la versione (patch `1.0.1` per correzioni, minor `1.1.0` per novità, major `2.0.0`
   per grandi cambiamenti):
   ```powershell
   cd frontend; npm version 1.0.1 --no-git-tag-version
   ```
2. aggiungere in cima a `releases.js` una voce con la stessa `version`, la data e le novità;
3. commit e push: Render pubblica e al primo accesso compare il popup.

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
