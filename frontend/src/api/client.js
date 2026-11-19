import axios from "axios";

// In dev le chiamate /api passano dal proxy di Vite verso FastAPI (porta 8000).
// Il login usa un cookie httpOnly impostato dal backend: lo stesso indirizzo serve app e API.
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Sessione scaduta o revocata: avvisa AuthGate, che torna alla pagina di accesso.
client.interceptors.response.use(undefined, (err) => {
  const url = err?.config?.url || "";
  if (err?.response?.status === 401 && !url.startsWith("/api/auth/")) {
    window.dispatchEvent(new Event("auth:expired"));
  }
  return Promise.reject(err);
});

export function errorMessage(err) {
  const d = err?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(", ");
  return d || err?.message || "Errore imprevisto";
}

export default client;
