import { useCallback, useEffect, useState } from "react"
import {
  ArrowDown, ArrowUp, ArrowUpDown, BookOpen, ChevronLeft, ChevronRight, Loader2,
  Moon, Pencil, Plus, Search, Sun, Trash2, X,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ConfirmDialog } from "@/components/ui/dialog"
import BookFormDialog, { selectCls } from "@/components/BookFormDialog"
import { deleteLibro, errorMessage, getGeneri, getLibri, getStats } from "@/api/libri"
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

export default function App() {
  const [dark, setDark] = useDarkMode()

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

  const refreshMeta = useCallback(() => {
    getGeneri().then(setGeneri).catch(() => {})
    getStats().then(setStats).catch(() => {})
  }, [])

  useEffect(() => { refreshMeta() }, [refreshMeta])

  // reset pagina quando cambiano i filtri (aggiustamento durante il render)
  const filterKey = `${q}|${genereId}|${pageSize}`
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey)
  if (filterKey !== prevFilterKey) {
    setPrevFilterKey(filterKey)
    setPage(1)
  }

  // "loading" = la richiesta corrente non è ancora conclusa
  const requestKey = JSON.stringify([q, genereId, sort, page, pageSize, reloadKey])
  const [doneKey, setDoneKey] = useState(null)
  const loading = doneKey !== requestKey

  useEffect(() => {
    let cancelled = false
    getLibri({
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
  }, [q, genereId, sort, page, pageSize, reloadKey, requestKey])

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
      await deleteLibro(toDelete.id)
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
            <h1 className="text-lg font-semibold leading-tight">Biblioteca</h1>
            {stats && (
              <p className="truncate text-xs text-muted-foreground">
                {stats.totale_libri.toLocaleString("it-IT")} libri · {stats.totale_autori.toLocaleString("it-IT")} autori · {stats.totale_generi} generi
              </p>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={() => setDark(!dark)} aria-label="Cambia tema">
            {dark ? <Sun /> : <Moon />}
          </Button>
          <Button className="h-9 px-3" onClick={() => setEditing({ libro: null })}>
            <Plus /> <span className="hidden sm:inline">Nuovo libro</span>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-5">
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
      </main>

      {editing && (
        <BookFormDialog
          key={editing.libro?.id ?? "new"}
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
