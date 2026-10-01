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
    out["fluxos"] = fluxos_energia(res, pt, eletricidade)
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


# --- Análise exergética (tanque/tomada à roda) -------------------------------------------

CATEGORIAS_EXERGIA = {
    "motor_destruicao": "Motor: combustão e atrito",
    "calor_rejeitado": "Calor rejeitado (escape + arrefecimento)",
    "trem_eletrico": "Trem elétrico (motor, bateria, carregador)",
    "transmissao": "Transmissão e embreagem",
    "acessorios": "Acessórios e ar-condicionado",
    "resistencias": "Aerodinâmica e rolamento",
    "frenagem": "Freios e freio-motor",
    "armazenada": "Armazenada (rampa, bateria)",
}


def fluxos_energia(res: ResultadoCiclo, pt: TremDeForca, eletricidade: Combustivel) -> dict:
    """Energias do ciclo (MJ) nas interfaces do trem de força, base da análise exergética."""
    mj = 1e-6
    f = {k: v * mj for k, v in res.fluxos.items()}
    f.update({k: v * mj for k, v in res.energias.items()})
    f["motor_eixo"] = res.energia_motor_mec_j * mj
    f["bateria"] = float(res.energia_bat_j[-1]) * mj
    f["distancia_km"] = float(res.distancia_m[-1]) / 1000.0
    f["arquitetura"] = pt.arquitetura
    f["eta_transmissao"] = pt.transmissao.eficiencia
    if pt.combustivel is not None:
        kg = float(res.combustivel_kg[-1])
        f["combustivel_pci"] = kg * pt.combustivel.pci
        f["combustivel_ex"] = kg * pt.combustivel.exergia
        f["renovavel_comb"] = pt.combustivel.fracao_renovavel
    else:
        f["combustivel_pci"] = f["combustivel_ex"] = f["renovavel_comb"] = 0.0
    f["eta_carregador"] = pt.bateria.eficiencia_carregador if pt.bateria else 1.0
    f["renovavel_rede"] = eletricidade.fracao_renovavel
    return f


def _fator_escape(t0: float, te: float) -> float:
    """Fração exergética do calor sensível de um gás resfriado de te até t0 (K)."""
    if te <= t0 + 1e-6:
        return 0.0
    return 1.0 - t0 / (te - t0) * math.log(te / t0)


def exergia_ciclo(f: dict, t0_c: float = 25.0, t_escape_c: float = 527.0, t_arrefecimento_c: float = 90.0,
                  fracao_escape: float = 0.5) -> dict:
    """Balanço de exergia de um ciclo (MJ e MJ/km).

    Hipóteses: estado morto a ``t0_c`` e 1 atm; exergia química dos combustíveis por
    phi = ex/PCI; o calor rejeitado pelo motor (PCI do combustível menos o trabalho no eixo) é
    dividido entre escapamento (gás resfriado de ``t_escape_c`` até ``t0_c``) e arrefecimento
    (a ``t_arrefecimento_c``); toda perda mecânica, elétrica e de frenagem é exergia destruída;
    a energia elétrica (bateria, rede) é exergia pura.
    """
    t0 = t0_c + 273.15
    arq = f["arquitetura"]
    ex_comb = f["combustivel_ex"]
    w_motor = f["motor_eixo"]
    q = max(f["combustivel_pci"] - w_motor, 0.0)
    ex_escape = fracao_escape * q * _fator_escape(t0, t_escape_c + 273.15)
    ex_arref = (1 - fracao_escape) * q * max(1 - t0 / (t_arrefecimento_c + 273.15), 0.0)
    itens = {
        "motor_destruicao": ex_comb - w_motor - ex_escape - ex_arref if ex_comb > 0 else 0.0,
        "escape": ex_escape,
        "arrefecimento": ex_arref,
        "acessorios": f["acessorios"],
        "motor_eletrico": (f["el_pos"] - f["em_pos"]) + (f["em_neg"] - f["el_neg"]),
        "bateria": 0.0,
        "carregador": 0.0,
        "aerodinamica": f["aerodinamica"],
        "rolamento": f["rolamento"],
        "rampa": f["rampa"],
    }
    entrada_comb, entrada_el, renovavel, armazenada_bat = ex_comb, 0.0, ex_comb * f["renovavel_comb"], 0.0
    if arq != "combustao":
        itens["bateria"] = f["bateria"] - (f["el_pos"] - f["el_neg"] + f["acessorios"])
        if arq == "eletrico":
            entrada_el = f["bateria"] / f["eta_carregador"]
            itens["carregador"] = entrada_el - f["bateria"]
        elif f["bateria"] >= 0:
            entrada_el = f["bateria"]  # híbrido: energia líquida retirada da bateria
        else:
            armazenada_bat = -f["bateria"]
        renovavel += entrada_el * (f["renovavel_rede"] if arq == "eletrico" else f["renovavel_comb"])
    eta_t = f["eta_transmissao"]
    regen_roda = f["regen_eixo"] / eta_t
    acc_mec = f["acessorios"] if arq == "combustao" else 0.0
    carga = f["em_neg"] - f["regen_eixo"]  # recarga da bateria pelo motor a combustão (híbrido)
    itens["transmissao"] = (w_motor - acc_mec) - carga + f["em_pos"] - f["roda_pos"] + (regen_roda - f["regen_eixo"])
    itens["freios"] = f["frenagem"] - regen_roda
    itens["armazenada_bateria"] = armazenada_bat

    entrada = entrada_comb + entrada_el
    entrada_energia = f["combustivel_pci"] + entrada_el
    saida = sum(itens.values())
    d = max(f["distancia_km"], 1e-9)
    grupos = {
        "motor_destruicao": itens["motor_destruicao"],
        "calor_rejeitado": itens["escape"] + itens["arrefecimento"],
        "trem_eletrico": itens["motor_eletrico"] + itens["bateria"] + itens["carregador"],
        "transmissao": itens["transmissao"],
        "acessorios": itens["acessorios"],
        "resistencias": itens["aerodinamica"] + itens["rolamento"],
        "frenagem": itens["freios"],
        "armazenada": itens["rampa"] + itens["armazenada_bateria"],
    }
    return {
        "entrada_mj_km": entrada / d,
        "entrada_combustivel_mj_km": entrada_comb / d,
        "entrada_eletrica_mj_km": entrada_el / d,
        "trabalho_rodas_mj_km": f["roda_pos"] / d,
        "eficiencia_2a_lei": f["roda_pos"] / entrada if entrada > 0 else None,
        "eficiencia_1a_lei": f["roda_pos"] / entrada_energia if entrada_energia > 0 else None,
        "fracao_renovavel": renovavel / entrada if entrada > 0 else None,
        "itens_mj_km": {k: v / d for k, v in itens.items()},
        "grupos_mj_km": {k: v / d for k, v in grupos.items()},
        "fechamento": (entrada - saida) / entrada if entrada > 0 else 0.0,
    }


