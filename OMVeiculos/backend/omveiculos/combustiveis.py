"""Combustíveis e energéticos do mercado brasileiro.

As propriedades das misturas (gasolina C, etanol hidratado, diesel B) são
calculadas a partir dos componentes puros, de modo que o teor de etanol anidro
na gasolina ou de biodiesel no diesel pode ser alterado pelo usuário quando a
legislação mudar.

Valores de referência (editáveis na interface):

* Teor de etanol anidro na gasolina C: 30 % v/v (Lei 14.993/2024 - "Combustível
  do Futuro", em vigor desde 1/8/2025).
* Teor de biodiesel no diesel B: 15 % v/v (B15, desde 1/8/2025).
* Etanol hidratado combustível (EHC): 93,5 % m/m de etanol (faixa ANP 92,5-94,6 %).
* Intensidade de carbono "poço à roda" (gCO2e/MJ): gasolina A e diesel A conforme
  os valores fósseis de referência do RenovaBio; etanol de cana e biodiesel com
  valores típicos de certificação - variam por usina e devem ser revisados.
* Fator de emissão da eletricidade: ordem de grandeza do fator médio do SIN
  publicado pelo MCTI; atualize com o valor do ano de interesse.
* Preços: apenas referência para cálculo de custo; edite com os valores da ANP
  ou do seu posto.

O CO2 "fóssil" de escapamento conta somente o carbono de origem fóssil, como no
Programa Brasileiro de Etiquetagem Veicular (PBEV): o CO2 do etanol e do
biodiesel é considerado biogênico.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

from dataclasses import asdict, dataclass

# --- Componentes puros -------------------------------------------------------
# densidade [kg/L], PCI [MJ/kg], fração mássica de carbono [-], gCO2e/MJ poço-roda
# exergia química padrão [MJ/kg]: etanol 1357,7 kJ/mol (Szargut); gasolina, diesel e biodiesel
# por phi = ex/PCI ~ 1,07 (correlação de Szargut para hidrocarbonetos líquidos); GNV phi ~ 1,04
GASOLINA_A = dict(densidade=0.745, pci=43.5, carbono=0.866, wtw=87.4, exergia=46.5)
ETANOL_ANIDRO = dict(densidade=0.791, pci=26.8, carbono=24.02 / 46.07, wtw=27.0, exergia=29.47)
DIESEL_A = dict(densidade=0.840, pci=42.6, carbono=0.862, wtw=86.5, exergia=45.6)
BIODIESEL = dict(densidade=0.880, pci=37.2, carbono=0.770, wtw=30.0, exergia=39.8)
EXERGIA_AGUA = 0.05  # MJ/kg, água líquida
FRACAO_RENOVAVEL_REDE = 0.88  # participação renovável típica da matriz elétrica brasileira (EPE)
CALOR_VAPORIZACAO_AGUA = 2.44  # MJ/kg, penaliza o PCI do etanol hidratado
CO2_POR_C = 44.01 / 12.011

TIPOS = ("gasolina", "etanol", "diesel", "gnv", "eletricidade")

PRECOS_REFERENCIA = {
    "gasolina": 6.29,  # R$/L
    "etanol": 4.29,  # R$/L
    "diesel": 6.09,  # R$/L
    "gnv": 4.79,  # R$/m3
    "eletricidade": 0.89,  # R$/kWh
}


@dataclass(frozen=True)
class Combustivel:
    """Propriedades por unidade comercial (L, m3 ou kWh)."""

    tipo: str
    nome: str
    unidade: str
    densidade: float  # kg por unidade comercial
    pci: float  # MJ/kg (para eletricidade: MJ por "kg" fictício = 3,6 MJ/kWh)
    co2_fossil: float  # kg CO2 fóssil por kg de combustível
    co2_total: float  # kg CO2 total (fóssil + biogênico) por kg
    wtw: float  # gCO2e/MJ, poço à roda
    fracao_etanol_vol: float  # fração volumétrica de etanol (efeito na eficiência do motor flex)
    preco: float  # R$ por unidade comercial
    exergia: float = 0.0  # exergia química [MJ/kg] (eletricidade: 3,6 MJ/kWh)
    fracao_renovavel: float = 0.0  # fração renovável da exergia (etanol, biodiesel, fontes renováveis)

    @property
    def exergia_por_unidade(self) -> float:
        return self.densidade * self.exergia

    @property
    def energia_por_unidade(self) -> float:
        """MJ por unidade comercial (MJ/L, MJ/m3 ou MJ/kWh)."""
        return self.densidade * self.pci

    def para_dict(self) -> dict:
        d = asdict(self)
        d["energia_por_unidade"] = self.energia_por_unidade
        return d


def _mistura_volumetrica(a: dict, b: dict, x_b: float) -> tuple[float, float, float, float]:
    """Retorna densidade, PCI, fração mássica de b e intensidade wtw da mistura a+b."""
    dens = (1 - x_b) * a["densidade"] + x_b * b["densidade"]
    w_b = x_b * b["densidade"] / dens
    pci = (1 - w_b) * a["pci"] + w_b * b["pci"]
    energia_b = w_b * b["pci"] / pci
    wtw = (1 - energia_b) * a["wtw"] + energia_b * b["wtw"]
    return dens, pci, w_b, wtw


def gasolina_c(teor_etanol: float = 30.0, preco: float | None = None) -> Combustivel:
    x = teor_etanol / 100.0
    dens, pci, w_et, wtw = _mistura_volumetrica(GASOLINA_A, ETANOL_ANIDRO, x)
    fossil = (1 - w_et) * GASOLINA_A["carbono"] * CO2_POR_C
    bio = w_et * ETANOL_ANIDRO["carbono"] * CO2_POR_C
    ex = (1 - w_et) * GASOLINA_A["exergia"] + w_et * ETANOL_ANIDRO["exergia"]
    return Combustivel(
        exergia=ex,
        fracao_renovavel=w_et * ETANOL_ANIDRO["exergia"] / ex,
        tipo="gasolina",
        nome=f"Gasolina C (E{teor_etanol:g})",
        unidade="L",
        densidade=dens,
        pci=pci,
        co2_fossil=fossil,
        co2_total=fossil + bio,
        wtw=wtw,
        fracao_etanol_vol=x,
        preco=PRECOS_REFERENCIA["gasolina"] if preco is None else preco,
    )


def etanol_hidratado(teor_massico: float = 93.5, preco: float | None = None) -> Combustivel:
    w = teor_massico / 100.0
    # densidade a 20 °C aproximada linearmente na faixa da especificação ANP
    dens = 0.8096 + (93.5 - teor_massico) * 0.0024
    pci = w * ETANOL_ANIDRO["pci"] - (1 - w) * CALOR_VAPORIZACAO_AGUA
    x_vol = w * dens / ETANOL_ANIDRO["densidade"]
    bio = w * ETANOL_ANIDRO["carbono"] * CO2_POR_C
    ex = w * ETANOL_ANIDRO["exergia"] + (1 - w) * EXERGIA_AGUA
    return Combustivel(
        exergia=ex,
        fracao_renovavel=1.0,
        tipo="etanol",
        nome="Etanol hidratado (EHC)",
        unidade="L",
        densidade=dens,
        pci=pci,
        co2_fossil=0.0,
        co2_total=bio,
        wtw=ETANOL_ANIDRO["wtw"],
        fracao_etanol_vol=x_vol,
        preco=PRECOS_REFERENCIA["etanol"] if preco is None else preco,
    )


def diesel_b(teor_biodiesel: float = 15.0, preco: float | None = None) -> Combustivel:
    x = teor_biodiesel / 100.0
    dens, pci, w_bio, wtw = _mistura_volumetrica(DIESEL_A, BIODIESEL, x)
    fossil = (1 - w_bio) * DIESEL_A["carbono"] * CO2_POR_C
    bio = w_bio * BIODIESEL["carbono"] * CO2_POR_C
    ex = (1 - w_bio) * DIESEL_A["exergia"] + w_bio * BIODIESEL["exergia"]
    return Combustivel(
        exergia=ex,
        fracao_renovavel=w_bio * BIODIESEL["exergia"] / ex,
        tipo="diesel",
        nome=f"Diesel S10 (B{teor_biodiesel:g})",
        unidade="L",
        densidade=dens,
        pci=pci,
        co2_fossil=fossil,
        co2_total=fossil + bio,
        wtw=wtw,
        fracao_etanol_vol=0.0,
        preco=PRECOS_REFERENCIA["diesel"] if preco is None else preco,
    )


def gnv(preco: float | None = None) -> Combustivel:
    # gás natural veicular, m3 a 20 °C e 1 atm
    co2 = 2.66
    return Combustivel(
        exergia=47.5 * 1.04,
        fracao_renovavel=0.0,
        tipo="gnv",
        nome="GNV",
        unidade="m³",
        densidade=0.766,
        pci=47.5,
        co2_fossil=co2,
        co2_total=co2,
        wtw=68.0,
        fracao_etanol_vol=0.0,
        preco=PRECOS_REFERENCIA["gnv"] if preco is None else preco,
    )


def eletricidade(
    fator_emissao_g_kwh: float = 40.0, preco: float | None = None, fracao_renovavel: float = FRACAO_RENOVAVEL_REDE
) -> Combustivel:
    return Combustivel(
        exergia=3.6,
        fracao_renovavel=fracao_renovavel,
        tipo="eletricidade",
        nome="Eletricidade (rede SIN)",
        unidade="kWh",
        densidade=1.0,
        pci=3.6,
        co2_fossil=0.0,
        co2_total=0.0,
        wtw=fator_emissao_g_kwh / 3.6,
        fracao_etanol_vol=0.0,
        preco=PRECOS_REFERENCIA["eletricidade"] if preco is None else preco,
    )


def criar(tipo: str, params: dict | None = None) -> Combustivel:
    """Cria um combustível a partir dos parâmetros do bloco 'Combustível'."""
    p = params or {}
    preco = p.get("preco")
    if tipo == "gasolina":
        return gasolina_c(float(p.get("teor_etanol", 30.0)), preco)
    if tipo == "etanol":
        return etanol_hidratado(float(p.get("teor_etanol_hidratado", 93.5)), preco)
    if tipo == "diesel":
        return diesel_b(float(p.get("teor_biodiesel", 15.0)), preco)
    if tipo == "gnv":
        return gnv(preco)
    if tipo == "eletricidade":
        return eletricidade(
            float(p.get("fator_emissao", 40.0)), preco, float(p.get("fracao_renovavel", FRACAO_RENOVAVEL_REDE))
        )
    raise ValueError(f"Tipo de combustível desconhecido: {tipo}")
