# Wallet PFA — Application Fintech DevSecOps

Application FastAPI servant de **cobaye** pour démontrer un pipeline CI/CD sécurisé
de bout en bout : SAST, scan de secrets, audit de dépendances, scan de CVE sur
l'image Docker, durcissement du conteneur, déploiement Kubernetes et monitoring.

Projet réalisé dans le cadre d'un PFA (Projet de Fin d'Année) DevSecOps.

---

## 1. Architecture

```
                         ┌─────────────────────────────────────────┐
                         │           GitHub Actions CI/CD            │
                         │                                           │
                         │  lint-dockerfile (Hadolint)                │
                         │  sast (Semgrep)                            │
                         │  secret-scan (Gitleaks)        ─┐          │
                         │  dependency-audit (pip-audit)   ├──► build │
                         │                                 │     │    │
                         │                          image-scan (Trivy)│
                         └─────────────────────────────────────────┘
                                              │
                                              ▼
        ┌──────────────────────────── Cluster Kubernetes ────────────────────────────┐
        │                                                                              │
        │   ┌──────────────────┐        ┌──────────────────┐                          │
        │   │  wallet-pfa Pod   │  x2    │   postgres Pod    │                          │
        │   │  (non-root, RO    │ ─────► │   (Service        │                          │
        │   │  filesystem)      │        │   ClusterIP:5432) │                          │
        │   └──────────────────┘        └──────────────────┘                          │
        │           ▲  Service NodePort:30800                                         │
        │           │                                                                  │
        │   Kyverno : refuse les pods root / images non signées                        │
        └──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
        ┌──────────────────────────────────────────┐
        │  Monitoring (docker-compose local)         │
        │  Prometheus (scrape /metrics) → Grafana    │
        └──────────────────────────────────────────┘
```

**Flux applicatif :** client → FastAPI (`/register`, `/login`, `/transfer`,
`/accounts/me/balance`) → SQLAlchemy → PostgreSQL.

---

## 2. Structure du projet

