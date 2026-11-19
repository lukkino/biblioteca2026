import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { RELEASES } from "@/data/releases"
import { formatData, nomeMese } from "@/lib/versions"

// Raggruppa i rilasci (già dal più recente) per mese "YYYY-MM"
function groupByMonth(releases) {
  const groups = []
  for (const r of releases) {
    const key = r.date.slice(0, 7)
    const last = groups[groups.length - 1]
    if (last && last.key === key) last.items.push(r)
    else groups.push({ key, items: [r] })
  }
  return groups
}

/** Storico delle versioni ("Novità e versioni"). */
export default function ReleasesDialog({ open, onOpenChange }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Novità e versioni</DialogTitle>
          <DialogDescription>
            Versione attuale {__APP_VERSION__} · ultimo aggiornamento {formatData(__APP_LAST_UPDATE__)}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5">
          {groupByMonth(RELEASES).map(({ key, items }) => (
            <section key={key}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{nomeMese(key)}</h3>
              <div className="divide-y rounded-lg border">
                {items.map((r) => (
                  <div key={`${r.date}-${r.version}`} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:gap-5">
                    <div className="flex shrink-0 items-baseline gap-2 sm:w-28 sm:flex-col sm:items-start sm:gap-1">
                      <span className="text-sm font-semibold">{formatData(r.date)}</span>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">v{r.version}</span>
                    </div>
                    <ul className="list-disc space-y-1 pl-5 text-sm">
                      {r.items.map((line, i) => <li key={i}>{line}</li>)}
                    </ul>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
