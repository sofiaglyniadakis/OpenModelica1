"""Componentes físicos do veículo (modelos quasi-estáticos).

As mesmas equações estão implementadas na biblioteca Modelica
``VeiculosLevesBR`` (pasta ``OMVeiculos/modelica``). Qualquer alteração aqui
deve ser refletida lá - o teste ``test_modelica.py`` compara os dois motores de
cálculo quando o ``omc`` está disponível.

Unidades internas: SI (m, s, kg, N, W, rad/s). Os parâmetros vindos da interface
usam as unidades das fichas técnicas brasileiras (cv, kgfm, km/h, rpm).
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

import math
import re
from dataclasses import dataclass, field

G = 9.80665
CV = 735.49875  # W
KGFM = 9.80665  # N.m
RPM = math.pi / 30.0  # rad/s por rpm
V_PARADO = 0.1  # m/s, abaixo disso o veículo é considerado parado


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def densidade_ar(temperatura_c: float, altitude_m: float) -> float:
    """Densidade do ar seco pela atmosfera padrão (kg/m3)."""
    p = 101325.0 * (1.0 - 2.25577e-5 * altitude_m) ** 5.25588
    return p / (287.05 * (temperatura_c + 273.15))


def raio_pneu(codigo: str) -> float:
    """Raio dinâmico (m) a partir da medida do pneu, ex.: '185/65 R15'."""
    m = re.match(r"\s*(\d{3})\s*/\s*(\d{2})\s*[A-Za-z]*\s*(\d{2})", codigo or "")
    if not m:
        raise ValueError(f"Medida de pneu inválida: '{codigo}'. Use o formato 185/65 R15.")
    largura, perfil, aro = (int(g) for g in m.groups())
    raio_estatico = aro * 0.0254 / 2 + largura * perfil / 100 / 1000
    return 0.975 * raio_estatico


@dataclass
class Ambiente:
    temperatura: float = 25.0  # °C
    altitude: float = 0.0  # m
    inclinacao: float = 0.0  # %

    @property
    def rho(self) -> float:
        return densidade_ar(self.temperatura, self.altitude)

    @property
    def theta(self) -> float:
        return math.atan(self.inclinacao / 100.0)


@dataclass
class Veiculo:
    nome: str = "Veículo"
    massa: float = 1050.0  # kg, em ordem de marcha
    carga: float = 136.0  # kg, ocupantes/carga (ensaio: +136 kg)
    fator_inercia: float = 0.03  # acréscimo de massa equivalente das partes girantes
    modo_resistencia: str = "fisico"  # 'fisico' ou 'coastdown'
    cd: float = 0.32
    area_frontal: float = 2.1  # m2
    cr: float = 0.011
    f0: float = 110.0  # N
    f1: float = 0.0  # N/(km/h)
    f2: float = 0.035  # N/(km/h)^2
    raio: float = 0.30  # m
    fracao_eixo_motriz: float = 0.6
    potencia_acessorios: float = 300.0  # W
    ar_condicionado: bool = False
    potencia_ar: float = 1500.0  # W
    tanque: float = 47.0  # unidades do combustível (L, m3)

    @property
    def massa_total(self) -> float:
        return self.massa + self.carga

    @property
    def massa_equivalente(self) -> float:
        return self.massa_total * (1.0 + self.fator_inercia)

    @property
    def p_acessorios(self) -> float:
        return self.potencia_acessorios + (self.potencia_ar if self.ar_condicionado else 0.0)

    def forcas(self, v: float, amb: Ambiente) -> tuple[float, float, float]:
        """(rolamento, aerodinâmica, rampa) em N.

        No modo coast-down, F0 + F1 v é atribuído ao rolamento e F2 v² à
        aerodinâmica (separação usual para curvas de desaceleração livre)."""
        m = self.massa_total
        mov = 1.0 if v > 1e-3 else 0.0
        rampa = m * G * math.sin(amb.theta)
        if self.modo_resistencia == "coastdown":
            vk = v * 3.6
            return mov * (self.f0 + self.f1 * vk), self.f2 * vk * vk, rampa
        rol = mov * self.cr * m * G * math.cos(amb.theta)
        aero = 0.5 * amb.rho * self.cd * self.area_frontal * v * v
        return rol, aero, rampa

    def forca_resistencia(self, v: float, amb: Ambiente) -> float:
        """Forças de rolamento + aerodinâmica + rampa (N)."""
        rol, aero, rampa = self.forcas(v, amb)
        return rol + aero + rampa


@dataclass
class MotorCombustao:
    nome: str = "Motor"
    tipo: str = "flex"  # flex | gasolina | diesel
    cilindrada: float = 1.0  # L
    potencia_g: float = 75.0  # cv (gasolina C ou diesel)
    potencia_e: float = 77.0  # cv (etanol)
    torque_g: float = 10.0  # kgfm
    torque_e: float = 10.4  # kgfm
    rpm_lenta: float = 850.0
    rpm_torque_ini: float = 3500.0
    rpm_torque_fim: float = 4000.0
    rpm_potencia: float = 6000.0
    rpm_max: float = 6500.0
    eficiencia_indicada: float = 0.37
    fmep0: float = 0.97  # bar
    fmep1: float = 0.15  # bar/krpm
    fmep2: float = 0.05  # bar/krpm^2
    pmep0: float = 0.6  # bar, perda de bombeamento em carga nula
    ganho_etanol: float = 0.04  # ganho relativo de eficiência por fração vol. de etanol
    fator_gnv: float = 0.85  # potência relativa ao usar GNV
    inercia: float = 0.15  # kg.m2, motor + volante (usado no ensaio de desempenho)
    start_stop: bool = False
    corte_combustivel: bool = True
    rpm_corte: float = 1100.0

    def classificacao(self, comb_tipo: str) -> tuple[float, float]:
        """(potência máx [W], torque máx [N.m]) para o combustível."""
        if comb_tipo == "etanol" and self.tipo == "flex":
            return self.potencia_e * CV, self.torque_e * KGFM
        if comb_tipo == "gnv":
            return self.potencia_g * CV * self.fator_gnv, self.torque_g * KGFM * self.fator_gnv
        return self.potencia_g * CV, self.torque_g * KGFM

    def eficiencia(self, fracao_etanol_vol: float) -> float:
        return self.eficiencia_indicada * (1.0 + self.ganho_etanol * fracao_etanol_vol)

    @property
    def w_lenta(self) -> float:
        return self.rpm_lenta * RPM

    @property
    def w_max(self) -> float:
        return self.rpm_max * RPM

    def torque_max(self, w: float, p_max: float, t_max: float) -> float:
        """Curva de torque a plena carga (N.m) em função da rotação (rad/s)."""
        rpm = clamp(w / RPM, self.rpm_lenta, self.rpm_max)
        r1 = max(self.rpm_torque_ini, self.rpm_lenta + 1.0)
        r2 = max(self.rpm_torque_fim, r1)
        rp = max(self.rpm_potencia, r2 + 1.0)
        t_p = p_max / (rp * RPM)
        if rpm <= r1:
            t = t_max * (0.55 + 0.45 * (rpm - self.rpm_lenta) / (r1 - self.rpm_lenta))
        elif rpm <= r2:
            t = t_max
        elif rpm <= rp:
            t = t_max + (t_p - t_max) * (rpm - r2) / (rp - r2)
        else:
            t = t_p * (1.0 - 0.6 * (rpm - rp) / max(self.rpm_max - rp, 1.0))
        return min(t, p_max / (rpm * RPM))

    def potencia_perdas(self, w: float, carga: float) -> float:
        """Atrito + bombeamento (W) na rotação w e fração de carga [0..1]."""
        krpm = w / RPM / 1000.0
        fmep = self.fmep0 + self.fmep1 * krpm + self.fmep2 * krpm * krpm
        pmep = self.pmep0 * (1.0 - clamp(carga, 0.0, 1.0))
        return (fmep + pmep) * 1e5 * self.cilindrada * 1e-3 * w / (4.0 * math.pi)

    def potencia_combustivel(self, w: float, p_eixo: float, t_max_w: float, eta_i: float) -> float:
        """Potência química do combustível (W) - modelo de Willans com perdas."""
        carga = (p_eixo / w) / t_max_w if t_max_w > 0 else 0.0
        return max(p_eixo + self.potencia_perdas(w, carga), 0.0) / eta_i


@dataclass
class MotorEletrico:
    nome: str = "Motor elétrico"
    potencia: float = 95.0  # cv (pico)
    torque: float = 18.3  # kgfm (pico)
    rpm_max: float = 12000.0
    eficiencia: float = 0.90  # média motor + inversor
    fracao_regeneracao: float = 0.7
    v_min_regeneracao: float = 5.0  # km/h
    inercia: float = 0.04  # kg.m2, rotor (usado no ensaio de desempenho)

    @property
    def p_max(self) -> float:
        return self.potencia * CV

    @property
    def t_max(self) -> float:
        return self.torque * KGFM

    def torque_disponivel(self, w: float) -> float:
        if w > self.rpm_max * RPM:
            return 0.0
        return min(self.t_max, self.p_max / max(w, 1e-6))


@dataclass
class Bateria:
    nome: str = "Bateria"
    capacidade: float = 44.9  # kWh (bruta)
    soc_inicial: float = 90.0  # %
    soc_min: float = 10.0
    soc_max: float = 95.0
    eficiencia: float = 0.96  # carga/descarga
    eficiencia_carregador: float = 0.90  # tomada -> bateria

    @property
    def energia_j(self) -> float:
        return self.capacidade * 3.6e6


@dataclass
class Transmissao:
    nome: str = "Transmissão"
    tipo: str = "manual"  # manual | automatica | cvt | redutor
    relacoes: list[float] = field(default_factory=lambda: [3.73, 2.05, 1.32, 0.97, 0.76])
    diferencial: float = 4.07
    eficiencia: float = 0.96
    cvt_min: float = 0.40
    cvt_max: float = 2.60
    rpm_troca_min: float = 1600.0
    rpm_troca_max: float = 4500.0
    rpm_partida: float = 1300.0  # rotação de patinação da embreagem/conversor na arrancada

    def relacao_total(self, marcha: int) -> float:
        if self.tipo == "cvt":
            return self.cvt_max * self.diferencial
        return self.relacoes[marcha - 1] * self.diferencial

    @property
    def n_marchas(self) -> int:
        return 1 if self.tipo in ("redutor", "cvt") else len(self.relacoes)


@dataclass
class Hibrido:
    """Estratégia de gerenciamento de energia do híbrido paralelo (P2)."""

    v_max_eletrico: float = 50.0  # km/h
    p_max_eletrico: float = 12.0  # kW na entrada da transmissão
    soc_alvo: float = 55.0  # %
    p_carga_max: float = 6.0  # kW de recarga pelo motor a combustão