```
wallet-pfa/
├── app/
│   ├── main.py                  # FastAPI + lifespan + /metrics (Prometheus)
│   ├── database.py              # Engine SQLAlchemy + session
│   ├── models.py                # User, Account, Transaction (ORM)
│   ├── schemas.py                # Schémas Pydantic (I/O)
│   ├── auth.py                   # JWT + hachage mot de passe
│   └── routers/
│       ├── auth_router.py       # POST /register  POST /login
│       └── wallet_router.py     # GET /accounts/me/balance  POST /transfer
├── k8s/
│   ├── deployment.yaml          # Déploiement app (2 replicas, securityContext durci)
│   ├── service.yaml             # Service NodePort:30800
│   ├── postgres-deployment.yaml # Déploiement PostgreSQL
│   ├── postgres-service.yaml    # Service ClusterIP:5432
│   ├── configmap.yaml           # Config non sensible
│   ├── secret.yaml              # Secrets (base64)
│   └── kyverno-policy.yaml      # Politiques Kyverno (bonus)
├── .github/workflows/
│   └── ci.yml                   # Pipeline GitHub Actions (6 jobs)
├── .hadolint.yaml               # Config du linter Dockerfile
├── Dockerfile                   # Durci en Phase 4 (non-root, healthcheck...)
├── docker-compose.yml           # App + PostgreSQL + Prometheus + Grafana
├── prometheus.yml               # Config du scraping Prometheus
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Prérequis

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- (Optionnel, Kubernetes) `kubectl` + `minikube`

---

## 4. Lancement en local

```bash
cd wallet-pfa
cp .env.example .env          # optionnel
docker compose up --build
```

| Service     | URL                              | Notes                          |
|-------------|-----------------------------------|---------------------------------|
| API         | http://localhost:8000/docs         | Swagger UI                      |
| API         | http://localhost:8000/health       | Health check                    |
| API         | http://localhost:8000/metrics      | Métriques Prometheus             |
| Prometheus  | http://localhost:9090              | Cible : `wallet-pfa` (app:8000)  |
| Grafana     | http://localhost:3000              | Login : **admin / admin**       |

Pour arrêter :
```bash
docker compose down          # garde les données
docker compose down -v       # supprime aussi les volumes (reset complet)
```

---

## 5. Endpoints API

| Méthode | Route                   | Auth | Description                                |
|---------|-------------------------|------|---------------------------------------------|
| POST    | `/register`             | —    | Créer un compte (solde initial 1000 MAD)     |
| POST    | `/login`                | —    | Authentification → JWT Bearer                |
| GET     | `/accounts/me/balance`  | JWT  | Consulter son solde                          |
| POST    | `/transfer`             | JWT  | Virer un montant vers un autre utilisateur   |
| GET     | `/health`               | —    | Vérification de santé                        |
| GET     | `/metrics`              | —    | Métriques Prometheus                         |

---

## 6. Outils du pipeline DevSecOps

| Étape | Outil | Rôle | Bloque si |
|-------|-------|------|-----------|
| Lint Dockerfile | **Hadolint** | Bonnes pratiques de conteneurisation | Erreur ≥ `warning` |
| SAST | **Semgrep** (`p/python`, `p/owasp-top-ten`) | Vulnérabilités dans le code Python | Finding sévérité `ERROR` |
| Secrets | **Gitleaks** | Secrets hardcodés dans tout l'historique git | Tout secret détecté |
| SCA | **pip-audit** | CVE dans les dépendances Python (`requirements.txt`) | Toute CVE trouvée |
| Image scan | **Trivy** | CVE dans l'image Docker construite (OS + libs Python) | CVE `MEDIUM`/`HIGH`/`CRITICAL` |
| Build | **Docker Buildx** | Construction de l'image | Échec de build |
| Déploiement | **Kubernetes** | Orchestration (2 replicas, securityContext) | — |
| Politique cluster (bonus) | **Kyverno** | Refuse pods root / images non signées | Pod non conforme |
| Monitoring | **Prometheus + Grafana** | Observabilité (latence, requêtes, erreurs) | — |

---

## 7. Vulnérabilités intentionnelles — statut final

| # | Fichier | Vulnérabilité | Détectée par | Statut |
|---|---------|----------------|--------------|--------|
| 1 | `app/auth.py:13,36` | `SECRET_KEY` hardcodée, utilisée dans `jwt.encode()` | **Gitleaks** (pattern du secret) + **Semgrep** (règle `python.jwt.security.jwt-hardcode.jwt-python-hardcoded-secret`, CWE-522) — Phase 2 | ⚠️ Toujours présente (démo volontaire) |
| 2 | `requirements.txt` | `requests==2.28.1` → CVE-2023-32681 (MEDIUM) | **pip-audit** (Phase 2) + **Trivy** (Phase 3) | ⚠️ Toujours présente (démo volontaire) |
| 3 | `Dockerfile` | Conteneur tournait en **root** | **Hadolint** (Phase 4) | ✅ **Corrigée** — `USER appuser` (UID 1000) |

La vulnérabilité #3 est désormais corrigée pour démontrer le cycle complet
*détection → durcissement → vérification continue* : Hadolint valide en CI que
le Dockerfile reste durci à chaque commit.

---

## 8. Résultats du pipeline — ce qui bloque et pourquoi

```
lint-dockerfile     ✅ pass   — Dockerfile durci (non-root, slim, healthcheck)
sast                ❌ FAIL   — Semgrep détecte SECRET_KEY hardcodée dans
                                jwt.encode() (app/auth.py:36), règle
                                python.jwt.security.jwt-hardcode.jwt-python-
                                hardcoded-secret (CWE-522, blocking)
secret-scan         ❌ FAIL   — Gitleaks détecte SECRET_KEY hardcodée dans app/auth.py
dependency-audit    ❌ FAIL   — CVE-2023-32681 détectée dans requests==2.28.1
        │
        ▼ (needs: les 4 jobs ci-dessus)
