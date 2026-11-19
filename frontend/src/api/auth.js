import client from "./client";

// null = login disattivato (backend senza Appwrite, solo file locali)
export const getMe = () => client.get("/api/auth/me").then((r) => r.data);
export const login = (email, password) => client.post("/api/auth/login", { email, password }).then((r) => r.data);
export const logout = () => client.post("/api/auth/logout");
// segna che l'utente ha visto le novità fino a questa versione; restituisce l'utente aggiornato
export const setVersioneVista = (version) =>
  client.post("/api/auth/versione-vista", { version }).then((r) => r.data);
