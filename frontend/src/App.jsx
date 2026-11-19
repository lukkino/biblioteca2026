import { useCallback, useEffect, useState } from "react"
import {
  ArrowDown, ArrowUp, ArrowUpDown, BookOpen, ChevronLeft, ChevronRight, DatabaseZap, Loader2,
  LogOut, Moon, Pencil, Plus, Search, Sun, Trash2, X,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ConfirmDialog } from "@/components/ui/dialog"
import BookFormDialog, { selectCls } from "@/components/BookFormDialog"
import BibliotecaSelector from "@/components/BibliotecaSelector"
import ReleasesDialog from "@/components/ReleasesDialog"
import WhatsNewDialog from "@/components/WhatsNewDialog"
import { RELEASES } from "@/data/releases"
import { formatData, pendingReleases } from "@/lib/versions"
import { deleteLibro, errorMessage, getBiblioteche, getGeneri, getLibri, getStats } from "@/api/libri"
import { useAuth } from "@/lib/auth"
import { cn } from "@/lib/utils"

const PAGE_SIZES = [25, 50, 100]

const COLUMNS = [
  { key: "titolo", label: "Titolo" },
  { key: "autore", label: "Autore" },
  { key: "editore", label: "Editore", className: "hidden lg:table-cell" },
  { key: "anno", label: "Anno", className: "w-20" },
  { key: "genere", label: "Genere", className: "hidden md:table-cell" },
  { key: "collocazione", label: "Collocazione", className: "hidden xl:table-cell" },
]

function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}

function useDarkMode() {
  const [dark, setDark] = useState(() => {
    try {
      const saved = localStorage.getItem("theme")
      if (saved) return saved === "dark"
    } catch { /* storage non disponibile */ }
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false
  })
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark)
    try { localStorage.setItem("theme", dark ? "dark" : "light") } catch { /* ignore */ }
  }, [dark])
  return [dark, setDark]
}

// Popup "Novità" una volta per versione: si basa sull'ultima versione vista dall'utente
// (preferenze su Appwrite, quindi vale su tutti i dispositivi).
// La versione è segnata come vista appena il popup compare (non alla chiusura): così il
// popup esce davvero una volta sola, anche se si chiude la scheda senza toccarlo.
function useWhatsNew(user, markVersionSeen) {
  const current = __APP_VERSION__
  const { entries, markSilently } = user
    ? pendingReleases({ releases: RELEASES, current, lastSeen: user.last_seen_version, createdAt: user.created_at })
    : { entries: [], markSilently: false }

  // voci mostrate nel popup, fissate alla prima comparsa (dopo il salvataggio "entries" si svuota)
  const [shown, setShown] = useState(null)
  if (shown === null && entries.length > 0) setShown(entries)

  const toMark = markSilently || (shown?.length ?? 0) > 0
  useEffect(() => {
    if (toMark) markVersionSeen(current)
  }, [toMark, markVersionSeen, current])

  const close = useCallback(() => setShown([]), [])
  return { entries: shown ?? [], close }
}

function readSavedBiblioteca() {
  try { return localStorage.getItem("biblioteca") } catch { return null }
}

