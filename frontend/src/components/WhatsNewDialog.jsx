import { Sparkles } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"

const MAX_RIGHE = 8

// Taglia l'elenco a max righe in tutto, mantenendo i gruppi per versione
function limitLines(entries, max) {
  const groups = []
  let used = 0, total = 0
  for (const r of entries) {
    total += r.items.length
    const shown = r.items.slice(0, Math.max(max - used, 0))
    used += shown.length
    if (shown.length) groups.push({ version: r.version, lines: shown })
  }
  return { groups, more: total - used }
}

/** Popup mostrato una volta sola dopo il rilascio di una nuova versione. */
export default function WhatsNewDialog({ entries, onClose, onDetails }) {
  const { groups, more } = limitLines(entries, MAX_RIGHE)
  const showVersions = entries.length > 1

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-5 text-primary" /> Novità della versione {__APP_VERSION__}
          </DialogTitle>
          <DialogDescription>Ecco cosa è cambiato dall'ultima volta.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          {groups.map((g) => (
            <div key={g.version}>
              {showVersions && (
                <span className="mb-1.5 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  v{g.version}
                </span>
              )}
              <ul className="list-disc space-y-1.5 pl-5 text-sm">
                {g.lines.map((line, i) => <li key={i}>{line}</li>)}
              </ul>
            </div>
          ))}
          {more > 0 && <p className="text-xs text-muted-foreground">…e altre {more} novità.</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onDetails}>Tutte le versioni</Button>
          <Button onClick={onClose} autoFocus>Ho capito</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
