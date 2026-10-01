# Autora: Sofia Glyniadakis
# Criado em: 2026-10-01

import dataclasses

import pytest

from omveiculos import analise, ciclos, combustiveis
from omveiculos.componentes import (Ambiente, Bateria, Hibrido, MotorCombustao, MotorEletrico, Transmissao,
                                    Veiculo, raio_pneu)
from omveiculos.simulador import TremDeForca, simular_ciclo, simular_desempenho

AMB = Ambiente()


def hatch(**kw):
    veh = Veiculo(massa=1000, cd=0.33, area_frontal=2.05, cr=0.010, raio=raio_pneu("175/65 R14"))
    mot = MotorCombustao(potencia_g=71, potencia_e=75, torque_g=10.0, torque_e=10.4, rpm_potencia=6200)
    pt = TremDeForca("combustao", veh, Transmissao(), motor=mot, combustivel=combustiveis.gasolina_c())
    return dataclasses.replace(pt, **kw)


def eletrico():
    veh = Veiculo(massa=1405, cd=0.30, area_frontal=2.3, cr=0.009, raio=raio_pneu("205/50 R17"))
    tr = Transmissao(tipo="redutor", relacoes=[1.0], diferencial=9.6, eficiencia=0.97)
    return TremDeForca("eletrico", veh, tr, eletrico=MotorEletrico(), bateria=Bateria())


def kml(pt, ciclo):
    r = simular_ciclo(pt, ciclos.obter(ciclo), AMB)
    return analise.indicadores_ciclo(r, pt, combustiveis.eletricidade())["km_por_unidade"]


def test_raio_pneu():
    assert raio_pneu("185/65 R15") == pytest.approx(0.975 * (15 * 0.0254 / 2 + 0.185 * 0.65), rel=1e-9)
    with pytest.raises(ValueError):
        raio_pneu("aro 15")


def test_hatch_flex_valores_plausiveis():
    urb = kml(hatch(), "ftp75")
    est = kml(hatch(), "hwfet")
    assert 12 < urb < 20 and est > urb
    et = kml(hatch(combustivel=combustiveis.etanol_hidratado()), "ftp75")
    assert 0.68 < et / urb < 0.75


def test_balanco_de_energia_na_roda():
    pt = hatch()
    r = simular_ciclo(pt, ciclos.obter("ftp75"), AMB)
    e = r.energias
    # energia de tração positiva = resistências + frenagem (energia cinética retorna a zero)
    tracao = sum(max(p, 0) for p in r.p_roda_kw) * 1000.0
    assert tracao == pytest.approx(e["aerodinamica"] + e["rolamento"] + e["frenagem"], rel=0.02)


def test_start_stop_e_ar_condicionado():
    base = kml(hatch(), "ftp75")
    mot_ss = dataclasses.replace(hatch().motor, start_stop=True)
    assert kml(hatch(motor=mot_ss), "ftp75") > base
    veh_ar = dataclasses.replace(hatch().veiculo, ar_condicionado=True)
    assert kml(hatch(veiculo=veh_ar), "ftp75") < base


def test_eletrico_regeneracao_reduz_consumo():
    pt = eletrico()
    sem = dataclasses.replace(pt, eletrico=dataclasses.replace(pt.eletrico, fracao_regeneracao=0.0))
    assert kml(pt, "ftp75") > 1.2 * kml(sem, "ftp75")


def test_hibrido_mais_eficiente_que_combustao_no_urbano():
    veh = Veiculo(massa=1420, cd=0.29, area_frontal=2.25, cr=0.009, raio=raio_pneu("205/55 R16"))
    mot = MotorCombustao(cilindrada=1.8, potencia_g=98, potencia_e=101, torque_g=14.5, torque_e=14.5,
                         rpm_torque_ini=3600, rpm_torque_fim=4000, rpm_potencia=5200, rpm_max=5600,
                         eficiencia_indicada=0.40, pmep0=0.3)
    tr = Transmissao(tipo="cvt", cvt_min=0.4, cvt_max=2.8, diferencial=5.0, eficiencia=0.92, rpm_troca_min=1300)
    comb = combustiveis.gasolina_c()
    conv = TremDeForca("combustao", veh, tr, motor=mot, combustivel=comb)
    hib = TremDeForca("hibrido", veh, tr, motor=mot, combustivel=comb,
                      eletrico=MotorEletrico(potencia=72, torque=16.6, rpm_max=13000),
                      bateria=Bateria(capacidade=1.3, soc_inicial=55, soc_min=30, soc_max=80), hibrido=Hibrido())
    assert kml(hib, "ftp75") > 1.15 * kml(conv, "ftp75")


def test_desempenho_mais_potencia_acelera_mais():
    base = simular_desempenho(hatch(), AMB)
    forte = dataclasses.replace(hatch().motor, potencia_g=120, torque_g=17)
    rapido = simular_desempenho(hatch(motor=forte), AMB)
    assert 10 < base.t_0_100 < 20
    assert rapido.t_0_100 < base.t_0_100
    assert rapido.v_max_kmh > base.v_max_kmh


def test_pbev_combinado_55_45():
    pt = hatch()
    u = analise.indicadores_ciclo(simular_ciclo(pt, ciclos.obter("ftp75"), AMB), pt, combustiveis.eletricidade())
    e = analise.indicadores_ciclo(simular_ciclo(pt, ciclos.obter("hwfet"), AMB), pt, combustiveis.eletricidade())
    p = analise.indicadores_pbev(u, e, pt)
    esperado = 0.55 * u["unidade_por_100km"] + 0.45 * e["unidade_por_100km"]
    assert p["combinado"]["unidade_por_100km"] == pytest.approx(esperado, abs=0.01)
    assert p["combinado"]["autonomia_km"] == pytest.approx(pt.veiculo.tanque * p["combinado"]["km_por_unidade"], rel=0.01)