def _combinar_exergia(u: dict, e: dict) -> dict:
    """Combina urbano e estrada por km (55/45), como no PBEV."""
    def mix(a, b):
        return PESO_URBANO * a + PESO_ESTRADA * b

    out = {k: mix(u[k], e[k]) for k in ("entrada_mj_km", "entrada_combustivel_mj_km", "entrada_eletrica_mj_km",
                                           "trabalho_rodas_mj_km")}
    for chave in ("itens_mj_km", "grupos_mj_km"):
        out[chave] = {k: mix(u[chave][k], e[chave][k]) for k in u[chave]}
    ent = out["entrada_mj_km"]
    out["eficiencia_2a_lei"] = out["trabalho_rodas_mj_km"] / ent if ent > 0 else None
    eu, ee = u.get("eficiencia_1a_lei"), e.get("eficiencia_1a_lei")
    out["eficiencia_1a_lei"] = None
    if eu and ee:
        en = mix(u["trabalho_rodas_mj_km"] / eu, e["trabalho_rodas_mj_km"] / ee)
        out["eficiencia_1a_lei"] = out["trabalho_rodas_mj_km"] / en
    ru, re_ = u.get("fracao_renovavel") or 0.0, e.get("fracao_renovavel") or 0.0
    out["fracao_renovavel"] = mix(ru * u["entrada_mj_km"], re_ * e["entrada_mj_km"]) / ent if ent > 0 else None
    return out


def _arredondar(x):
    if isinstance(x, dict):
        return {k: _arredondar(v) for k, v in x.items()}
    if isinstance(x, float):
        return _seguro(x, 4)
    return x


def exergia_cenario(indicadores: dict, ensaio_tipo: str, params: dict) -> dict | None:
    """Análise exergética de um cenário a partir dos indicadores de ciclo (com 'fluxos')."""
    if ensaio_tipo == "ensaio_pbev":
        u = exergia_ciclo(indicadores["urbano"]["fluxos"], **params)
        e = exergia_ciclo(indicadores["estrada"]["fluxos"], **params)
        return _arredondar({"urbano": u, "estrada": e, "principal": _combinar_exergia(u, e)})
    if ensaio_tipo == "ciclo":
        c = exergia_ciclo(indicadores["ciclo"]["fluxos"], **params)
        return _arredondar({"ciclo": c, "principal": c})
    return None
