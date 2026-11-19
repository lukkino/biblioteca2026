// Unico punto di accesso ai dati: quando passeremo a Supabase basta
// reimplementare queste funzioni (stessa firma) con @supabase/supabase-js.
// `bid` = id della biblioteca (es. "biblioteca1"), vedi biblioteche.json nel backend.
import client from "./client";

const b = (bid) => `/api/b/${encodeURIComponent(bid)}`;

export const getBiblioteche = () => client.get("/api/biblioteche").then((r) => r.data);
export const renameBiblioteca = (bid, nome) =>
  client.patch(`/api/biblioteche/${encodeURIComponent(bid)}`, { nome }).then((r) => r.data);

export const getLibri = (bid, params) => client.get(`${b(bid)}/libri`, { params }).then((r) => r.data);
export const getLibro = (bid, id) => client.get(`${b(bid)}/libri/${id}`).then((r) => r.data);
export const createLibro = (bid, data) => client.post(`${b(bid)}/libri`, data).then((r) => r.data);
export const updateLibro = (bid, id, data) => client.put(`${b(bid)}/libri/${id}`, data).then((r) => r.data);
export const deleteLibro = (bid, id) => client.delete(`${b(bid)}/libri/${id}`);
export const getGeneri = (bid) => client.get(`${b(bid)}/generi`).then((r) => r.data);
export const getStats = (bid) => client.get(`${b(bid)}/stats`).then((r) => r.data);
export { errorMessage } from "./client";
