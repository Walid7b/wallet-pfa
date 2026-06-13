# Wallet PFA — Application Fintech DevSecOps

Application FastAPI servant de **cobaye** pour démontrer un pipeline CI/CD sécurisé
(SAST, scan de secrets, scan CVE, déploiement Kubernetes) dans le cadre d'un PFA DevSecOps.

---

## Structure du projet

```
wallet-pfa/
├── app/
│   ├── main.py          # Point d'entrée FastAPI + lifespan
│   ├── database.py      # Engine SQLAlchemy + session
│   ├── models.py        # User, Account, Transaction (ORM)
│   ├── schemas.py       # Schémas Pydantic (I/O)
│   ├── auth.py          # JWT + hachage mot de passe
│   └── routers/
│       ├── auth_router.py    # POST /register  POST /login
│       └── wallet_router.py  # GET /accounts/me/balance  POST /transfer
├── .github/workflows/
│   └── ci.yml           # Pipeline GitHub Actions (Phase 1 : build)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose

---

## Lancement en local

```bash
# 1. Cloner / se placer dans le répertoire
cd wallet-pfa

# 2. (Optionnel) Copier le fichier d'environnement
cp .env.example .env

# 3. Construire et démarrer les conteneurs
docker compose up --build

# L'API est disponible sur http://localhost:8000
# Documentation Swagger : http://localhost:8000/docs
# Documentation ReDoc   : http://localhost:8000/redoc
```

Pour arrêter :
```bash
docker compose down          # garde les données PostgreSQL
docker compose down -v       # supprime aussi le volume (reset BDD)
```

---

## Endpoints API

| Méthode | Route                   | Auth | Description                        |
|---------|-------------------------|------|------------------------------------|
| POST    | `/register`             | —    | Créer un compte (solde initial 1000 MAD) |
| POST    | `/login`                | —    | Authentification → JWT Bearer      |
| GET     | `/accounts/me/balance`  | JWT  | Consulter son solde                |
| POST    | `/transfer`             | JWT  | Virer un montant vers un autre utilisateur |
| GET     | `/health`               | —    | Vérification de santé              |

### Exemples curl

```bash
# Inscription
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'

# Connexion
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret123"}'
# → {"access_token": "<TOKEN>", "token_type": "bearer"}

# Consulter le solde
curl http://localhost:8000/accounts/me/balance \
  -H "Authorization: Bearer <TOKEN>"

# Virement (après avoir créé un utilisateur "bob")
curl -X POST http://localhost:8000/transfer \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"to_username": "bob", "amount": 100, "description": "Remboursement"}'
```

---

## Vulnérabilités intentionnelles (DevSecOps)

Ces failles sont **volontaires** et servent de cibles pour les outils de sécurité
dans les phases suivantes :

| # | Fichier | Vulnérabilité | Détecté en |
|---|---------|---------------|------------|
| 1 | `app/auth.py:13` | `SECRET_KEY` hardcodée en clair | **Phase 2** — Gitleaks |
| 2 | `requirements.txt` | `requests==2.28.1` (CVE-2023-32681) | **Phase 3** — Trivy / pip-audit |
| 3 | `Dockerfile` | Conteneur tourne en **root** | **Phase 4** — hadolint / CIS Docker |

---

## Roadmap des phases

```
Phase 1 (actuelle) → App + conteneurisation + ossature pipeline
Phase 2            → SAST (Bandit) + scan de secrets (Gitleaks)
Phase 3            → Scan CVE image (Trivy) + SCA dépendances (pip-audit)
Phase 4            → Durcissement Dockerfile + déploiement Kubernetes
```

---

## Stack technique

- **Backend** : FastAPI 0.104, Python 3.11
- **Base de données** : PostgreSQL 15 via SQLAlchemy 2.0
- **Auth** : JWT (python-jose) + bcrypt (passlib)
- **Conteneurisation** : Docker + Docker Compose
- **CI/CD** : GitHub Actions
