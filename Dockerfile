# VULNÉRABLE EXPRÈS - démo DevSecOps
# 1. Image de base générique (python:3.11) non durcie
# 2. Tourne en ROOT (pas de directive USER) → sera corrigé en Phase 4
#    avec un user non-privilégié + multi-stage build
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
