// Quali novità mostrare nel popup "Novità", in base all'ultima versione vista
// dall'utente (salvata nelle sue preferenze su Appwrite).

// "1.5.0" -> [1, 5, 0]; null se il formato non è riconosciuto
export function versionKey(v) {
  const m = /^(\d+)\.(\d+)\.(\d+)/.exec(v || "")
  return m ? m.slice(1).map(Number) : null
}

// > 0 se a è più recente di b, 0 se uguali, < 0 se più vecchia
export function compareVersions(a, b) {
  const ka = versionKey(a), kb = versionKey(b)
  for (let i = 0; i < 3; i++) {
    if (ka[i] !== kb[i]) return ka[i] - kb[i]
  }
  return 0
}

/**
 * Restituisce { entries, markSilently }:
 * - entries: voci da mostrare (dalla più recente); vuoto = niente popup
 * - markSilently: true se la versione corrente va segnata come vista senza mostrare
 *   nulla (utente creato dopo il rilascio, nessuna voce per questa versione…)
 *
 * Se l'utente non ha mai visto una versione si mostra solo la voce della versione
 * corrente, non tutto lo storico; chi è stato creato dopo l'uscita della versione
 * corrente non vede niente.
 */
export function pendingReleases({ releases, current, lastSeen, createdAt }) {
  const none = { entries: [], markSilently: false }
  if (!versionKey(current)) return none
  if (versionKey(lastSeen) && compareVersions(current, lastSeen) <= 0) return none

  if (!versionKey(lastSeen)) {
    const top = releases.find((r) => r.version === current)
    const createdAfter = top && createdAt && String(createdAt).slice(0, 10) >= top.date
    if (!top || createdAfter) return { entries: [], markSilently: true }
    return { entries: [top], markSilently: false }
  }

  const entries = releases.filter((r) =>
    versionKey(r.version)
    && compareVersions(r.version, lastSeen) > 0
    && compareVersions(r.version, current) <= 0,
  )
  return entries.length ? { entries, markSilently: false } : { entries: [], markSilently: true }
}

const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
  "settembre", "ottobre", "novembre", "dicembre"]

// "2026-11-19" (o ISO completo) -> "19 novembre 2026"
export function formatData(iso) {
  const [y, m, d] = String(iso).slice(0, 10).split("-").map(Number)
  return `${d} ${MESI[m - 1]} ${y}`
}

export function nomeMese(yyyyMm) {
  const [y, m] = yyyyMm.split("-").map(Number)
  return `${MESI[m - 1]} ${y}`
}
