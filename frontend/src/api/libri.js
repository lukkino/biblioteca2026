// Unico punto di accesso ai dati: quando passeremo a Supabase basta
// reimplementare queste funzioni (stessa firma) con @supabase/supabase-js.
import client from "./client";

export const getLibri = (params) => client.get("/api/libri", { params }).then((r) => r.data);
export const getLibro = (id) => client.get(`/api/libri/${id}`).then((r) => r.data);
export const createLibro = (data) => client.post("/api/libri", data).then((r) => r.data);
export const updateLibro = (id, data) => client.put(`/api/libri/${id}`, data).then((r) => r.data);
export const deleteLibro = (id) => client.delete(`/api/libri/${id}`);
export const getGeneri = () => client.get("/api/generi").then((r) => r.data);
export const getStats = () => client.get("/api/stats").then((r) => r.data);
export { errorMessage } from "./client";
