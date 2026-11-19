import { useCallback, useEffect, useMemo, useState } from "react"
import { Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import LoginPage from "@/components/LoginPage"
import { getMe, logout as apiLogout } from "@/api/auth"
import { errorMessage } from "@/api/client"
import { AuthContext } from "@/lib/auth"

// Mostra l'app solo a chi ha fatto l'accesso.
// status: "loading" | "in" (dentro) | "out" (pagina di accesso) | "error" (backend non raggiungibile)
export default function AuthGate({ children }) {
  const [state, setState] = useState({ status: "loading" })

  const check = useCallback(() => {
    getMe()
      .then((user) => setState({ status: "in", user }))
      .catch((e) =>
        setState(e?.response?.status === 401 ? { status: "out" } : { status: "error", error: errorMessage(e) }),
      )
  }, [])
  useEffect(() => { check() }, [check])

  useEffect(() => {
    const expired = () => setState({ status: "out", notice: "La sessione è scaduta: accedi di nuovo." })
    window.addEventListener("auth:expired", expired)
    return () => window.removeEventListener("auth:expired", expired)
  }, [])

  const logout = useCallback(async () => {
    try { await apiLogout() } catch { /* in ogni caso torno alla pagina di accesso */ }
    setState({ status: "out", notice: "Sei uscito dalla biblioteca." })
  }, [])

  const ctx = useMemo(() => ({ user: state.user ?? null, logout }), [state.user, logout])

  if (state.status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        <Loader2 className="size-6 animate-spin" aria-label="Caricamento" />
      </div>
    )
  }
  if (state.status === "error") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center">
        <p className="max-w-sm text-sm text-muted-foreground">
          Impossibile contattare il server: {state.error}
        </p>
        <Button variant="outline" onClick={() => { setState({ status: "loading" }); check() }}>Riprova</Button>
      </div>
    )
  }
  if (state.status === "out") {
    return <LoginPage notice={state.notice} onLogin={(user) => setState({ status: "in", user })} />
  }
  return <AuthContext.Provider value={ctx}>{children}</AuthContext.Provider>
}
