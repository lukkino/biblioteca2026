import { useState } from "react"
import { Loader2, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { createLibro, errorMessage, updateLibro } from "@/api/libri"

const EMPTY = {
  titolo: "", autore: "", editore: "", anno: "", codice: "",
  collocazione: "", premi: "", note: "", genere_id: "",
}

function toForm(libro) {
  if (!libro) return EMPTY
  const f = { ...EMPTY }
  for (const k of Object.keys(EMPTY)) f[k] = libro[k] ?? ""
  return f
}

function toPayload(form) {
  const out = {}
  for (const [k, v] of Object.entries(form)) {
    if (k === "genere_id") out[k] = v === "" ? null : Number(v)
    else out[k] = v.trim() === "" ? null : v.trim()
  }
  out.titolo = form.titolo.trim()
  return out
}

export const selectCls =
  "h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 dark:bg-input/30"

/**
 * Form inserimento / modifica. `libro` null = nuovo libro.
 * Il componente va montato con una `key` diversa per ogni libro così lo stato si resetta.
 */
export default function BookFormDialog({ open, onOpenChange, libro, generi, onSaved, onDelete }) {
  const [form, setForm] = useState(() => toForm(libro))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const isEdit = Boolean(libro)

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.titolo.trim()) {
      setError("Il titolo è obbligatorio")
      return
    }
    setSaving(true)
    setError("")
    try {
      const payload = toPayload(form)
      const saved = isEdit ? await updateLibro(libro.id, payload) : await createLibro(payload)
      onSaved(saved, isEdit)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const field = (k, label, props = {}) => (
    <div className="grid gap-1.5">
      <Label htmlFor={`f-${k}`}>{label}</Label>
      <Input id={`f-${k}`} value={form[k]} onChange={set(k)} className="h-9" {...props} />
    </div>
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Modifica libro" : "Nuovo libro"}</DialogTitle>
          <DialogDescription>
            {isEdit ? `ID ${libro.id}` : "Inserisci i dati del libro. Solo il titolo è obbligatorio."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">{field("titolo", "Titolo *", { autoFocus: true, required: true })}</div>
            {field("autore", "Autore", { placeholder: "Cognome Nome" })}
            {field("editore", "Editore")}
            {field("anno", "Anno", { inputMode: "numeric", maxLength: 20 })}
            <div className="grid gap-1.5">
              <Label htmlFor="f-genere">Genere</Label>
              <select id="f-genere" value={form.genere_id} onChange={set("genere_id")} className={selectCls}>
                <option value="">— Nessun genere —</option>
                {generi.map((g) => (
                  <option key={g.id} value={g.id}>{g.descrizione}</option>
                ))}
              </select>
            </div>
            {field("codice", "Codice libro")}
            {field("collocazione", "Collocazione", { placeholder: "sc. 1 - rip. 1 - n. 1" })}
            <div className="sm:col-span-2">{field("premi", "Premi")}</div>
            <div className="grid gap-1.5 sm:col-span-2">
              <Label htmlFor="f-note">Note</Label>
              <textarea
                id="f-note"
                value={form.note}
                onChange={set("note")}
                rows={3}
                className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/50 dark:bg-input/30"
              />
            </div>
          </div>

          {error && (
            <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}

          <DialogFooter className="sm:justify-between">
            {isEdit ? (
              <Button type="button" variant="destructive" className="h-9" onClick={() => onDelete(libro)}>
                <Trash2 /> Elimina
              </Button>
            ) : <span />}
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button type="button" variant="outline" className="h-9" onClick={() => onOpenChange(false)}>
                Annulla
              </Button>
              <Button type="submit" className="h-9 px-4" disabled={saving}>
                {saving && <Loader2 className="animate-spin" />}
                {isEdit ? "Salva modifiche" : "Aggiungi libro"}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
