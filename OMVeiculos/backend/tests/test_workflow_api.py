# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01

import copy

import pytest
from fastapi.testclient import TestClient

from omveiculos import workflow
from omveiculos.api import app


def test_todos_os_modelos_rodam_sem_erros(modelos):
    for mid, wf in modelos.items():
        r = workflow.executar(wf)
        if mid == "em-branco":
            assert r["erros"]
            continue
        assert r["erros"] == [], mid
        assert r["cenarios"], mid


def test_flex_com_dois_combustiveis_gera_paridade(modelos):
    r = workflow.executar(modelos["etanol-gasolina"])
    assert len(r["cenarios"]) == 2
    par = r["paineis"][0]["paridades"][0]
    assert 0.68 < par["relacao_consumo"] < 0.75
    assert par["compensa"] in ("etanol", "gasolina")


def test_combustivel_incompativel(modelos):
    wf = copy.deepcopy(modelos["etanol-gasolina"])
    for n in wf["nos"]:
        if n["id"] == "mot":
            n["params"]["tipo"] = "diesel"
    r = workflow.executar(wf)
    assert any("não é compatível" in e["mensagem"] for e in r["erros"])


def test_veiculo_sem_transmissao(modelos):
    wf = copy.deepcopy(modelos["etanol-gasolina"])
    wf["arestas"] = [a for a in wf["arestas"] if a["destino"] != "vei"]
    r = workflow.executar(wf)
    assert any(e["no"] == "vei" for e in r["erros"])
    assert r["cenarios"] == []


def test_motor_eletrico_sem_bateria(modelos):
    wf = copy.deepcopy(modelos["flex-eletrico-hibrido"])
    wf["arestas"] = [a for a in wf["arestas"] if a["origem"] != "bat"]
    r = workflow.executar(wf)
    assert any("bateria" in e["mensagem"] for e in r["erros"])
    assert len(r["cenarios"]) == 2  # os outros veículos continuam sendo simulados


def test_parametro_invalido(modelos):
    wf = copy.deepcopy(modelos["etanol-gasolina"])
    for n in wf["nos"]:
        if n["id"] == "vei":
            n["params"]["pneu"] = "xyz"
    r = workflow.executar(wf)
    assert any("pneu" in e["mensagem"].lower() for e in r["erros"])


@pytest.fixture
def cliente():
    return TestClient(app)


def test_api_catalogo_e_simulacao(cliente, modelos):
    cat = cliente.get("/api/catalogo").json()
    assert {b["tipo"] for b in cat["blocos"]} >= {"veiculo", "motor_combustao", "ensaio_pbev", "painel"}
    r = cliente.post("/api/simular", json={"workflow": modelos["desempenho"]})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["motor"] == "rapido"
    assert any(c["ensaio_tipo"] == "desempenho" for c in corpo["cenarios"])


def test_api_codigo_modelica(cliente, modelos):
    r = cliente.post("/api/modelica", json=modelos["flex-eletrico-hibrido"]).json()
    assert "extends VeiculosLevesBR.Experimentos.CicloHibrido" in r["codigo"]
    assert "extends VeiculosLevesBR.Experimentos.CicloEletrico" in r["codigo"]
    assert len(r["modelos"]) == 6
