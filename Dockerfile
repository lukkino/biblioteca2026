# Immagine unica per Render: compila il frontend e lo serve insieme alle API FastAPI.
# Variabili d'ambiente richieste: APPWRITE_ENDPOINT, APPWRITE_PROJECT_ID, APPWRITE_API_KEY.

# 1) frontend (React + Vite)
FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2) backend (FastAPI)
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist

RUN useradd --create-home app
USER app

# Render passa la porta in $PORT; --proxy-headers fa vedere al backend che il sito è in https
# (cookie "Secure") e l'IP vero dei visitatori (blocco dei tentativi di login).
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips '*'"]
