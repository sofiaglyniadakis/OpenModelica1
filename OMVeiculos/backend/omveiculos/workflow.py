"""Interpretação do workflow (grafo de blocos) e execução das simulações.

O grafo segue o fluxo "montar o veículo -> ensaiar -> analisar":

    Combustível --> Motor a combustão --\
                                          >--> Transmissão --> Veículo --> Ensaio --> Painel
    Bateria ----> Motor elétrico -------/

Cada caminho completo até um ensaio gera um *cenário*. Um motor flex ligado a
dois combustíveis gera dois cenários (um por combustível); um veículo ligado a
dois ensaios é simulado nos dois.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

import time
from dataclasses import dataclass, field, fields

from . import analise, ciclos, combustiveis
from .catalogo import BLOCOS_POR_TIPO
from .erros import ErroOMVeiculos, ErroWorkflow
from .componentes import (
    Ambiente,
    Bateria,
    Hibrido,
    MotorCombustao,
    MotorEletrico,
    Transmissao,
    Veiculo,
    raio_pneu,
)
from .simulador import ResultadoCiclo, ResultadoDesempenho, TremDeForca, simular_ciclo, simular_desempenho

ENSAIOS = ("ensaio_pbev", "ciclo", "desempenho")
COMBUSTIVEIS_ACEITOS = {
    "flex": ("gasolina", "etanol", "gnv"),
    "gasolina": ("gasolina", "gnv"),
    "diesel": ("diesel",),
}


@dataclass
class No:
    id: str
    tipo: str
    rotulo: str
    params: dict

    def p(self, chave: str):
        """Parâmetro já convertido para as unidades internas (aplica a escala do catálogo)."""
        bloco = BLOCOS_POR_TIPO[self.tipo]
        for spec in bloco["parametros"]:
            if spec["chave"] == chave:
                valor = self.params.get(chave, spec["padrao"])
                if spec["tipo"] == "numero":
                    try:
                        valor = float(valor)
                    except (TypeError, ValueError):
                        raise ErroWorkflow(f"{self.rotulo}: '{spec['rotulo']}' deve ser um número.") from None
                    return valor * spec.get("escala", 1.0)
                return valor
        raise KeyError(chave)


@dataclass
class Cenario:
    id: str
    nome: str
    ensaio: No
    veiculo: No
    combustivel: No | None
    trem: TremDeForca
    eletricidade: combustiveis.Combustivel


@dataclass
class Diagnostico:
    erros: list[dict] = field(default_factory=list)
    avisos: list[dict] = field(default_factory=list)

    def erro(self, no: No | str | None, msg: str) -> None:
        self.erros.append({"no": no.id if isinstance(no, No) else no, "mensagem": msg})

    def aviso(self, no: No | str | None, msg: str) -> None:
        self.avisos.append({"no": no.id if isinstance(no, No) else no, "mensagem": msg})


# --- conversão parâmetros -> componentes ---------------------------------------


def _preencher(cls, no: No, extra: dict | None = None):
    valores = {}
    chaves = {s["chave"] for s in BLOCOS_POR_TIPO[no.tipo]["parametros"]}
    for f in fields(cls):
        if f.name in chaves:
            valores[f.name] = no.p(f.name)
    valores.update(extra or {})
    if "nome" in {f.name for f in fields(cls)}:
        valores["nome"] = no.rotulo
    return cls(**valores)


def _lista_numeros(texto) -> list[float]:
    if isinstance(texto, (list, tuple)):
        return [float(x) for x in texto]
    itens = [t.strip().replace(",", ".") for t in str(texto).replace("\n", ";").split(";")]
    return [float(t) for t in itens if t]


def converter_veiculo(no: No) -> Veiculo:
    try:
        raio = raio_pneu(str(no.p("pneu")))
    except ValueError as e:
        raise ErroWorkflow(f"{no.rotulo}: {e}") from None
    return _preencher(Veiculo, no, {"raio": raio, "ar_condicionado": bool(no.p("ar_condicionado"))})


def converter_transmissao(no: No) -> Transmissao:
    tipo = no.p("tipo")
    try:
        relacoes = _lista_numeros(no.p("relacoes")) if tipo != "cvt" else [1.0]
    except ValueError:
        raise ErroWorkflow(f"{no.rotulo}: relações inválidas. Use números separados por ';'.") from None
    if not relacoes or any(r <= 0 for r in relacoes):
        raise ErroWorkflow(f"{no.rotulo}: informe ao menos uma relação positiva.")
    if len(relacoes) > 10:
        raise ErroWorkflow(f"{no.rotulo}: no máximo 10 marchas.")
    return _preencher(Transmissao, no, {"relacoes": relacoes})


def converter_motor(no: No) -> MotorCombustao:
    m = _preencher(MotorCombustao, no, {
        "start_stop": bool(no.p("start_stop")),
        "corte_combustivel": bool(no.p("corte_combustivel")),
    })
    if m.tipo != "flex":
        m.potencia_e, m.torque_e = m.potencia_g, m.torque_g
    if not (m.rpm_lenta < m.rpm_potencia <= m.rpm_max):
        raise ErroWorkflow(f"{no.rotulo}: as rotações devem obedecer marcha lenta < potência máx. <= rotação máx.")
    return m


def converter_bateria(no: No) -> tuple[Bateria, Hibrido, combustiveis.Combustivel]:
    bat = _preencher(Bateria, no)
    if not (0 <= bat.soc_min < bat.soc_max <= 100):
        raise ErroWorkflow(f"{no.rotulo}: SOC mínimo deve ser menor que o máximo.")
    hib = _preencher(Hibrido, no)
    ele = combustiveis.eletricidade(no.p("fator_emissao"), no.p("preco_kwh"), no.p("fracao_renovavel"))
    return bat, hib, ele


def converter_combustivel(no: No) -> combustiveis.Combustivel:
    p = {k: no.p(k) for k in ("teor_etanol", "teor_etanol_hidratado", "teor_biodiesel", "preco")}
    return combustiveis.criar(no.p("tipo"), p)


def ambiente_do_ensaio(no: No) -> Ambiente:
    inclinacao = no.p("inclinacao") if no.tipo == "ciclo" else 0.0
    return Ambiente(temperatura=no.p("temperatura"), altitude=no.p("altitude"), inclinacao=inclinacao)


# --- grafo ---------------------------------------------------------------------


class Grafo:
    def __init__(self, workflow: dict):
        self.nos: dict[str, No] = {}
        for n in workflow.get("nos", []):
            tipo = n.get("tipo")
            if tipo not in BLOCOS_POR_TIPO:
                raise ErroWorkflow(f"Tipo de bloco desconhecido: {tipo}")
            self.nos[n["id"]] = No(n["id"], tipo, n.get("rotulo") or BLOCOS_POR_TIPO[tipo]["nome"], n.get("params", {}))
        self.arestas = [a for a in workflow.get("arestas", []) if a.get("origem") in self.nos and a.get("destino") in self.nos]

    def entradas(self, no: No, porta: str) -> list[No]:
        return [self.nos[a["origem"]] for a in self.arestas if a["destino"] == no.id and a.get("entrada") == porta]

    def saidas(self, no: No) -> list[No]:
        return [self.nos[a["destino"]] for a in self.arestas if a["origem"] == no.id]

    def do_tipo(self, *tipos: str) -> list[No]:
        return [n for n in self.nos.values() if n.tipo in tipos]


def montar_cenarios(grafo: Grafo, diag: Diagnostico) -> list[Cenario]:
    cenarios: list[Cenario] = []
    vistos: set[str] = set()
    for ensaio in grafo.do_tipo(*ENSAIOS):
        veiculos = grafo.entradas(ensaio, "veiculo")
        if not veiculos:
            diag.aviso(ensaio, f"'{ensaio.rotulo}' não tem nenhum veículo conectado.")
            continue
        for vno in veiculos:
            try:
                for c in _cenarios_do_veiculo(grafo, ensaio, vno, diag):
                    if c.id not in vistos:
                        vistos.add(c.id)
                        cenarios.append(c)
            except ErroWorkflow as e:
                diag.erro(vno, str(e))
    return cenarios


def _cenarios_do_veiculo(grafo: Grafo, ensaio: No, vno: No, diag: Diagnostico) -> list[Cenario]:
    trens = grafo.entradas(vno, "trem")
    if len(trens) != 1:
        raise ErroWorkflow(f"'{vno.rotulo}' precisa de exatamente uma transmissão conectada.")
    tno = trens[0]
    motores = grafo.entradas(tno, "potencia")
    ices = [m for m in motores if m.tipo == "motor_combustao"]
    els = [m for m in motores if m.tipo == "motor_eletrico"]
    if not motores:
        raise ErroWorkflow(f"'{tno.rotulo}' não tem motor conectado.")
    if len(ices) > 1 or len(els) > 1:
        raise ErroWorkflow(f"'{tno.rotulo}' aceita no máximo um motor a combustão e um elétrico.")

    veiculo = converter_veiculo(vno)
    transmissao = converter_transmissao(tno)
    eletrico = bateria = hibrido = None
    eletricidade = combustiveis.eletricidade()
    if els:
        eno = els[0]
        bats = grafo.entradas(eno, "energia")
        if len(bats) != 1:
            raise ErroWorkflow(f"'{eno.rotulo}' precisa de uma bateria conectada.")
        eletrico = _preencher(MotorEletrico, eno)
        bateria, hibrido, eletricidade = converter_bateria(bats[0])

    if not ices:
        if transmissao.tipo != "redutor":
            diag.aviso(tno, f"'{tno.rotulo}': no elétrico é usada apenas a primeira relação (redutor).")
        pt = TremDeForca("eletrico", veiculo, transmissao, eletrico=eletrico, bateria=bateria)
        cid = f"{ensaio.id}|{vno.id}|eletrico"
        return [Cenario(cid, f"{vno.rotulo} · Elétrico", ensaio, vno, None, pt, eletricidade)]

    mno = ices[0]
    motor = converter_motor(mno)
    fontes = grafo.entradas(mno, "combustivel")
    if not fontes:
        raise ErroWorkflow(f"'{mno.rotulo}' precisa de pelo menos um combustível conectado.")
    arq = "hibrido" if els else "combustao"
    if arq == "combustao" and transmissao.tipo == "redutor":
        raise ErroWorkflow(f"'{tno.rotulo}': redutor fixo serve apenas para veículos elétricos.")
    saida = []
    for cno in fontes:
        comb = converter_combustivel(cno)
        if comb.tipo not in COMBUSTIVEIS_ACEITOS[motor.tipo]:
            diag.erro(cno, f"'{cno.rotulo}' não é compatível com o motor '{mno.rotulo}' ({motor.tipo}).")
            continue
        pt = TremDeForca(arq, veiculo, transmissao, motor=motor, combustivel=comb,
                         eletrico=eletrico, bateria=bateria, hibrido=hibrido)
        cid = f"{ensaio.id}|{vno.id}|{cno.id}"
        rotulo_comb = cno.rotulo if cno.rotulo != BLOCOS_POR_TIPO["combustivel"]["nome"] else comb.nome
        saida.append(Cenario(cid, f"{vno.rotulo} · {rotulo_comb}", ensaio, vno, cno, pt, eletricidade))
    return saida


# --- execução --------------------------------------------------------------------


def ciclos_do_ensaio(ensaio: No) -> list[tuple[str, ciclos.Ciclo]]:
    if ensaio.tipo == "ensaio_pbev":
        return [("urbano", ciclos.obter("ftp75")), ("estrada", ciclos.obter("hwfet"))]
    if ensaio.tipo == "ciclo":
        cid = ensaio.p("ciclo")
        try:
            return [("ciclo", ciclos.obter(cid, ensaio.params))]
        except ValueError as e:
            raise ErroWorkflow(f"{ensaio.rotulo}: {e}") from None
    return []


class MotorRapido:
    nome = "rapido"

    def ciclos(self, pedidos: list[tuple[Cenario, str, ciclos.Ciclo, Ambiente]]) -> list[ResultadoCiclo]:
        return [simular_ciclo(c.trem, ciclo, amb) for c, _, ciclo, amb in pedidos]

    def desempenhos(self, pedidos: list[tuple[Cenario, Ambiente, float]]) -> list[ResultadoDesempenho]:
        return [simular_desempenho(c.trem, amb, mu) for c, amb, mu in pedidos]


@dataclass
class Plano:
    grafo: Grafo | None
    diag: Diagnostico
    itens: list = field(default_factory=list)  # (cenario, 'ciclo'|'desempenho', referência)
    pedidos_ciclo: list = field(default_factory=list)  # (cenario, nome, ciclo, ambiente)
    pedidos_des: list = field(default_factory=list)  # (cenario, ambiente, mu)


def planejar(workflow: dict) -> Plano:
    """Valida o workflow e lista as simulações necessárias."""
    diag = Diagnostico()
    try:
        grafo = Grafo(workflow)
    except ErroWorkflow as e:
        diag.erro(None, str(e))
        return Plano(None, diag)
    plano = Plano(grafo, diag)
    if not grafo.do_tipo(*ENSAIOS):
        diag.erro(None, "Adicione um ensaio (Ensaio PBEV, Ciclo de condução ou Desempenho) ligado a um veículo.")
    for c in montar_cenarios(grafo, diag):
        try:
            if c.ensaio.tipo == "desempenho":
                amb = Ambiente(temperatura=c.ensaio.p("temperatura"), altitude=c.ensaio.p("altitude"))
                plano.itens.append((c, "desempenho", len(plano.pedidos_des)))
                plano.pedidos_des.append((c, amb, c.ensaio.p("mu")))
            else:
                amb = ambiente_do_ensaio(c.ensaio)
                idx = []
                for nome, ciclo in ciclos_do_ensaio(c.ensaio):
                    idx.append((nome, len(plano.pedidos_ciclo)))
                    plano.pedidos_ciclo.append((c, nome, ciclo, amb))
                plano.itens.append((c, "ciclo", idx))
        except ErroWorkflow as e:
            diag.erro(c.ensaio, str(e))
    return plano


def executar(workflow: dict, motor=None) -> dict:
    """Valida o workflow, simula todos os cenários e calcula os indicadores."""
    inicio = time.perf_counter()
    motor = motor or MotorRapido()
    plano = planejar(workflow)
    diag, grafo = plano.diag, plano.grafo
    if grafo is None:
        return _resposta(motor, inicio, diag, [], [])
    try:
        res_ciclos = motor.ciclos(plano.pedidos_ciclo) if plano.pedidos_ciclo else []
        res_des = motor.desempenhos(plano.pedidos_des) if plano.pedidos_des else []
    except ErroOMVeiculos as e:  # erros do motor de cálculo (ex.: falha no omc)
        diag.erro(None, str(e))
        return _resposta(motor, inicio, diag, [], [])

    saida_cenarios = []
    for c, tipo, ref in plano.itens:
        base = {
            "id": c.id,
            "nome": c.nome,
            "ensaio_id": c.ensaio.id,
            "ensaio_tipo": c.ensaio.tipo,
            "ensaio_nome": c.ensaio.rotulo,
            "veiculo_id": c.veiculo.id,
            "veiculo_nome": c.veiculo.rotulo,
            "combustivel_id": c.combustivel.id if c.combustivel else None,
            "energetico": c.trem.combustivel.tipo if c.trem.combustivel else "eletricidade",
            "arquitetura": c.trem.arquitetura,
            "preco": c.trem.combustivel.preco if c.trem.combustivel else c.eletricidade.preco,
        }
        if tipo == "desempenho":
            r = res_des[ref]
            base["indicadores"] = analise.indicadores_desempenho(r, c.trem)
            base["series"] = {"desempenho": {"t": [round(x, 2) for x in r.t.tolist()], "v_kmh": [round(x, 2) for x in r.v_kmh.tolist()]}}
        else:
            por_ciclo = {nome: analise.indicadores_ciclo(res_ciclos[i], c.trem, c.eletricidade) for nome, i in ref}
            series = {nome: analise.series(res_ciclos[i], c.trem) for nome, i in ref}
            for nome, i in ref:
                if res_ciclos[i].tempo_excedido_s > 1.0:
                    diag.aviso(c.veiculo, f"{c.nome}: o trem de força não acompanha o ciclo {res_ciclos[i].ciclo_nome} "
                                          f"durante {res_ciclos[i].tempo_excedido_s:.0f} s.")
            if c.ensaio.tipo == "ensaio_pbev":
                base["indicadores"] = analise.indicadores_pbev(por_ciclo["urbano"], por_ciclo["estrada"], c.trem)
            else:
                base["indicadores"] = {"ciclo": por_ciclo["ciclo"]}
            base["series"] = series
        saida_cenarios.append(base)

    paineis = _paineis(grafo, saida_cenarios, diag)
    return _resposta(motor, inicio, diag, saida_cenarios, paineis)


def _principal(cen: dict) -> dict | None:
    ind = cen.get("indicadores", {})
    if cen["ensaio_tipo"] == "ensaio_pbev":
        return ind.get("combinado")
    if cen["ensaio_tipo"] == "ciclo":
        return ind.get("ciclo")
    return None


def _paineis(grafo: Grafo, cenarios: list[dict], diag: Diagnostico) -> list[dict]:
    paineis = []
    nos_painel = grafo.do_tipo("painel", "exergia")
    if not grafo.do_tipo("painel") and cenarios:
        nos_painel = [No("__todos__", "painel", "Todos os resultados", {})] + nos_painel
    for p in nos_painel:
        if p.id == "__todos__":
            ensaios = {c["ensaio_id"] for c in cenarios}
        else:
            ensaios = {n.id for n in grafo.entradas(p, "resultado")}
            if not ensaios:
                diag.aviso(p, f"'{p.rotulo}' não recebe nenhum resultado.")
        selec = [c for c in cenarios if c["ensaio_id"] in ensaios]
        if p.tipo == "exergia":
            params = {k: p.p(k) for k in ("t0_c", "t_escape_c", "t_arrefecimento_c", "fracao_escape")}
            exergia = {}
            for c in selec:
                r = analise.exergia_cenario(c["indicadores"], c["ensaio_tipo"], params)
                if r is not None:
                    exergia[c["id"]] = r
            paineis.append({
                "id": p.id,
                "nome": p.rotulo,
                "tipo": "exergia",
                "km_mes": 0,
                "cenarios": list(exergia),
                "paridades": [],
                "exergia": exergia,
                "parametros": params,
            })
            continue
        km_mes = p.p("km_mes")
        paineis.append({
            "id": p.id,
            "nome": p.rotulo,
            "km_mes": km_mes,
            "cenarios": [c["id"] for c in selec],
            "paridades": _paridades(selec, km_mes),
            "tipo": "painel",
        })
    return paineis


def _paridades(cenarios: list[dict], km_mes: float) -> list[dict]:
    """Compara gasolina × etanol do mesmo veículo no mesmo ensaio."""
    saida = []
    grupos: dict[tuple, dict] = {}
    for c in cenarios:
        if c["arquitetura"] == "eletrico" or _principal(c) is None:
            continue
        grupos.setdefault((c["ensaio_id"], c["veiculo_id"]), {}).setdefault(c["energetico"], c)
    for (_, _), g in grupos.items():
        if "gasolina" in g and "etanol" in g:
            cg, ce = g["gasolina"], g["etanol"]
            pg, pe = _principal(cg), _principal(ce)
            if not pg.get("km_por_unidade") or not pe.get("km_por_unidade"):
                continue
            par = analise.paridade_etanol(pg, pe, cg["preco"], ce["preco"], km_mes)
            par.update(veiculo=cg["veiculo_nome"], ensaio=cg["ensaio_nome"], cenario_gasolina=cg["id"], cenario_etanol=ce["id"])
            saida.append(par)
    return saida


def _resposta(motor, inicio, diag, cenarios, paineis) -> dict:
    return {
        "motor": motor.nome,
        "tempo_s": round(time.perf_counter() - inicio, 3),
        "erros": diag.erros,
        "avisos": diag.avisos,
        "cenarios": cenarios,
        "paineis": paineis,
    }
