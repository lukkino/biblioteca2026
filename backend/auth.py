# backend/auth.py
"""Login con gli utenti di Appwrite.

- Il browser manda email e password a POST /api/auth/login; il backend apre una sessione
  Appwrite e ne salva il "secret" in un cookie httpOnly (JavaScript non lo può leggere).
- Possono entrare solo gli utenti con l'etichetta (label) "biblioteca" in Appwrite:
  avere un account nel progetto non basta.
- Le sessioni valide restano in memoria per SESSION_CACHE_TTL secondi, per non
  interrogare Appwrite a ogni richiesta.
- Troppi tentativi sbagliati bloccano il login per un po' (con la API key Appwrite non
  applica i suoi limiti, quindi li applichiamo qui).

Senza Appwrite configurato (solo file .db3 locali) il login è disattivato.
"""
from __future__ import annotations

import hashlib
import threading
import time

from appwrite.exception import AppwriteException
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend import appwrite_client

COOKIE = "biblioteca_sessione"
LABEL = "biblioteca"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 giorni (la sessione Appwrite dura fino a 1 anno)
SESSION_CACHE_TTL = 300
MAX_FAILS_EMAIL = 10                 # tentativi sbagliati per email...
MAX_FAILS_IP = 30                    # ...e per indirizzo IP
FAIL_WINDOW = 15 * 60                # nell'arco di 15 minuti
CREDENZIALI_ERRATE = {"user_invalid_credentials", "user_not_found", "user_password_mismatch", "user_blocked"}

router = APIRouter(prefix="/api/auth")

_lock = threading.Lock()
_sessions: dict[str, tuple[float, dict]] = {}   # hash(secret) -> (scadenza cache, utente)
_fails: dict[str, list[float]] = {}             # "email:..." / "ip:..." -> orari dei tentativi falliti


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    name: str
    email: str
    created_at: str | None = None
    last_seen_version: str | None = None   # ultima versione di cui ha visto le novità

    @classmethod
    def of(cls, user: dict) -> "UserOut":
        return cls(name=user["name"] or user["email"], email=user["email"], created_at=user.get("created_at"),
                   last_seen_version=(user.get("prefs") or {}).get("last_seen_version"))


class VersioneVistaIn(BaseModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")


def enabled() -> bool:
    return appwrite_client.configured()


def _h(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _client_ip(request: Request) -> str:
    # dietro il proxy di Render l'IP vero è l'ultimo aggiunto (i primi li può inventare il client)
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "?")


def _recent(key: str, now: float) -> list[float]:
    times = [t for t in _fails.get(key, []) if now - t < FAIL_WINDOW]
    _fails[key] = times
    return times


def _check_rate(keys: list[tuple[str, int]]) -> None:
    now = time.monotonic()
    with _lock:
        if any(len(_recent(k, now)) >= limit for k, limit in keys):
            raise HTTPException(429, "Troppi tentativi sbagliati. Riprova tra qualche minuto.")


def _add_fail(keys: list[str]) -> None:
    now = time.monotonic()
    with _lock:
        for k in keys:
            _recent(k, now).append(now)


def _user_or_none(secret: str | None) -> dict | None:
    if not secret:
        return None
    key, now = _h(secret), time.monotonic()
    with _lock:
        cached = _sessions.get(key)
        if cached and cached[0] > now:
            return cached[1]
    try:
        user = appwrite_client.user_for_session(secret)
    except AppwriteException as e:
        if e.code in (401, 403, 404):
            with _lock:
                _sessions.pop(key, None)
            return None
        raise
    if LABEL not in user["labels"]:
        return None
    with _lock:
        _sessions[key] = (now + SESSION_CACHE_TTL, user)
    return user


def require_user(request: Request) -> dict | None:
    """Dipendenza FastAPI: 401 se non c'è un utente autenticato (quando il login è attivo)."""
    if not enabled():
        return None
    user = _user_or_none(request.cookies.get(COOKIE))
    if user is None:
        raise HTTPException(401, "Accesso richiesto")
    return user


def _set_cookie(response: Response, request: Request, secret: str) -> None:
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        COOKIE, secret, max_age=COOKIE_MAX_AGE, httponly=True, secure=https, samesite="lax", path="/",
    )


@router.get("/me", response_model=UserOut | None)
def me(request: Request):
    """Utente collegato; null se il login è disattivato (solo file locali)."""
    user = require_user(request)
    return UserOut.of(user) if user else None


@router.post("/versione-vista", response_model=UserOut)
def versione_vista(data: VersioneVistaIn, request: Request):
    """Segna che l'utente ha visto le novità fino a questa versione (popup "Novità")."""
    current = require_user(request)
    if current is None:
        raise HTTPException(400, "Login non attivo")
    secret = request.cookies[COOKIE]
    # una sola chiamata ad Appwrite: le altre preferenze sono già note dalla sessione
    prefs = {**(current.get("prefs") or {}), "last_seen_version": data.version}
    user = appwrite_client.update_prefs(secret, prefs)
    with _lock:
        _sessions[_h(secret)] = (time.monotonic() + SESSION_CACHE_TTL, user)
    return UserOut.of(user)


@router.post("/login", response_model=UserOut)
def login(data: LoginIn, request: Request, response: Response):
    if not enabled():
        raise HTTPException(400, "Login non attivo (Appwrite non configurato)")
    email = data.email.strip().lower()
    keys = [(f"email:{email}", MAX_FAILS_EMAIL), (f"ip:{_client_ip(request)}", MAX_FAILS_IP)]
    _check_rate(keys)
    try:
        secret, user = appwrite_client.login(email, data.password)
    except AppwriteException as e:
        # solo le credenziali sbagliate sono "password errata"; il resto (es. chiave API senza
        # permessi) è un problema del server e va nei log, non va confuso con un tentativo fallito
        if e.type in CREDENZIALI_ERRATE or (e.code == 400 and e.type == "general_argument_invalid"):
            _add_fail([k for k, _ in keys])
            if e.type == "user_blocked":
                raise HTTPException(403, "Questo utente è bloccato") from None
            raise HTTPException(401, "Email o password non corretti") from None
        raise
    if LABEL not in user["labels"]:
        try:
            appwrite_client.logout(secret)
        except AppwriteException:
            pass
        _add_fail([k for k, _ in keys])
        raise HTTPException(403, "Questo utente non è abilitato alla biblioteca")
    with _lock:
        _sessions[_h(secret)] = (time.monotonic() + SESSION_CACHE_TTL, user)
    _set_cookie(response, request, secret)
    return UserOut.of(user)


@router.post("/logout", status_code=204)
def logout(request: Request):
    secret = request.cookies.get(COOKIE)
    if secret:
        with _lock:
            _sessions.pop(_h(secret), None)
        try:
            appwrite_client.logout(secret)
        except AppwriteException:
            pass  # sessione già scaduta o eliminata
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response
