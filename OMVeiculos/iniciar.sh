#!/usr/bin/env bash
# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01
#
# Inicia o OM Veículos Leves em http://127.0.0.1:8000
#
#   ./iniciar.sh                      # usa o omc do PATH (se houver)
#   ./iniciar.sh --omc /caminho/omc   # aponta para um OpenModelica específico
#   ./iniciar.sh --porta 9000
#
# Requisitos: Python >= 3.10 e Node.js >= 20.19.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo ">> criando ambiente Python (.venv)"
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e "backend[dev]"

if [ ! -f frontend/dist/index.html ] || [ -n "$(find frontend/src frontend/index.html -newer frontend/dist/index.html -print -quit)" ]; then
  echo ">> compilando a interface"
  (cd frontend && npm ci --no-audit --no-fund && npm run build)
fi

cd backend
exec python -m omveiculos --abrir "$@"