export default function App() {
  const [dark, setDark] = useDarkMode()
  const { user, logout, markVersionSeen } = useAuth()
  const whatsNew = useWhatsNew(user, markVersionSeen)
  const [showReleases, setShowReleases] = useState(false)

  // biblioteche (es. Casa / Parrocchia): ognuna ha il suo DB
  const [biblioteche, setBiblioteche] = useState(null) // null = in caricamento
  const [bibliotecheError, setBibliotecheError] = useState("")
  const [savedBid, setSavedBid] = useState(readSavedBiblioteca)
  const current = biblioteche
    ? biblioteche.find((b) => b.id === savedBid) ?? biblioteche.find((b) => b.disponibile) ?? biblioteche[0]
    : null
  const bid = current?.id
  const canLoad = Boolean(current?.disponibile)

  const reloadBiblioteche = useCallback(() => {
    getBiblioteche()
      .then((l) => { setBiblioteche(l); setBibliotecheError("") })
      .catch((e) => setBibliotecheError(errorMessage(e)))
  }, [])
  useEffect(() => { reloadBiblioteche() }, [reloadBiblioteche])

  // filtri
  const [search, setSearch] = useState("")
  const [genereId, setGenereId] = useState("")
  const [sort, setSort] = useState({ key: "titolo", order: "asc" })
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const q = useDebounced(search)

  // dati
  const [data, setData] = useState({ items: [], total: 0 })
  const [generi, setGeneri] = useState([])
  const [stats, setStats] = useState(null)
  const [error, setError] = useState("")
  const [reloadKey, setReloadKey] = useState(0)

  // dialog
  const [editing, setEditing] = useState(null) // {libro|null} quando aperto
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [toast, setToast] = useState("")

  // generi e statistiche della biblioteca corrente; metaKey++ per ricaricarli
  const [metaKey, setMetaKey] = useState(0)
  const refreshMeta = useCallback(() => {
    setMetaKey((k) => k + 1)
    reloadBiblioteche() // aggiorna anche il numero di libri nel selettore
  }, [reloadBiblioteche])

  useEffect(() => {
    if (!canLoad) return
    let cancelled = false
    getGeneri(bid).then((g) => { if (!cancelled) setGeneri(g) }).catch(() => {})
    getStats(bid).then((s) => { if (!cancelled) setStats(s) }).catch(() => {})
    return () => { cancelled = true }
  }, [bid, canLoad, metaKey])

  function changeBiblioteca(id) {
    if (id === bid) return
    try { localStorage.setItem("biblioteca", id) } catch { /* ignore */ }
    setSavedBid(id)
    // i generi sono diversi in ogni DB: azzero filtro e dati della biblioteca precedente
    setGenereId("")
    setData({ items: [], total: 0 })
    setGeneri([])
    setStats(null)
    setError("")
    setEditing(null)
    setToDelete(null)
  }

  // reset pagina quando cambiano i filtri o la biblioteca (aggiustamento durante il render)
  const filterKey = `${bid}|${q}|${genereId}|${pageSize}`
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey)
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey)
    setPage(1)
  }

  // "loading" = la richiesta corrente non è ancora conclusa
  const requestKey = JSON.stringify([bid, q, genereId, sort, page, pageSize, reloadKey])
  const [doneKey, setDoneKey] = useState(null)
  const loading = canLoad && doneKey !== requestKey

  useEffect(() => {
    if (!canLoad) return
    let cancelled = false
    getLibri(bid, {
      q: q || undefined,
      genere_id: genereId === "" ? undefined : genereId,
      sort: sort.key,
      order: sort.order,
      page,
      page_size: pageSize,
    })
      .then((d) => { if (!cancelled) { setData(d); setError("") } })
      .catch((e) => { if (!cancelled) setError(errorMessage(e)) })
      .finally(() => { if (!cancelled) setDoneKey(requestKey) })
    return () => { cancelled = true }
  }, [bid, canLoad, q, genereId, sort, page, pageSize, reloadKey, requestKey])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(""), 2800)
    return () => clearTimeout(t)
  }, [toast])

  const totalPages = Math.max(1, Math.ceil(data.total / pageSize))
  const from = data.total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, data.total)
  const hasFilters = search !== "" || genereId !== ""

  function toggleSort(key) {
    setSort((s) => (s.key === key ? { key, order: s.order === "asc" ? "desc" : "asc" } : { key, order: "asc" }))
  }

  function handleSaved(libro, isEdit) {
    setEditing(null)
    setToast(isEdit ? `“${libro.titolo}” aggiornato` : `“${libro.titolo}” aggiunto`)
    setReloadKey((k) => k + 1)
    refreshMeta()
  }

  async function confirmDelete() {
    setDeleting(true)
    try {
      await deleteLibro(bid, toDelete.id)
      setToast(`“${toDelete.titolo}” eliminato`)
      setToDelete(null)
      setEditing(null)
      if (data.items.length === 1 && page > 1) setPage((p) => p - 1)
      setReloadKey((k) => k + 1)
      refreshMeta()
    } catch (e) {
      setToast(errorMessage(e))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <BookOpen className="size-5" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="sr-only">Biblioteca{current ? ` – ${current.nome}` : ""}</h1>
            {biblioteche ? (
              <BibliotecaSelector
                biblioteche={biblioteche}
                value={bid}
                onChange={changeBiblioteca}
                onRenamed={(b) => { setToast(`Biblioteca rinominata in “${b.nome}”`); reloadBiblioteche() }}
              />
            ) : (
              <p className="text-lg font-semibold leading-tight">Biblioteca</p>
            )}
            {canLoad && stats && (
              <p className="truncate text-xs text-muted-foreground">
                {stats.totale_libri.toLocaleString("it-IT")} libri · {stats.totale_autori.toLocaleString("it-IT")} autori · {stats.totale_generi} generi
              </p>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={() => setDark(!dark)} aria-label="Cambia tema">
            {dark ? <Sun /> : <Moon />}
          </Button>
          <Button className="h-9 px-3" disabled={!canLoad} onClick={() => setEditing({ libro: null })}>
            <Plus /> <span className="hidden sm:inline">Nuovo libro</span>
          </Button>
          {user && (
            <Button variant="ghost" size="icon" onClick={logout}
              aria-label={`Esci (${user.name})`} title={`${user.name} – Esci`}>
              <LogOut />
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-5">
        {bibliotecheError && (
          <div role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Impossibile caricare le biblioteche: {bibliotecheError}. Il backend è avviato sulla porta 8000?
          </div>
        )}

        {current && !canLoad && (
          <div className="flex flex-col items-center gap-3 rounded-xl border bg-card px-6 py-16 text-center">
            <DatabaseZap className="size-10 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Il database di “{current.nome}” non è ancora disponibile</h2>
            {current.sorgente === "Appwrite" ? (
              <p className="max-w-md text-sm text-muted-foreground">
                Il database online non risponde. Riprova tra qualche minuto ricaricando la pagina.
              </p>
            ) : (
              <p className="max-w-md break-all text-sm text-muted-foreground">
                {/[\\/:]/.test(current.sorgente) ? "Il file " : "Copia il file "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-foreground">{current.sorgente}</code>
                {/[\\/:]/.test(current.sorgente)
                  ? " non è stato trovato. Controlla il percorso in biblioteche.json e ricarica la pagina."
                  : " nella cartella del progetto (accanto a Biblioteca.db3) e ricarica la pagina."}
              </p>
            )}
            {biblioteche.some((b) => b.disponibile && b.id !== current.id) && (
              <Button variant="outline" className="mt-2 h-9"
                onClick={() => changeBiblioteca(biblioteche.find((b) => b.disponibile && b.id !== current.id).id)}>
                Vai a “{biblioteche.find((b) => b.disponibile && b.id !== current.id).nome}”
              </Button>
            )}
          </div>
        )}

        {canLoad && (<>
        {/* Toolbar ricerca */}
        <div className="mb-4 flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cerca per titolo, autore, editore, codice, collocazione…"
              className="h-10 bg-card pl-9 pr-9"
              aria-label="Cerca libri"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
                aria-label="Cancella ricerca"
              >
                <X className="size-4" />
              </button>
            )}
          </div>
          <select
            value={genereId}
            onChange={(e) => setGenereId(e.target.value)}
            className={cn(selectCls, "h-10 bg-card sm:w-56")}
            aria-label="Filtra per genere"
          >
            <option value="">Tutti i generi</option>
            {generi.map((g) => (
              <option key={g.id} value={g.id}>{g.descrizione} ({g.totale})</option>
            ))}
            {stats?.senza_genere > 0 && <option value="-1">Senza genere ({stats.senza_genere})</option>}
          </select>
          {hasFilters && (
            <Button variant="outline" className="h-10" onClick={() => { setSearch(""); setGenereId("") }}>
              Azzera filtri
            </Button>
          )}
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            Impossibile caricare i libri: {error}. Il backend è avviato sulla porta 8000?
          </div>
        )}

        {/* Tabella (desktop) */}
        <div className="relative overflow-hidden rounded-xl border bg-card">
          {loading && (
            <div className="absolute inset-x-0 top-0 h-0.5 overflow-hidden">
              <div className="h-full w-1/3 animate-pulse bg-primary" />
            </div>
          )}

          <table className="hidden w-full text-sm sm:table">
            <thead className="border-b bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} className={cn("px-3 py-2.5 font-medium", c.className)}>
                    <button onClick={() => toggleSort(c.key)} className="inline-flex items-center gap-1 hover:text-foreground">
                      {c.label}
                      {sort.key === c.key
                        ? (sort.order === "asc" ? <ArrowUp className="size-3" /> : <ArrowDown className="size-3" />)
                        : <ArrowUpDown className="size-3 opacity-40" />}
                    </button>
                  </th>
                ))}
                <th className="w-24 px-3 py-2.5"><span className="sr-only">Azioni</span></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((b) => (
                <tr
                  key={b.id}
                  onClick={() => setEditing({ libro: b })}
                  className="group cursor-pointer border-b last:border-0 hover:bg-accent/60"
                >
                  <td className="px-3 py-2.5">
                    <div className="font-medium">{b.titolo}</div>
                    {b.premi && <div className="text-xs text-amber-700 dark:text-amber-400">🏆 {b.premi}</div>}
                  </td>
                  <td className="px-3 py-2.5 text-muted-foreground">{b.autore}</td>
                  <td className="hidden px-3 py-2.5 text-muted-foreground lg:table-cell">{b.editore}</td>
                  <td className="px-3 py-2.5 tabular-nums text-muted-foreground">{b.anno}</td>
                  <td className="hidden px-3 py-2.5 md:table-cell">
                    {b.genere
                      ? <span className="rounded-full bg-secondary px-2 py-0.5 text-xs">{b.genere}</span>
                      : <span className="text-xs text-muted-foreground">—</span>}
                  </td>
                  <td className="hidden px-3 py-2.5 text-xs text-muted-foreground xl:table-cell">{b.collocazione}</td>
                  <td className="px-3 py-2.5 text-right">
                    <div className="flex justify-end gap-1 opacity-60 group-hover:opacity-100">
                      <Button variant="ghost" size="icon" aria-label="Modifica"
                        onClick={(e) => { e.stopPropagation(); setEditing({ libro: b }) }}>
                        <Pencil />
                      </Button>
                      <Button variant="ghost" size="icon" aria-label="Elimina" className="hover:text-destructive"
                        onClick={(e) => { e.stopPropagation(); setToDelete(b) }}>
                        <Trash2 />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Lista (mobile) */}
          <ul className="divide-y sm:hidden">
            {data.items.map((b) => (
              <li key={b.id}>
                <button onClick={() => setEditing({ libro: b })} className="w-full px-4 py-3 text-left active:bg-accent">
                  <div className="font-medium">{b.titolo}</div>
                  <div className="text-sm text-muted-foreground">{[b.autore, b.editore, b.anno].filter(Boolean).join(" · ")}</div>
                  {b.genere && <span className="mt-1 inline-block rounded-full bg-secondary px-2 py-0.5 text-xs">{b.genere}</span>}
                </button>
              </li>
            ))}
          </ul>

          {!loading && data.items.length === 0 && !error && (
            <div className="flex flex-col items-center gap-2 px-4 py-16 text-center text-muted-foreground">
              <Search className="size-8 opacity-40" />
              <p>Nessun libro trovato{hasFilters ? " con questi filtri" : ""}.</p>
            </div>
          )}
          {loading && data.items.length === 0 && (
            <div className="flex justify-center py-16"><Loader2 className="size-6 animate-spin text-muted-foreground" /></div>
          )}
        </div>

        {/* Paginazione */}
        <div className="mt-4 flex flex-col items-center justify-between gap-3 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <span>
              {from.toLocaleString("it-IT")}–{to.toLocaleString("it-IT")} di {data.total.toLocaleString("it-IT")}
            </span>
            <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}
              className={cn(selectCls, "h-8 w-auto bg-card")} aria-label="Libri per pagina">
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} per pagina</option>)}
            </select>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="outline" className="h-8" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              <ChevronLeft /> Prec.
            </Button>
            <span className="px-2 tabular-nums">Pagina {page} / {totalPages}</span>
            <Button variant="outline" className="h-8" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Succ. <ChevronRight />
            </Button>
          </div>
        </div>
        </>)}
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-6 text-center text-xs text-muted-foreground">
        <button onClick={() => setShowReleases(true)} className="rounded hover:text-foreground hover:underline">
          Biblioteca v{__APP_VERSION__} · aggiornata il {formatData(__APP_LAST_UPDATE__)}
        </button>
      </footer>

      <ReleasesDialog open={showReleases} onOpenChange={setShowReleases} />
      {whatsNew.entries.length > 0 && !showReleases && (
        <WhatsNewDialog
          entries={whatsNew.entries}
          onClose={whatsNew.close}
          onDetails={() => { whatsNew.close(); setShowReleases(true) }}
        />
      )}

      {editing && (
        <BookFormDialog
          key={`${bid}-${editing.libro?.id ?? "new"}`}
          bid={bid}
          open
          onOpenChange={(o) => { if (!o) setEditing(null) }}
          libro={editing.libro}
          generi={generi}
          onSaved={handleSaved}
          onDelete={(b) => setToDelete(b)}
        />
      )}

      <ConfirmDialog
        open={Boolean(toDelete)}
        onOpenChange={(o) => { if (!o) setToDelete(null) }}
        title="Eliminare questo libro?"
        description={toDelete ? `“${toDelete.titolo}”${toDelete.autore ? ` di ${toDelete.autore}` : ""} verrà eliminato definitivamente.` : ""}
        confirmLabel={deleting ? "Elimino…" : "Elimina"}
        busy={deleting}
        onConfirm={confirmDelete}
      />

      {toast && (
        <div role="status" className="fixed bottom-4 left-1/2 z-[60] -translate-x-1/2 rounded-lg bg-foreground px-4 py-2 text-sm text-background shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
