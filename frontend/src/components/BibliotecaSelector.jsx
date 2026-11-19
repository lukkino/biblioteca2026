import { useState } from "react"
import { ChevronDown, Loader2, Pencil } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { errorMessage, renameBiblioteca } from "@/api/libri"

/** Selettore della biblioteca corrente (es. Casa / Parrocchia) + rinomina. */
export default function BibliotecaSelector({ biblioteche, value, onChange, onRenamed }) {
  const [renaming, setRenaming] = useState(false)
  const current = biblioteche.find((b) => b.id === value)

  return (
    <div className="flex min-w-0 items-center gap-1">
      {/* il nome è un testo normale (si accorcia con "…" solo se manca spazio); sopra c'è la
          tendina nativa trasparente, così su telefono si apre il selettore del sistema */}
      <div className="relative min-w-0">
        <select
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          aria-label="Biblioteca"
          className="peer absolute inset-0 z-10 w-full cursor-pointer appearance-none opacity-0"
        >
          {biblioteche.map((b) => (
            <option key={b.id} value={b.id}>
              {b.nome}{b.disponibile ? "" : " (non disponibile)"}
            </option>
          ))}
        </select>
        <span aria-hidden="true"
          className="-ml-1 block truncate rounded-md py-0.5 pl-1 pr-6 text-lg font-semibold leading-tight peer-hover:bg-muted peer-focus-visible:ring-2 peer-focus-visible:ring-ring/50">
          {current?.nome ?? "Biblioteca"}
        </span>
        <ChevronDown className="pointer-events-none absolute right-1 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      </div>
      {current && (
        <Button variant="ghost" size="icon" className="size-7 shrink-0 text-muted-foreground"
          aria-label="Rinomina biblioteca" onClick={() => setRenaming(true)}>
          <Pencil className="size-3.5" />
        </Button>
      )}
      {renaming && current && (
        <RenameDialog
          biblioteca={current}
          onClose={() => setRenaming(false)}
          onSaved={(b) => { setRenaming(false); onRenamed(b) }}
        />
      )}
    </div>
  )
}

function RenameDialog({ biblioteca, onClose, onSaved }) {
  const [nome, setNome] = useState(biblioteca.nome)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  async function submit(e) {
    e.preventDefault()
    if (!nome.trim()) return setError("Il nome è obbligatorio")
    setSaving(true)
    setError("")
    try {
      onSaved(await renameBiblioteca(biblioteca.id, nome.trim()))
    } catch (err) {
      setError(errorMessage(err))
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Rinomina biblioteca</DialogTitle>
          <DialogDescription>
            {biblioteca.sorgente === "Appwrite" ? "Database online (Appwrite)" : `File: ${biblioteca.sorgente}`}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="b-nome">Nome</Label>
            <Input id="b-nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={60}
              autoFocus className="h-9" placeholder="es. Casa, Parrocchia" />
          </div>
          {error && <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" className="h-9" onClick={onClose}>Annulla</Button>
            <Button type="submit" className="h-9 px-4" disabled={saving}>
              {saving && <Loader2 className="animate-spin" />} Salva
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
