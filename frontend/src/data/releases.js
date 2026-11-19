// Storico dei rilasci, mostrato nella finestra "Novità e versioni" e nel popup che
// compare una volta dopo ogni nuova versione.
//
// Dal più recente al più vecchio. I testi sono per chi usa l'app: niente dettagli
// tecnici o di sicurezza; gli interventi solo interni (test, dipendenze,
// configurazione) non compaiono.
//
// Per ogni rilascio:
//   1. aumentare "version" in frontend/package.json
//      (patch 1.0.1 = correzioni, minor 1.1.0 = novità, major 2.0.0 = grandi cambiamenti):
//        cd frontend; npm version 1.0.1 --no-git-tag-version
//   2. aggiungere qui in cima una voce con la stessa `version` e la data del rilascio
//      (più voci possono avere la stessa data).

export const RELEASES = [
  {
    date: "2026-11-19",
    version: "1.0.0",
    items: [
      "La Biblioteca è online: si apre dal browser, da computer, tablet o telefono",
      "Accesso con email e password; l'accesso resta valido sullo stesso dispositivo",
      "Catalogo completo con ricerca libera su titolo, autore, editore, anno, codice, collocazione, premi e note",
      "Filtro per genere (anche \"senza genere\"), ordinamento cliccando sulle colonne, 25, 50 o 100 libri per pagina",
      "Inserimento, modifica ed eliminazione dei libri",
      "Più biblioteche (ad esempio Casa e Parrocchia), da scegliere e rinominare dal menu in alto",
      "Tema chiaro e scuro",
      "Corretti gli anni di pubblicazione sbagliati di 9 libri",
    ],
  },
]
