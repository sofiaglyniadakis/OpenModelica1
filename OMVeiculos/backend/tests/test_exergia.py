# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01

import pytest

from omveiculos import analise, combustiveis, workflow


def _exergia(modelos, modelo):
    r = workflow.executar(modelos[modelo])
    assert r["erros"] == []
    return r, next(p for p in r["paineis"] if p["tipo"] == "exergia")


def test_exergia_quimica_dos_combustiveis():
    e = combustiveis.etanol_hidratado()
    g = combustiveis.gasolina_c()
    assert 1.05 < e.exergia / e.pci < 1.12
    assert 1.05 < g.exergia / g.pci < 1.09
    assert e.fracao_renovavel == 1.0
    assert 0.2 < g.fracao_renovavel < 0.3  # parcela do etanol anidro (E30)


def test_balanco_fecha_e_itens_nao_negativos(modelos):
    _, p = _exergia(modelos, "exergia")
    assert len(p["exergia"]) == 4
    for x in p["exergia"].values():
        for ciclo in ("urbano", "estrada"):
            c = x[ciclo]
            assert abs(c["fechamento"]) < 1e-6
            for nome, v in c["itens_mj_km"].items():
                if nome != "rampa":
                    assert v >= -1e-6, (nome, v)


def test_eficiencias_coerentes(modelos):
    r, p = _exergia(modelos, "exergia")
    nomes = {c["id"]: c for c in r["cenarios"]}
    eta = {nomes[k]["arquitetura"] + ":" + nomes[k]["energetico"]: v["principal"]["eficiencia_2a_lei"]
           for k, v in p["exergia"].items()}
    assert 0.15 < eta["combustao:etanol"] < 0.30
    assert eta["hibrido:etanol"] > eta["combustao:etanol"]
    assert 0.7 < eta["eletrico:eletricidade"] < 0.9
    # a 2ª lei é sempre mais exigente que a 1ª para combustíveis (phi > 1)
    for v in p["exergia"].values():
        pr = v["principal"]
        assert pr["eficiencia_2a_lei"] <= pr["eficiencia_1a_lei"] + 1e-9


def test_perdas_da_transmissao_no_eletrico(modelos):
    r, p = _exergia(modelos, "exergia")
    cid = next(c["id"] for c in r["cenarios"] if c["arquitetura"] == "eletrico")
    c = next(x for x in r["cenarios"] if x["id"] == cid)
    f = c["indicadores"]["urbano"]["fluxos"]
    ex = analise.exergia_ciclo(f)
    d = f["distancia_km"]
    eta = f["eta_transmissao"]
    esperado = (f["roda_pos"] * (1 / eta - 1) + f["regen_eixo"] * (1 / eta - 1)) / d
    assert ex["itens_mj_km"]["transmissao"] == pytest.approx(esperado, rel=0.02)


def test_ar_condicionado_aumenta_destruicao_em_acessorios(modelos):
    import copy

    wf = copy.deepcopy(modelos["ar-condicionado"])
    wf["nos"].append({"id": "exe", "tipo": "exergia", "rotulo": "Exergia", "params": {}, "posicao": {"x": 0, "y": 0}})
    wf["arestas"].append({"origem": "cic", "destino": "exe", "entrada": "resultado"})
    r = workflow.executar(wf)
    p = next(x for x in r["paineis"] if x["tipo"] == "exergia")
    por_nome = {c["veiculo_nome"]: p["exergia"][c["id"]]["principal"] for c in r["cenarios"]}
    assert por_nome["Hatch com ar"]["grupos_mj_km"]["acessorios"] > 3 * por_nome["Hatch sem ar"]["grupos_mj_km"]["acessorios"]
    assert por_nome["Hatch com ar"]["eficiencia_2a_lei"] < por_nome["Hatch sem ar"]["eficiencia_2a_lei"]
