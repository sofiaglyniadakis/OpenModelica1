"""Indicadores de consumo, custo, emissões e desempenho.

Usado igualmente pelos resultados do motor rápido (Python) e do OpenModelica,
pois ambos produzem um :class:`~omveiculos.simulador.ResultadoCiclo`.

Convenções:

* Ciclo urbano FTP-75 ponderado conforme ABNT NBR 6601:
  ``Y = 0,43 (Yc + Ys)/(Dc + Ds) + 0,57 (Yh + Ys)/(Dh + Ds)``.
* Combinado (PBEV): 55 % urbano + 45 % estrada, ponderando consumo por km.
* Híbridos: o consumo é corrigido pela variação líquida de energia da bateria,
  convertida em combustível equivalente pela eficiência média do motor.
* Elétricos: energia "na tomada" = energia retirada da bateria / eficiência do
  carregador.
* "Uso real" (opcional): fórmulas de ajuste da EPA (derived 5-cycle) aplicadas
  em base energética - apenas indicativas, não são os fatores do PBEV.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

import math

import numpy as np

from .ciclos import FTP75_PESOS
from .combustiveis import Combustivel
from .simulador import ResultadoCiclo, ResultadoDesempenho, TremDeForca

PESO_URBANO = 0.55
PESO_ESTRADA = 0.45
MJ_POR_LITRO_GASOLINA_EPA = 32.05


def _indices_fases(res: ResultadoCiclo) -> tuple[int, int] | None:
    if res.ciclo_id != "ftp75" or len(res.fases) != 4:
        return None
    return int(res.fases[1]), int(res.fases[2])


def por_km(res: ResultadoCiclo, acumulado: np.ndarray) -> float:
    """Quantidade por km do ciclo (ponderada por fase no FTP-75)."""
    d = res.distancia_m / 1000.0
    fases = _indices_fases(res)
    if fases is None:
        return float(acumulado[-1] / max(d[-1], 1e-9))
    i1, i2 = fases
    yc, ys, yh = acumulado[i1], acumulado[i2] - acumulado[i1], acumulado[-1] - acumulado[i2]
    dc, ds, dh = d[i1], d[i2] - d[i1], d[-1] - d[i2]
    w1, w2 = FTP75_PESOS
    return float(w1 * (yc + ys) / (dc + ds) + w2 * (yh + ys) / (dh + ds))


def _seguro(x: float, nd: int = 3) -> float | None:
    if x is None or not math.isfinite(x):
        return None
    return round(float(x), nd)


def combustivel_corrigido_kg(res: ResultadoCiclo, pt: TremDeForca) -> np.ndarray:
    """Massa de combustível acumulada; nos híbridos inclui a correção pelo balanço da bateria."""
    if pt.arquitetura != "hibrido":
        return res.combustivel_kg
    pci_j = pt.combustivel.pci * 1e6
    e_comb = res.combustivel_kg[-1] * pci_j
    eta_ice = res.energia_motor_mec_j / e_comb if e_comb > 0 else 0.3
    eta_ice = min(max(eta_ice, 0.15), 0.45)
    k = pt.eletrico.eficiencia * pt.bateria.eficiencia / eta_ice
    return res.combustivel_kg + res.energia_bat_j * k / pci_j


def indicadores_ciclo(res: ResultadoCiclo, pt: TremDeForca, eletricidade: Combustivel) -> dict:
    dist_km = res.distancia_m[-1] / 1000.0
    out: dict = {
        "ciclo": res.ciclo_id,
        "ciclo_nome": res.ciclo_nome,
        "distancia_km": _seguro(dist_km),
        "duracao_s": _seguro(res.t[-1], 0),
        "v_media_kmh": _seguro(dist_km / max(res.t[-1], 1) * 3600, 1),
        "tempo_excedido_s": _seguro(res.tempo_excedido_s, 1),
        "energias_mj": {k: _seguro(v / 1e6) for k, v in res.energias.items()},
    }
    if pt.arquitetura in ("combustao", "hibrido"):
        comb = pt.combustivel
        kg = combustivel_corrigido_kg(res, pt)
        unid_km = por_km(res, kg / comb.densidade)
        mj_km = unid_km * comb.energia_por_unidade
        out.update(
            energetico=comb.tipo,
            unidade=comb.unidade,
            km_por_unidade=_seguro(1.0 / unid_km if unid_km > 0 else float("inf"), 2),
            unidade_por_100km=_seguro(100.0 * unid_km, 2),
            mj_km=_seguro(mj_km),
            co2_fossil_g_km=_seguro(unid_km * comb.densidade * comb.co2_fossil * 1000.0, 1),
            co2_total_g_km=_seguro(unid_km * comb.densidade * comb.co2_total * 1000.0, 1),
            co2_wtw_g_km=_seguro(mj_km * comb.wtw, 1),
            custo_r_km=_seguro(unid_km * comb.preco, 3),
            combustivel_total=_seguro(kg[-1] / comb.densidade),
        )
        e_comb = res.combustivel_kg[-1] * comb.pci * 1e6
        out["eficiencia_media_motor"] = _seguro(res.energia_motor_mec_j / e_comb if e_comb > 0 else 0.0)
        movendo = res.rpm[:-1] > 0
        out["rpm_medio"] = _seguro(float(np.mean(res.rpm[:-1][movendo])) if movendo.any() else 0.0, 0)
    if pt.arquitetura == "eletrico":
        tomada_kwh = res.energia_bat_j / 3.6e6 / pt.bateria.eficiencia_carregador
        kwh_km = por_km(res, tomada_kwh)
        mj_km = kwh_km * 3.6
        out.update(
            energetico="eletricidade",
            unidade="kWh",
            km_por_unidade=_seguro(1.0 / kwh_km if kwh_km > 0 else float("inf"), 2),
            unidade_por_100km=_seguro(100.0 * kwh_km, 2),
            mj_km=_seguro(mj_km),
            co2_fossil_g_km=0.0,
            co2_total_g_km=0.0,
            co2_wtw_g_km=_seguro(mj_km * eletricidade.wtw, 1),
            custo_r_km=_seguro(kwh_km * eletricidade.preco, 3),
            combustivel_total=_seguro(tomada_kwh[-1]),
        )
    if pt.arquitetura in ("eletrico", "hibrido"):
        out["soc_inicial"] = _seguro(res.soc[0], 1)
        out["soc_final"] = _seguro(res.soc[-1], 1)
    return out


def _uso_real(mj_km: float, ciclo: str, arquitetura: str) -> float:
    if arquitetura == "eletrico":
        return mj_km / 0.7
    if ciclo == "urbano":
        return 0.007666 * MJ_POR_LITRO_GASOLINA_EPA + 1.1805 * mj_km
    return 0.003237 * MJ_POR_LITRO_GASOLINA_EPA + 1.3466 * mj_km


def indicadores_pbev(urb: dict, est: dict, pt: TremDeForca) -> dict:
    """Combina os resultados urbano (FTP-75) e estrada (HWFET) no formato da etiqueta."""
    def comb(chave: str) -> float | None:
        a, b = urb.get(chave), est.get(chave)
        if a is None or b is None:
            return None
        return PESO_URBANO * a + PESO_ESTRADA * b

    unid_100 = comb("unidade_por_100km")
    unid_km = unid_100 / 100.0 if unid_100 else None
    mj_km = comb("mj_km")
    energia_un = mj_km / unid_km if unid_km else None
    out = {
        "urbano": urb,
        "estrada": est,
        "combinado": {
            "km_por_unidade": _seguro(1.0 / unid_km, 2) if unid_km else None,
            "unidade_por_100km": _seguro(unid_100, 2),
            "mj_km": _seguro(mj_km),
            "co2_fossil_g_km": _seguro(comb("co2_fossil_g_km"), 1),
            "co2_total_g_km": _seguro(comb("co2_total_g_km"), 1),
            "co2_wtw_g_km": _seguro(comb("co2_wtw_g_km"), 1),
            "custo_r_km": _seguro(comb("custo_r_km"), 3),
            "unidade": urb.get("unidade"),
        },
    }
    c = out["combinado"]
    if pt.arquitetura == "eletrico":
        util = (pt.bateria.soc_max - pt.bateria.soc_min) / 100.0 * pt.bateria.capacidade
        kwh_bat_km = unid_km * pt.bateria.eficiencia_carregador if unid_km else None
        c["autonomia_km"] = _seguro(util / kwh_bat_km, 0) if kwh_bat_km else None
    elif unid_km:
        c["autonomia_km"] = _seguro(pt.veiculo.tanque / unid_km, 0)
    if urb.get("mj_km") and est.get("mj_km") and energia_un:
        mj_u = _uso_real(urb["mj_km"], "urbano", pt.arquitetura)
        mj_e = _uso_real(est["mj_km"], "estrada", pt.arquitetura)
        out["uso_real_estimado"] = {
            "urbano_km_por_unidade": _seguro(energia_un / mj_u, 2),
            "estrada_km_por_unidade": _seguro(energia_un / mj_e, 2),
            "combinado_km_por_unidade": _seguro(energia_un / (PESO_URBANO * mj_u + PESO_ESTRADA * mj_e), 2),
            "metodo": "Fórmulas de ajuste EPA (derived 5-cycle) em base energética - indicativo",
        }
    return out


def indicadores_desempenho(res: ResultadoDesempenho, pt: TremDeForca) -> dict:
    if pt.arquitetura == "eletrico":
        p_cv = pt.eletrico.potencia
    else:
        p_w, _ = pt.classificacao()
        p_cv = p_w / 735.49875
        if pt.arquitetura == "hibrido":
            p_cv += pt.eletrico.potencia
    return {
        "t_0_100_s": _seguro(res.t_0_100, 1) if res.t_0_100 else None,
        "t_80_120_s": _seguro(res.t_80_120, 1) if res.t_80_120 else None,
        "v_max_kmh": _seguro(res.v_max_kmh, 0),
        "potencia_cv": _seguro(p_cv, 0),
        "peso_potencia_kg_cv": _seguro(pt.veiculo.massa / p_cv, 2) if p_cv > 0 else None,
    }


def paridade_etanol(gasolina: dict, etanol: dict, pg: float, pe: float, km_mes: float) -> dict:
    """Relação de preço etanol/gasolina a partir da qual o etanol deixa de compensar.

    ``gasolina`` e ``etanol`` são os indicadores principais (combinado do PBEV
    ou o ciclo isolado); ``pg`` e ``pe`` são os preços por litro."""
    relacao_consumo = etanol["km_por_unidade"] / gasolina["km_por_unidade"]
    relacao_preco = pe / pg
    return {
        "relacao_consumo": _seguro(relacao_consumo, 3),
        "relacao_preco": _seguro(relacao_preco, 3),
        "compensa": "etanol" if relacao_preco < relacao_consumo else "gasolina",
        "preco_max_etanol": _seguro(pg * relacao_consumo, 2),
        "economia_mensal": _seguro(abs(gasolina["custo_r_km"] - etanol["custo_r_km"]) * km_mes, 2),
    }


def series(res: ResultadoCiclo, pt: TremDeForca, passo: int = 1) -> dict:
    """Séries temporais para os gráficos (amostradas a cada ``passo`` segundos)."""
    s = slice(None, None, passo)
    out = {
        "t": res.t[s].tolist(),
        "v_kmh": np.round(res.v_kmh[s], 2).tolist(),
        "p_roda_kw": np.round(res.p_roda_kw[s], 2).tolist(),
    }
    if pt.arquitetura != "eletrico":
        comb = pt.combustivel
        out["rpm"] = np.round(res.rpm[s], 0).tolist()
        out["marcha"] = res.marcha[s].astype(int).tolist()
        out["p_motor_kw"] = np.round(res.p_motor_kw[s], 2).tolist()
        out["combustivel_acumulado"] = np.round(res.combustivel_kg[s] / comb.densidade, 4).tolist()
    if pt.arquitetura != "combustao":
        out["p_eletrico_kw"] = np.round(res.p_eletrico_kw[s], 2).tolist()
        out["soc"] = np.round(res.soc[s], 2).tolist()
    return out
