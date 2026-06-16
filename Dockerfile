# DURCI Phase 4 : image slim officielle déjà en place — réduit la surface
# d'attaque par rapport à python:3.11 complet (moins de paquets OS = moins de CVE)
FROM python:3.11-slim

# DURCI Phase 4 : pas de bytecode .pyc écrit sur un FS en lecture seule,
# logs non bufferisés, et pip ne doit jamais utiliser de cache local
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .

# DURCI Phase 4 : aucun outil supplémentaire installé (pas d'apt-get) —
# l'image slim ne contient déjà ni compilateur ni shell utilitaire superflu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# DURCI Phase 4 : utilisateur applicatif non privilégié — corrige la
# vulnérabilité root intentionnelle de la Phase 1. UID fixe (non-système)
# pour rester compatible avec securityContext.runAsUser en Kubernetes.
RUN groupadd -g 1000 appuser && useradd -m -g appuser -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# DURCI Phase 4 : health check natif Python (pas de paquet curl/wget ajouté,
# donc surface d'attaque minimale) — vérifie /health toutes les 30s
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
