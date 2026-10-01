# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01

import pytest

from omveiculos import ciclos, combustiveis


def test_gasolina_c_e30():
    g = combustiveis.gasolina_c(30)
    assert g.densidade == pytest.approx(0.7588, abs=1e-4)
    assert 28.5 < g.energia_por_unidade < 29.5  # MJ/L
    # só a parcela fóssil (gasolina A) conta no CO2 fóssil
    assert g.co2_fossil < g.co2_total


def test_etanol_hidratado_e_biogenico():
    e = combustiveis.etanol_hidratado()
    assert 24.5 < e.pci < 25.5
    assert e.co2_fossil == 0.0
    assert e.fracao_etanol_vol == pytest.approx(0.957, abs=0.01)


def test_relacao_energetica_etanol_gasolina_proxima_de_70pct():
    r = combustiveis.etanol_hidratado().energia_por_unidade / combustiveis.gasolina_c().energia_por_unidade
    assert 0.67 < r < 0.72


def test_mais_etanol_na_gasolina_reduz_energia_por_litro():
    assert combustiveis.gasolina_c(27).energia_por_unidade > combustiveis.gasolina_c(30).energia_por_unidade


def test_criar_tipo_invalido():
    with pytest.raises(ValueError):
        combustiveis.criar("querosene")


@pytest.mark.parametrize(
    "cid, duracao, km",
    [("ftp75", 1874, 17.77), ("hwfet", 765, 16.51), ("us06", 600, 12.89)],
)
def test_ciclos_oficiais(cid, duracao, km):
    c = ciclos.obter(cid)
    assert c.duracao == duracao
    assert c.distancia_km == pytest.approx(km, abs=0.03)


def test_ciclo_personalizado_reamostra_a_1hz():
    c = ciclos.obter("personalizado", {"dados_personalizados": "tempo;vel\n0;0\n10,5;50\n20;0"})
    assert c.duracao == 20
    assert c.v_kmh[10] == pytest.approx(50 * 10 / 10.5, rel=1e-6)


def test_ciclo_personalizado_invalido():
    with pytest.raises(ValueError):
        ciclos.obter("personalizado", {"dados_personalizados": "abc"})
