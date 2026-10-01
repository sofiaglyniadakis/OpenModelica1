"""Ciclos de condução usados nos ensaios de veículos leves no Brasil.

* FTP-75 - ciclo urbano da ABNT NBR 6601 (emissões, PROCONVE) e base do consumo
  urbano da ABNT NBR 7024 / PBEV. Composto pelas fases "partida a frio"
  (0-505 s), "estabilizada" (505-1369 s) e "partida a quente" (repetição dos
  primeiros 505 s). O intervalo de 10 min de repouso entre as fases 2 e 3 não é
  simulado.
* HWFET - ciclo estrada da ABNT NBR 7024.
* US06 - ciclo agressivo (altas acelerações), útil para análises de sensibilidade.

Todos os perfis são amostrados a 1 Hz e armazenados em km/h.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

DADOS = Path(__file__).parent / "dados" / "ciclos"

# fases do FTP-75 (segundos) e pesos da ABNT NBR 6601
FTP75_FASES = (0.0, 505.0, 1369.0, 1874.0)
FTP75_PESOS = (0.43, 0.57)

# código numérico usado também na biblioteca Modelica (VeiculosLevesBR.Dados.Ciclos)
CODIGOS = {"ftp75": 1, "hwfet": 2, "us06": 3, "constante": 4, "personalizado": 0}

NOMES = {
    "ftp75": "Urbano FTP-75 (NBR 6601)",
    "hwfet": "Estrada HWFET (NBR 7024)",
    "us06": "Agressivo US06",
    "constante": "Velocidade constante",
    "personalizado": "Ciclo personalizado",
}


@dataclass
class Ciclo:
    id: str
    nome: str
    v_kmh: np.ndarray  # perfil de velocidade a 1 Hz
    fases: tuple[float, ...] = field(default_factory=tuple)

    @property
    def duracao(self) -> float:
        return float(len(self.v_kmh) - 1)

    @property
    def v(self) -> np.ndarray:
        return self.v_kmh / 3.6

    @property
    def distancia_km(self) -> float:
        v = self.v
        return float(np.sum(0.5 * (v[1:] + v[:-1]))) / 1000.0

    def resumo(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "duracao_s": self.duracao,
            "distancia_km": round(self.distancia_km, 3),
            "v_media_kmh": round(self.distancia_km / max(self.duracao, 1) * 3600, 1),
            "v_max_kmh": round(float(np.max(self.v_kmh)), 1),
        }


def _ler_csv(nome: str) -> np.ndarray:
    with open(DADOS / f"{nome}.csv", encoding="utf-8") as f:
        linhas = [l for l in f if not l.startswith("#")]
    leitor = csv.DictReader(linhas)
    return np.array([float(r["v_kmh"]) for r in leitor])


@lru_cache(maxsize=None)
def _perfil(id_: str) -> np.ndarray:
    if id_ == "ftp75":
        udds = _ler_csv("udds")
        return np.concatenate([udds, udds[1:506]])
    return _ler_csv(id_)


def obter(id_: str, params: dict | None = None) -> Ciclo:
    p = params or {}
    if id_ == "ftp75":
        return Ciclo(id_, NOMES[id_], _perfil(id_).copy(), FTP75_FASES)
    if id_ in ("hwfet", "us06"):
        return Ciclo(id_, NOMES[id_], _perfil(id_).copy())
    if id_ == "constante":
        v = float(p.get("velocidade_constante", 100.0))
        dur = int(p.get("duracao_constante", 600))
        return Ciclo(id_, f"Constante {v:g} km/h", np.full(dur + 1, v))
    if id_ == "personalizado":
        return Ciclo(id_, NOMES[id_], ler_personalizado(p.get("dados_personalizados", "")))
    raise ValueError(f"Ciclo desconhecido: {id_}")


def ler_personalizado(texto: str) -> np.ndarray:
    """Lê um CSV 'tempo_s, velocidade_kmh' (separador vírgula, ponto-e-vírgula ou tab)
    e reamostra a 1 Hz por interpolação linear."""
    t, v = [], []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        for sep in (";", "\t", ","):
            if sep in linha:
                partes = linha.split(sep)
                break
        else:
            partes = linha.split()
        try:
            t.append(float(partes[0].replace(",", ".")))
            v.append(float(partes[1].replace(",", ".")))
        except (ValueError, IndexError):
            continue  # cabeçalho ou linha inválida
    if len(t) < 2:
        raise ValueError("O ciclo personalizado precisa de pelo menos 2 pontos (tempo_s; velocidade_kmh).")
    t_arr, v_arr = np.array(t), np.array(v)
    ordem = np.argsort(t_arr)
    t_arr, v_arr = t_arr[ordem] - t_arr[ordem][0], v_arr[ordem]
    grade = np.arange(0, int(np.floor(t_arr[-1])) + 1, 1.0)
    return np.clip(np.interp(grade, t_arr, v_arr), 0, None)


def catalogo() -> list[dict]:
    return [obter(i).resumo() for i in ("ftp75", "hwfet", "us06")]
