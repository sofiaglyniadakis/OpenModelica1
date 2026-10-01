"""Compara o motor rápido (Python) com o OpenModelica.

Executado apenas quando o ``omc`` está disponível (OMVEICULOS_OMC, OPENMODELICAHOME
ou PATH). Ex.: ``micromamba create -p ./omenv -c conda-forge omcompiler`` e
``OMVEICULOS_OMC=./omenv/bin/omc pytest``.
"""

__author__ = "Sofia Glyniadakis"

import pytest

from omveiculos import modelica, workflow

OMC = modelica.localizar_omc()
pytestmark = pytest.mark.skipif(OMC is None, reason="omc (OpenModelica) não encontrado")


def _comparar(a: dict, b: dict, chaves, rel):
    for k in chaves:
        if a.get(k) is not None:
            assert b[k] == pytest.approx(a[k], rel=rel, abs=0.02), k


@pytest.mark.parametrize("modelo", ["etanol-gasolina", "flex-eletrico-hibrido", "desempenho", "ar-condicionado"])
def test_openmodelica_confere_com_motor_rapido(modelos, modelo):
    rapido = workflow.executar(modelos[modelo])
    omc = workflow.executar(modelos[modelo], modelica.MotorOpenModelica(OMC))
    assert omc["erros"] == []
    assert len(omc["cenarios"]) == len(rapido["cenarios"])
    for a, b in zip(rapido["cenarios"], omc["cenarios"]):
        ia, ib = a["indicadores"], b["indicadores"]
        if a["ensaio_tipo"] == "ensaio_pbev":
            for parte in ("urbano", "estrada", "combinado"):
                _comparar(ia[parte], ib[parte], ("km_por_unidade", "mj_km"), 0.005)
        elif a["ensaio_tipo"] == "ciclo":
            _comparar(ia["ciclo"], ib["ciclo"], ("km_por_unidade", "mj_km"), 0.005)
        else:
            _comparar(ia, ib, ("t_0_100_s", "t_80_120_s", "v_max_kmh"), 0.01)