build               ⏭️ SKIPPED — bloqué par sast / secret-scan / dependency-audit
        │
        ▼ (needs: build)
image-scan          ⏭️ SKIPPED — bloqué car build ne s'exécute pas
```

**Pourquoi c'est le comportement attendu :** les vulnérabilités #1 et #2 sont
volontaires (cf. section 7) — elles servent à démontrer que le pipeline
bloque bien la mise en production tant qu'elles ne sont pas corrigées. Pour
obtenir un pipeline 100 % vert, il suffirait de remplacer `SECRET_KEY` par une
variable d'environnement et de monter `requests` vers `>=2.31.0`.

---

## 9. Déploiement Kubernetes (minikube)

```powershell
# Installation (Windows)
winget install -e --id Kubernetes.kubectl
winget install -e --id Kubernetes.minikube

# Démarrage du cluster
minikube start --driver=docker

# Build de l'image dans le contexte Docker de minikube
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
docker build -t wallet-pfa:latest .

# Déploiement
kubectl apply -f k8s/

# Vérification
kubectl get pods
kubectl get services

# Accès à l'application
minikube service wallet-pfa --url
```

**Sécurité du déploiement :**
- `securityContext` : `runAsNonRoot`, `runAsUser: 1000`, `readOnlyRootFilesystem`, `allowPrivilegeEscalation: false`, capabilities droppées
- Secrets (`DB_PASSWORD`, `SECRET_KEY`) injectés via `Secret` K8s, jamais en dur dans les manifests applicatifs
- (Bonus) Politiques **Kyverno** pour interdire au niveau cluster tout pod root ou image non signée — voir `k8s/kyverno-policy.yaml`

---

## 10. Captures d'écran

> À insérer après exécution locale / sur le cluster.

| Capture | Emplacement suggéré |
|---------|----------------------|
| Pipeline GitHub Actions — vue d'ensemble des 6 jobs | `docs/screenshots/pipeline-overview.png` |
| Job `secret-scan` en échec (Gitleaks) | `docs/screenshots/gitleaks-fail.png` |
| Job `dependency-audit` en échec (pip-audit) | `docs/screenshots/pip-audit-fail.png` |
| Rapport Trivy (table des CVE) | `docs/screenshots/trivy-report.png` |
| `kubectl get pods` — 2 replicas Running | `docs/screenshots/k8s-pods.png` |
| Dashboard Grafana — métriques `wallet-pfa` | `docs/screenshots/grafana-dashboard.png` |
| Swagger UI — endpoints de l'API | `docs/screenshots/swagger-ui.png` |

```markdown
<!-- Exemple d'insertion une fois les images ajoutées dans docs/screenshots/ -->
![Pipeline GitHub Actions](docs/screenshots/pipeline-overview.png)
```

---

## 11. Roadmap des phases

```
Phase 1 ✅ App FastAPI + conteneurisation + ossature pipeline
Phase 2 ✅ SAST (Semgrep) + scan de secrets (Gitleaks) + SCA (pip-audit)
Phase 3 ✅ Scan CVE image Docker (Trivy) + manifestes Kubernetes
Phase 4 ✅ Durcissement Dockerfile (Hadolint) + monitoring (Prometheus/Grafana)
            + politiques cluster (Kyverno, bonus) + documentation finale
```

---

## 12. Stack technique

- **Backend** : FastAPI 0.104, Python 3.11
- **Base de données** : PostgreSQL 15 via SQLAlchemy 2.0
- **Auth** : JWT (python-jose) + bcrypt (passlib)
- **Conteneurisation** : Docker (image `slim`, non-root, healthcheck) + Docker Compose
- **Orchestration** : Kubernetes (Deployment, Service, ConfigMap, Secret) + Kyverno
- **CI/CD** : GitHub Actions (6 jobs : Hadolint, Semgrep, Gitleaks, pip-audit, build, Trivy)
- **Monitoring** : Prometheus (scraping `/metrics`) + Grafana (dashboards)
