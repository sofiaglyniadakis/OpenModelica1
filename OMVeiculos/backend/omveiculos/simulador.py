"""Motor de cálculo rápido (Python) - abordagem quasi-estática "para trás".

O veículo segue exatamente o perfil de velocidade do ciclo. Em cada intervalo de
1 s a aceleração é constante e as decisões discretas (marcha, relação do CVT,
liga/desliga do motor a combustão no híbrido) são tomadas no início do
intervalo. As grandezas contínuas (rotação, potência, vazão de combustível,
SOC) são integradas com ``N_SUB`` subpassos por segundo (regra do ponto médio).

A biblioteca Modelica ``VeiculosLevesBR`` implementa o mesmo modelo usando
``when sample(0, 1)`` para as decisões e integração contínua (DASSL) para o
restante, o que permite comparar os dois motores de cálculo.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

from dataclasses import dataclass, field

import numpy as np

from .ciclos import Ciclo
from .combustiveis import Combustivel
from .componentes import (
    G,
    RPM,
    V_PARADO,
    Ambiente,
    Bateria,
    Hibrido,
    MotorCombustao,
    MotorEletrico,
    Transmissao,
    Veiculo,
    clamp,
)

N_SUB = 10


@dataclass
class TremDeForca:
    arquitetura: str  # 'combustao' | 'eletrico' | 'hibrido'
    veiculo: Veiculo
    transmissao: Transmissao
    motor: MotorCombustao | None = None
    combustivel: Combustivel | None = None
    eletrico: MotorEletrico | None = None
    bateria: Bateria | None = None
    hibrido: Hibrido | None = None

    def classificacao(self) -> tuple[float, float]:
        assert self.motor is not None and self.combustivel is not None
        return self.motor.classificacao(self.combustivel.tipo)

    def eta_motor(self) -> float:
        assert self.motor is not None and self.combustivel is not None
        return self.motor.eficiencia(self.combustivel.fracao_etanol_vol)


@dataclass
class ResultadoCiclo:
    ciclo_id: str
    ciclo_nome: str
    fases: tuple[float, ...]
    t: np.ndarray
    v_kmh: np.ndarray
    distancia_m: np.ndarray  # acumulado
    combustivel_kg: np.ndarray  # acumulado
    energia_bat_j: np.ndarray  # energia interna líquida retirada da bateria (acumulado)
    soc: np.ndarray  # %
    marcha: np.ndarray
    rpm: np.ndarray  # média no intervalo
    p_motor_kw: np.ndarray  # motor a combustão (eixo), média no intervalo
    p_eletrico_kw: np.ndarray  # motor elétrico (eixo), média no intervalo
    p_roda_kw: np.ndarray
    energia_motor_mec_j: float = 0.0  # trabalho positivo no eixo do motor a combustão
    energias: dict = field(default_factory=dict)  # balanço de energia na roda (J)
    fluxos: dict = field(default_factory=dict)  # energias nas interfaces do trem de força (J), p/ análise exergética
    tempo_excedido_s: float = 0.0  # tempo em que o trem de força não atende a demanda


def escolher_relacao(
    tr: Transmissao, motor: MotorCombustao | None, w_roda: float, p_entrada: float, p_max: float, t_max: float
) -> tuple[int, float]:
    """Marcha (ou relação do CVT) para o intervalo. Retorna (marcha, relação total)."""
    if tr.tipo == "redutor" or motor is None:
        return 1, tr.relacoes[0] * tr.diferencial
    frac = clamp(p_entrada / p_max, 0.0, 1.0) if p_max > 0 else 0.0
    w_alvo = (tr.rpm_troca_min + (tr.rpm_troca_max - tr.rpm_troca_min) * frac) * RPM
    if tr.tipo == "cvt":
        r_min, r_max = tr.cvt_min * tr.diferencial, tr.cvt_max * tr.diferencial
        if w_roda < 1e-3:
            return 1, r_max
        return 1, clamp(w_alvo / w_roda, r_min, r_max)
    n = len(tr.relacoes)
    for g in range(n, 0, -1):
        r = tr.relacoes[g - 1] * tr.diferencial
        w_e = w_roda * r
        if w_e < w_alvo or w_e > motor.w_max:
            continue
        if p_entrada > 0 and p_entrada / w_e > 0.95 * motor.torque_max(w_e, p_max, t_max):
            continue
        return g, r
    for g in range(1, n + 1):
        r = tr.relacoes[g - 1] * tr.diferencial
        if w_roda * r <= motor.w_max:
            return g, r
    return n, tr.relacoes[-1] * tr.diferencial


def simular_ciclo(pt: TremDeForca, ciclo: Ciclo, amb: Ambiente, n_sub: int = N_SUB) -> ResultadoCiclo:
    veh, tr = pt.veiculo, pt.transmissao
    motor, el, bat, hib = pt.motor, pt.eletrico, pt.bateria, pt.hibrido
    arq = pt.arquitetura
    usa_ice = arq in ("combustao", "hibrido")
    usa_el = arq in ("eletrico", "hibrido")

    v = ciclo.v
    n = len(v)
    dt = 1.0 / n_sub
    r = veh.raio
    m_eq = veh.massa_equivalente
    eta_t = tr.eficiencia
    p_acc = veh.p_acessorios

    if usa_ice:
        p_max, t_max = pt.classificacao()
        eta_i = pt.eta_motor()
        pci_j = pt.combustivel.pci * 1e6  # J/kg
        w_lenta = motor.w_lenta
        w_corte = motor.rpm_corte * RPM
        t_lenta = motor.torque_max(w_lenta, p_max, t_max)
        p_f_lenta = motor.potencia_combustivel(w_lenta, p_acc, t_lenta, eta_i)
    else:
        p_max = t_max = 0.0
    if usa_el:
        e_bat = bat.energia_j
        eta_b = bat.eficiencia
        eta_m = el.eficiencia
        soc = bat.soc_inicial
    else:
        soc = 0.0

    serie = {k: np.zeros(n) for k in ("dist", "comb", "ebat", "soc", "marcha", "rpm", "pm", "pe", "pr")}
    dist = comb = ebat = 0.0
    e_mec = excedido = 0.0
    e_aero = e_rol = e_rampa = e_freio = 0.0
    fx = dict.fromkeys(("acessorios", "roda_pos", "em_pos", "em_neg", "el_pos", "el_neg", "regen_eixo"), 0.0)
    serie["soc"][0] = soc

    def regen(p_mec_roda: float, vt: float, w_m: float, soc_atual: float) -> float:
        """Potência mecânica regenerada no eixo do motor elétrico (<= 0)."""
        if vt * 3.6 <= el.v_min_regeneracao or soc_atual >= bat.soc_max:
            return 0.0
        p = max(p_mec_roda * eta_t * el.fracao_regeneracao, -el.p_max)
        return max(p, -el.torque_disponivel(w_m) * w_m)

    for k in range(n - 1):
        v0, v1 = v[k], v[k + 1]
        a = v1 - v0
        parado = v0 < V_PARADO and v1 < V_PARADO
        v_rep = 0.5 * (v0 + v1)
        f_rep = m_eq * a + veh.forca_resistencia(v_rep, amb)
        p_rep = f_rep * v_rep
        p_ent_rep = p_rep / eta_t if p_rep > 0 else p_rep * eta_t
        marcha, rel = 0, 0.0
        if not parado:
            marcha, rel = escolher_relacao(tr, motor if usa_ice else None, v_rep / r, p_ent_rep, p_max, t_max)
        ice_ligado = arq == "combustao"
        p_carga = 0.0
        if arq == "hibrido" and not parado and p_rep > 0:
            modo_eletrico = (
                soc > bat.soc_min
                and v_rep * 3.6 <= hib.v_max_eletrico
                and p_ent_rep <= hib.p_max_eletrico * 1000.0
            )
            ice_ligado = not modo_eletrico
            p_carga = clamp((hib.soc_alvo - soc) / 10.0, 0.0, 1.0) * hib.p_carga_max * 1000.0

        soma = {"rpm": 0.0, "pm": 0.0, "pe": 0.0, "pr": 0.0}
        for j in range(n_sub):
            vt = v0 + a * (j + 0.5) / n_sub
            p_f = 0.0  # potência do combustível (W)
            p_ice = 0.0  # potência no eixo do motor a combustão
            w_e = 0.0
            p_em = 0.0  # potência mecânica do motor elétrico
            p_el = 0.0  # potência elétrica do motor elétrico
            acc_no_motor = False  # acessórios supridos pelo motor a combustão neste instante
            if parado:
                p_roda = 0.0
                if arq == "combustao" and not motor.start_stop:
                    w_e = w_lenta
                    p_ice = p_acc
                    p_f = p_f_lenta
                    acc_no_motor = True
            else:
                f_rol, f_aero, f_rampa = veh.forcas(vt, amb)
                f = m_eq * a + f_rol + f_aero + f_rampa
                p_roda = f * vt
                w_in = vt / r * rel
                # balanço de energia na roda
                e_rol += f_rol * vt * dt
                e_aero += f_aero * vt * dt
                e_rampa += f_rampa * vt * dt
                if f < 0:
                    e_freio += -p_roda * dt
                if f >= 0:
                    t_in = f * r / (rel * eta_t)
                    if arq == "combustao" or (arq == "hibrido" and ice_ligado):
                        w_e = max(w_in, w_lenta)
                        t_disp = motor.torque_max(w_e, p_max, t_max)
                        if arq == "combustao":
                            t_ice = t_in
                            if t_ice > t_disp:
                                excedido += dt
                            p_ice = t_ice * w_e + p_acc
                            acc_no_motor = True
                        else:
                            t_ice = min(t_in + p_carga / w_e, t_disp)
                            t_em = t_in - t_ice
                            t_em_disp = el.torque_disponivel(w_in)
                            if t_em > 0 and soc <= bat.soc_min:
                                t_em = 0.0
                                t_ice = t_in
                            if t_em > t_em_disp:
                                excedido += dt
                            t_em = max(t_em, -t_em_disp)
                            t_ice = t_in - t_em
                            p_ice = t_ice * w_e
                            p_em = t_em * w_in
                        p_f = motor.potencia_combustivel(w_e, p_ice, t_disp, eta_i)
                    else:  # tração 100 % elétrica
                        if t_in > el.torque_disponivel(w_in):
                            excedido += dt
                        p_em = t_in * w_in
                else:
                    p_ent = p_roda * eta_t
                    if arq == "combustao":
                        if motor.corte_combustivel and w_in >= w_corte:
                            w_e = w_in
                            p_ice = p_ent
                        else:
                            w_e = w_lenta
                            p_ice = p_acc
                            p_f = p_f_lenta
                            acc_no_motor = True
                    else:
                        p_em = regen(p_roda, vt, w_in, soc)
                        fx["regen_eixo"] += -p_em * dt
                if usa_el:
                    p_el = p_em / eta_m if p_em >= 0 else p_em * eta_m

            if p_roda > 0:
                fx["roda_pos"] += p_roda * dt
            if acc_no_motor or usa_el:
                fx["acessorios"] += p_acc * dt
            if p_em >= 0:
                fx["em_pos"] += p_em * dt
                fx["el_pos"] += p_el * dt
            else:
                fx["em_neg"] += -p_em * dt
                fx["el_neg"] += -p_el * dt
            if usa_el:
                p_bat = p_el + p_acc
                p_int = p_bat / eta_b if p_bat >= 0 else p_bat * eta_b
                ebat += p_int * dt
                soc -= p_int * dt / e_bat * 100.0
            if usa_ice:
                comb += p_f / pci_j * dt
                if p_ice > 0:
                    e_mec += p_ice * dt
            dist += vt * dt
            soma["rpm"] += w_e / RPM
            soma["pm"] += p_ice / 1000.0
            soma["pe"] += p_em / 1000.0
            soma["pr"] += p_roda / 1000.0

        i = k + 1
        serie["dist"][i] = dist
        serie["comb"][i] = comb
        serie["ebat"][i] = ebat
        serie["soc"][i] = soc
        serie["marcha"][k] = marcha
        for chave in ("rpm", "pm", "pe", "pr"):
            serie[chave][k] = soma[chave] / n_sub

    energias = {
        "aerodinamica": e_aero,
        "rolamento": e_rol,
        "rampa": e_rampa,
        "frenagem": e_freio,
    }
    return ResultadoCiclo(
        ciclo_id=ciclo.id,
        ciclo_nome=ciclo.nome,
        fases=ciclo.fases,
        t=np.arange(n, dtype=float),
        v_kmh=ciclo.v_kmh,
        distancia_m=serie["dist"],
        combustivel_kg=serie["comb"],
        energia_bat_j=serie["ebat"],
        soc=serie["soc"],
        marcha=serie["marcha"],
        rpm=serie["rpm"],
        p_motor_kw=serie["pm"],
        p_eletrico_kw=serie["pe"],
        p_roda_kw=serie["pr"],
        energia_motor_mec_j=e_mec,
        energias=energias,
        fluxos=fx,
        tempo_excedido_s=excedido,
    )


# --- Desempenho (aceleração plena) ---------------------------------------------


def relacoes_candidatas(pt: TremDeForca, w_roda: float) -> list[float]:
    tr = pt.transmissao
    if tr.tipo == "redutor" or pt.arquitetura == "eletrico":
        return [tr.relacoes[0] * tr.diferencial]
    if tr.tipo == "cvt":
        r_min, r_max = tr.cvt_min * tr.diferencial, tr.cvt_max * tr.diferencial
        if w_roda < 1e-3:
            return [r_max]
        return [clamp(pt.motor.rpm_potencia * RPM / w_roda, r_min, r_max)]
    return [x * tr.diferencial for x in tr.relacoes]


def _tracao_por_relacao(pt: TremDeForca, v: float, mu: float) -> list[tuple[float, float]]:
    """(força de tração [N], inércia girante refletida na roda [kg]) para cada relação viável."""
    veh, tr = pt.veiculo, pt.transmissao
    w_roda = v / veh.raio
    if pt.arquitetura != "eletrico":
        p_max, t_max = pt.classificacao()
    limite = mu * veh.massa_total * G * veh.fracao_eixo_motriz
    saida = []
    for rel in relacoes_candidatas(pt, w_roda):
        w_in = w_roda * rel
        torque = inercia = 0.0
        if pt.arquitetura != "eletrico":
            if w_in > pt.motor.w_max:
                continue
            w_e = max(w_in, tr.rpm_partida * RPM)
            torque += pt.motor.torque_max(w_e, p_max, t_max)
            inercia += pt.motor.inercia
        if pt.arquitetura != "combustao":
            torque += pt.eletrico.torque_disponivel(w_in)
            inercia += pt.eletrico.inercia
        forca = min(torque * rel * tr.eficiencia / veh.raio, limite)
        saida.append((forca, inercia * (rel / veh.raio) ** 2))
    return saida


def forca_tracao_maxima(pt: TremDeForca, v: float, mu: float) -> float:
    return max((f for f, _ in _tracao_por_relacao(pt, v, mu)), default=0.0)


def aceleracao_maxima(pt: TremDeForca, v: float, amb: Ambiente, mu: float) -> float:
    """Aceleração (m/s2) na melhor marcha, incluindo a inércia do motor refletida na roda."""
    f_res = pt.veiculo.forca_resistencia(v, amb)
    m_eq = pt.veiculo.massa_equivalente
    return max(((f - f_res) / (m_eq + m_j) for f, m_j in _tracao_por_relacao(pt, v, mu)), default=-f_res / m_eq)


@dataclass
class ResultadoDesempenho:
    t_0_100: float | None
    t_80_120: float | None
    v_max_kmh: float
    t: np.ndarray
    v_kmh: np.ndarray


def velocidade_maxima(pt: TremDeForca, amb: Ambiente, mu: float) -> float:
    def excesso(v: float) -> float:
        return forca_tracao_maxima(pt, v, mu) - pt.veiculo.forca_resistencia(v, amb)

    v_ant = 1.0
    if excesso(v_ant) <= 0:
        return 0.0
    v = v_ant
    while v < 120.0:
        v += 0.25
        if excesso(v) <= 0:
            lo, hi = v - 0.25, v
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if excesso(mid) > 0:
                    lo = mid
                else:
                    hi = mid
            return lo * 3.6
    return v * 3.6


def simular_desempenho(
    pt: TremDeForca, amb: Ambiente, mu: float = 0.9, t_final: float = 90.0, dt: float = 0.01
) -> ResultadoDesempenho:
    def dvdt(v: float) -> float:
        return aceleracao_maxima(pt, v, amb, mu)

    marcos = {80: None, 100: None, 120: None}
    t, v = 0.0, 0.0
    ts, vs = [0.0], [0.0]
    passo_registro = max(int(round(0.1 / dt)), 1)
    i = 0
    while t < t_final - 1e-12:
        k1 = dvdt(v)
        k2 = dvdt(v + 0.5 * dt * k1)
        k3 = dvdt(v + 0.5 * dt * k2)
        k4 = dvdt(v + dt * k3)
        v_novo = max(v + dt / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4), 0.0)
        for alvo in marcos:
            vm = alvo / 3.6
            if marcos[alvo] is None and v < vm <= v_novo:
                marcos[alvo] = t + dt * (vm - v) / (v_novo - v)
        t += dt
        v = v_novo
        i += 1
        if i % passo_registro == 0:
            ts.append(t)
            vs.append(v * 3.6)
        if marcos[120] is not None and t > marcos[120] + 2.0:
            break
    t_80_120 = marcos[120] - marcos[80] if marcos[120] is not None and marcos[80] is not None else None
    return ResultadoDesempenho(
        t_0_100=marcos[100],
        t_80_120=t_80_120,
        v_max_kmh=velocidade_maxima(pt, amb, mu),
        t=np.array(ts),
        v_kmh=np.array(vs),
    )
