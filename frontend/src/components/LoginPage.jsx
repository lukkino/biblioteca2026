import { useState } from "react"
import { BookOpen, Eye, EyeOff, Loader2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/api/auth"
import { errorMessage } from "@/api/client"

export default function LoginPage({ notice, onLogin }) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError("")
    try {
      onLogin(await login(email.trim(), password))
    } catch (err) {
      setError(errorMessage(err))
      setPassword("")
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <div className="flex size-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <BookOpen className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Biblioteca</h1>
            <p className="text-sm text-muted-foreground">Accedi per consultare e gestire il catalogo</p>
          </div>
        </div>

        <form onSubmit={submit} className="grid gap-4 rounded-xl border bg-card p-6 shadow-sm">
          {notice && !error && (
            <p role="status" className="rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">{notice}</p>
          )}
          {error && (
            <p role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}
          <div className="grid gap-1.5">
            <Label htmlFor="login-email">Email</Label>
            <Input id="login-email" type="email" autoComplete="username" required autoFocus
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="login-password">Password</Label>
            <div className="relative">
              <Input id="login-password" type={show ? "text" : "password"} autoComplete="current-password" required
                className="pr-10" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" onClick={() => setShow(!show)}
                aria-label={show ? "Nascondi password" : "Mostra password"}
                className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground">
                {show ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <Button type="submit" className="h-10" disabled={busy}>
            {busy && <Loader2 className="animate-spin" />} Entra
          </Button>
        </form>
        <p className="mt-4 text-center text-xs text-muted-foreground">v{__APP_VERSION__}</p>
      </div>
    </main>
  )
}
