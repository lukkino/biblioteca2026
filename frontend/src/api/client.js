import axios from "axios";

// In dev le chiamate /api passano dal proxy di Vite verso FastAPI (porta 8000).
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  headers: { "Content-Type": "application/json" },
});

export function errorMessage(err) {
  const d = err?.response?.data?.detail;
  if (Array.isArray(d)) return d.map((x) => x.msg).join(", ");
  return d || err?.message || "Errore imprevisto";
}

export default client;
