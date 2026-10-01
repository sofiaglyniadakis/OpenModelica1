# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from omveiculos import catalogo  # noqa: E402


@pytest.fixture
def modelos():
    return {m["id"]: {"nos": m["nos"], "arestas": m["arestas"]} for m in catalogo.catalogo()["modelos"]}
