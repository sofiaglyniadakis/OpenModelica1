"""Integração com o OpenModelica.

* :func:`gerar_pacote` transforma os cenários do workflow em um pacote Modelica
  (um modelo por cenário/ciclo) que estende os experimentos da biblioteca
  ``VeiculosLevesBR``.
* :class:`MotorOpenModelica` compila e simula esses modelos com o ``omc`` e
  converte os resultados CSV para as mesmas estruturas do motor rápido, de modo
  que toda a análise (PBEV, custos, CO2) é compartilhada.

Localização do compilador: variável ``OMVEICULOS_OMC``, ``$OPENMODELICAHOME/bin/omc``
ou ``omc`` no PATH. O compilador C usado para gerar o simulador pode ser
definido em ``OMVEICULOS_CC``; instalações do conda-forge são detectadas
automaticamente.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

import csv
import glob
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import ciclos as mod_ciclos
from .componentes import CV, KGFM, Ambiente
from .erros import ErroOpenModelica
from .simulador import ResultadoCiclo, ResultadoDesempenho

BIBLIOTECA = Path(__file__).resolve().parents[2] / "modelica" / "VeiculosLevesBR"
PACOTE = "OMVeiculosCenarios"
TIPO_TRANSMISSAO = {"manual": 1, "automatica": 2, "cvt": 3, "redutor": 4}
EXPERIMENTO = {"combustao": "CicloCombustao", "eletrico": "CicloEletrico", "hibrido": "CicloHibrido"}
ARQUITETURA = {"combustao": 1, "eletrico": 2, "hibrido": 3}
VARS_CICLO = ("distancia", "massaCombustivel", "energiaBateria", "soc", "marcha", "rpm", "pIce", "pEm",
              "pRoda", "eAero", "eRol", "eRampa", "eFreio", "energiaMecanica", "tempoExcedido")
VARS_DESEMPENHO = ("vKmh", "t80", "t100", "t120", "vMaxKmh")
TEMPO_DESEMPENHO = 90.0


# --- geração de código -------------------------------------------------------------


def _v(x) -> str:
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, (list, tuple, np.ndarray)):
        return "{" + ", ".join(_v(float(e)) for e in x) + "}"
    return f"{float(x):.10g}"


def _mod(nome: str, campos: dict, largura: int = 96) -> str:
    """Modificador de registro, quebrado em linhas de até ``largura`` caracteres."""
    itens = [f"{k} = {_v(v)}" for k, v in campos.items()]
    linhas, atual = [], ""
    for item in itens:
        if atual and len(atual) + len(item) + 2 > largura:
            linhas.append(atual + ",")
            atual = item
        else:
            atual = f"{atual}, {item}" if atual else item
    linhas.append(atual)
    recuo = "\n" + " " * 8
    return f"{nome}({recuo.join(linhas)})"


def _veiculo(pt) -> dict:
    v = pt.veiculo
    return {
        "massa": v.massa, "carga": v.carga, "fatorInercia": v.fator_inercia,
        "modoResistencia": 2 if v.modo_resistencia == "coastdown" else 1,
        "Cd": v.cd, "areaFrontal": v.area_frontal, "Cr": v.cr, "F0": v.f0, "F1": v.f1, "F2": v.f2,
        "raio": v.raio, "fracaoEixoMotriz": v.fracao_eixo_motriz, "potenciaAcessorios": v.p_acessorios,
    }


def _transmissao(pt) -> dict:
    t = pt.transmissao
    rel = list(t.relacoes)[:10]
    return {
        "tipo": TIPO_TRANSMISSAO[t.tipo], "nMarchas": len(rel), "relacoes": rel + [0.0] * (10 - len(rel)),
        "diferencial": t.diferencial, "eficiencia": t.eficiencia, "cvtMin": t.cvt_min, "cvtMax": t.cvt_max,
        "rpmTrocaMin": t.rpm_troca_min, "rpmTrocaMax": t.rpm_troca_max, "rpmPartida": t.rpm_partida,
    }


def _motor(pt) -> dict:
    m = pt.motor
    return {
        "cilindrada": m.cilindrada, "potenciaG": m.potencia_g * CV, "potenciaE": m.potencia_e * CV,
        "torqueG": m.torque_g * KGFM, "torqueE": m.torque_e * KGFM, "rpmLenta": m.rpm_lenta,
        "rpmTorqueIni": m.rpm_torque_ini, "rpmTorqueFim": m.rpm_torque_fim, "rpmPotencia": m.rpm_potencia,
        "rpmMax": m.rpm_max, "eficienciaIndicada": m.eficiencia_indicada, "fmep0": m.fmep0, "fmep1": m.fmep1,
        "fmep2": m.fmep2, "pmep0": m.pmep0, "ganhoEtanol": m.ganho_etanol, "startStop": m.start_stop,
        "corteCombustivel": m.corte_combustivel, "rpmCorte": m.rpm_corte, "inercia": m.inercia,
    }


def _combustivel(pt) -> dict:
    c, m = pt.combustivel, pt.motor
    return {
        "densidade": c.densidade, "pci": c.pci, "fracaoEtanolVol": c.fracao_etanol_vol,
        "classificacaoEtanol": c.tipo == "etanol" and m.tipo == "flex",
        "fatorPotencia": m.fator_gnv if c.tipo == "gnv" else 1.0,
    }


def _eletrico(pt) -> dict:
    e = pt.eletrico
    return {
        "potenciaMax": e.p_max, "torqueMax": e.t_max, "rpmMax": e.rpm_max, "eficiencia": e.eficiencia,
        "fracaoRegeneracao": e.fracao_regeneracao, "vMinRegeneracao": e.v_min_regeneracao, "inercia": e.inercia,
    }


def _bateria(pt) -> dict:
    b = pt.bateria
    return {
        "capacidade": b.capacidade, "socInicial": b.soc_inicial, "socMin": b.soc_min, "socMax": b.soc_max,
        "eficiencia": b.eficiencia, "eficienciaCarregador": b.eficiencia_carregador,
    }


def _hibrido(pt) -> dict:
    h = pt.hibrido
    return {"vMaxEletrico": h.v_max_eletrico, "pMaxEletrico": h.p_max_eletrico, "socAlvo": h.soc_alvo,
            "pCargaMax": h.p_carga_max}


def _ambiente(amb: Ambiente) -> dict:
    return {"temperatura": amb.temperatura, "altitude": amb.altitude, "inclinacao": amb.inclinacao}


def _comentario(texto: str) -> str:
    return texto.replace('"', "'")


@dataclass
class ModeloGerado:
    nome: str
    descricao: str
    codigo: str
    stop_time: float
    intervalo: float
    filtro: tuple[str, ...]


def modelo_ciclo(nome: str, cenario, ciclo: mod_ciclos.Ciclo, amb: Ambiente) -> ModeloGerado:
    pt = cenario.trem
    mods = [f"ciclo = {mod_ciclos.CODIGOS[ciclo.id]}"]
    if ciclo.id == "constante":
        mods += [f"vConstante = {_v(ciclo.v_kmh[0])}", f"duracaoConstante = {_v(ciclo.duracao)}"]
    if ciclo.id == "personalizado":
        mods.append(f"vPersonalizado = {_v(np.round(ciclo.v_kmh, 4))}")
    mods += [_mod("veiculo", _veiculo(pt)), _mod("transmissao", _transmissao(pt)), _mod("ambiente", _ambiente(amb))]
    if pt.arquitetura in ("combustao", "hibrido"):
        mods += [_mod("motor", _motor(pt)), _mod("combustivel", _combustivel(pt))]
    if pt.arquitetura in ("eletrico", "hibrido"):
        mods += [_mod("eletrico", _eletrico(pt)), _mod("bateria", _bateria(pt))]
    if pt.arquitetura == "hibrido":
        mods.append(_mod("hibrido", _hibrido(pt)))
    desc = f"{cenario.nome} · {ciclo.nome}"
    corpo = ",\n      ".join(mods)
    codigo = (
        f'  model {nome} "{_comentario(desc)}"\n'
        f"    extends VeiculosLevesBR.Experimentos.{EXPERIMENTO[pt.arquitetura]}(\n      {corpo});\n"
        f"    annotation(experiment(StopTime = {_v(ciclo.duracao)}, Interval = 0.5));\n"
        f"  end {nome};\n"
    )
    return ModeloGerado(nome, desc, codigo, ciclo.duracao, 0.5, VARS_CICLO)


def modelo_desempenho(nome: str, cenario, amb: Ambiente, mu: float) -> ModeloGerado:
    pt = cenario.trem
    mods = [f"arquitetura = {ARQUITETURA[pt.arquitetura]}", f"mu = {_v(mu)}",
            _mod("veiculo", _veiculo(pt)), _mod("transmissao", _transmissao(pt)), _mod("ambiente", _ambiente(amb))]
    if pt.arquitetura != "eletrico":
        mods += [_mod("motor", _motor(pt)), _mod("combustivel", _combustivel(pt))]
    if pt.arquitetura != "combustao":
        mods.append(_mod("eletrico", _eletrico(pt)))
    desc = f"{cenario.nome} · Desempenho"
    corpo = ",\n      ".join(mods)
    codigo = (
        f'  model {nome} "{_comentario(desc)}"\n'
        f"    extends VeiculosLevesBR.Experimentos.Desempenho(\n      {corpo});\n"
        f"    annotation(experiment(StopTime = {_v(TEMPO_DESEMPENHO)}, Interval = 0.1));\n"
        f"  end {nome};\n"
    )
    return ModeloGerado(nome, desc, codigo, TEMPO_DESEMPENHO, 0.1, VARS_DESEMPENHO)


def pacote(modelos: list[ModeloGerado]) -> str:
    corpo = "\n".join(m.codigo for m in modelos)
    return (
        f'package {PACOTE} "Cenários gerados pelo OM Veículos Leves"\n'
        f"{corpo}\n"
        f'  annotation(uses(VeiculosLevesBR(version = "0.1.0")));\n'
        f"end {PACOTE};\n"
    )


def _nomes_modelos(pedidos_ciclo, pedidos_des) -> tuple[list[ModeloGerado], list[ModeloGerado]]:
    mc = [modelo_ciclo(f"Cenario{i + 1}_{nome}", c, ciclo, amb) for i, (c, nome, ciclo, amb) in enumerate(pedidos_ciclo)]
    md = [modelo_desempenho(f"Desempenho{i + 1}", c, amb, mu) for i, (c, amb, mu) in enumerate(pedidos_des)]
    return mc, md


# --- execução ---------------------------------------------------------------------


def localizar_omc() -> str | None:
    candidatos = [os.environ.get("OMVEICULOS_OMC")]
    if os.environ.get("OPENMODELICAHOME"):
        candidatos.append(str(Path(os.environ["OPENMODELICAHOME"]) / "bin" / "omc"))
    candidatos.append(shutil.which("omc"))
    for c in candidatos:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    return None


@lru_cache(maxsize=8)
def versao_omc(caminho: str) -> str | None:
    try:
        out = subprocess.run([caminho, "--version"], capture_output=True, text=True, timeout=30)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def status() -> dict:
    caminho = localizar_omc()
    return {"disponivel": caminho is not None, "caminho": caminho, "versao": versao_omc(caminho) if caminho else None}


def _compiladores(omc: str) -> tuple[str | None, str | None]:
    cc = os.environ.get("OMVEICULOS_CC")
    cxx = os.environ.get("OMVEICULOS_CXX")
    if cc:
        return cc, cxx
    pasta = Path(omc).parent
    achados = sorted(glob.glob(str(pasta / "*-conda-*-cc")))
    if achados:
        cc = achados[0]
        cxx_cand = Path(cc[: -len("-cc")] + "-c++")
        return cc, str(cxx_cand) if cxx_cand.exists() else None
    return None, None


def _ler_csv(caminho: Path) -> dict[str, np.ndarray]:
    with open(caminho, newline="") as f:
        leitor = csv.reader(f)
        cabecalho = [c.strip().strip('"') for c in next(leitor)]
        dados = np.array([[float(x) for x in linha] for linha in leitor if linha])
    return {nome: dados[:, i] for i, nome in enumerate(cabecalho)}


def _amostrar(dados: dict[str, np.ndarray], tempos: np.ndarray, var: str) -> np.ndarray:
    """Valor de ``var`` em cada instante (última linha com aquele tempo, após eventos)."""
    t = dados["time"]
    idx = np.searchsorted(t, tempos + 1e-9, side="right") - 1
    idx = np.clip(idx, 0, len(t) - 1)
    return dados[var][idx]


def resultado_ciclo(dados: dict[str, np.ndarray], ciclo: mod_ciclos.Ciclo) -> ResultadoCiclo:
    n = len(ciclo.v_kmh)
    t = np.arange(n, dtype=float)
    meio = np.minimum(t + 0.5, t[-1])
    fim = {v: float(dados[v][-1]) for v in ("eAero", "eRol", "eRampa", "eFreio", "energiaMecanica", "tempoExcedido")}
    inst = {v: _amostrar(dados, meio, v) for v in ("marcha", "rpm", "pIce", "pEm", "pRoda")}
    return ResultadoCiclo(
        ciclo_id=ciclo.id,
        ciclo_nome=ciclo.nome,
        fases=ciclo.fases,
        t=t,
        v_kmh=ciclo.v_kmh,
        distancia_m=_amostrar(dados, t, "distancia"),
        combustivel_kg=_amostrar(dados, t, "massaCombustivel"),
        energia_bat_j=_amostrar(dados, t, "energiaBateria"),
        soc=_amostrar(dados, t, "soc"),
        marcha=np.round(inst["marcha"]),
        rpm=inst["rpm"],
        p_motor_kw=inst["pIce"] / 1000.0,
        p_eletrico_kw=inst["pEm"] / 1000.0,
        p_roda_kw=inst["pRoda"] / 1000.0,
        energia_motor_mec_j=fim["energiaMecanica"],
        energias={"aerodinamica": fim["eAero"], "rolamento": fim["eRol"], "rampa": fim["eRampa"], "frenagem": fim["eFreio"]},
        tempo_excedido_s=fim["tempoExcedido"],
    )


def resultado_desempenho(dados: dict[str, np.ndarray]) -> ResultadoDesempenho:
    def marco(v: str) -> float | None:
        x = float(dados[v][-1])
        return x if x >= 0 else None

    t80, t100, t120 = marco("t80"), marco("t100"), marco("t120")
    t = dados["time"]
    # remove instantes duplicados (eventos)
    _, idx = np.unique(t[::-1], return_index=True)
    idx = len(t) - 1 - idx
    corte = t[idx] <= (t120 + 2.0 if t120 else TEMPO_DESEMPENHO)
    return ResultadoDesempenho(
        t_0_100=t100,
        t_80_120=(t120 - t80) if (t120 is not None and t80 is not None) else None,
        v_max_kmh=float(dados["vMaxKmh"][-1]),
        t=t[idx][corte],
        v_kmh=dados["vKmh"][idx][corte],
    )


class MotorOpenModelica:
    nome = "openmodelica"

    def __init__(self, omc: str | None = None, timeout: float = 600.0, manter_arquivos: bool = False):
        self.omc = omc or localizar_omc()
        if not self.omc:
            raise ErroOpenModelica(
                "OpenModelica (omc) não encontrado. Instale o OpenModelica ou defina OMVEICULOS_OMC "
                "com o caminho do executável."
            )
        self.timeout = timeout
        self.manter_arquivos = manter_arquivos
        self.ultimo_log = ""

    def _simular(self, modelos: list[ModeloGerado]) -> dict[str, dict[str, np.ndarray]]:
        if not modelos:
            return {}
        pasta = Path(tempfile.mkdtemp(prefix="omveiculos-"))
        try:
            (pasta / f"{PACOTE}.mo").write_text(pacote(modelos), encoding="utf-8")
            linhas = []
            cc, cxx = _compiladores(self.omc)
            if cc:
                linhas.append(f'setCompiler("{cc}");')
            if cxx:
                linhas.append(f'setCXXCompiler("{cxx}");')
            linhas += [
                f'loadFile("{(BIBLIOTECA / "package.mo").as_posix()}"); getErrorString();',
                f'loadFile("{PACOTE}.mo"); getErrorString();',
            ]
            for m in modelos:
                filtro = "time|" + "|".join(m.filtro)
                n = int(round(m.stop_time / m.intervalo))
                linhas.append(
                    f'simulate({PACOTE}.{m.nome}, stopTime={_v(m.stop_time)}, numberOfIntervals={n}, '
                    f'tolerance=1e-6, outputFormat="csv", variableFilter="{filtro}"); getErrorString();'
                )
            (pasta / "executar.mos").write_text("\n".join(linhas) + "\n", encoding="utf-8")
            try:
                env = dict(os.environ)
                env["PATH"] = str(Path(self.omc).parent) + os.pathsep + env.get("PATH", "")
                proc = subprocess.run([self.omc, "executar.mos"], cwd=pasta, capture_output=True, text=True,
                                      timeout=self.timeout, env=env)
            except subprocess.TimeoutExpired:
                raise ErroOpenModelica(f"O OpenModelica excedeu o tempo limite de {self.timeout:.0f} s.") from None
            self.ultimo_log = proc.stdout + proc.stderr
            saida = {}
            for m in modelos:
                arq = pasta / f"{PACOTE}.{m.nome}_res.csv"
                if not arq.exists():
                    raise ErroOpenModelica(f"A simulação de '{m.descricao}' falhou no OpenModelica:\n" + _resumo_erro(self.ultimo_log))
                saida[m.nome] = _ler_csv(arq)
            return saida
        finally:
            if not self.manter_arquivos:
                shutil.rmtree(pasta, ignore_errors=True)

    def ciclos(self, pedidos) -> list[ResultadoCiclo]:
        modelos, _ = _nomes_modelos(pedidos, [])
        dados = self._simular(modelos)
        return [resultado_ciclo(dados[m.nome], ciclo) for m, (_, _, ciclo, _) in zip(modelos, pedidos)]

    def desempenhos(self, pedidos) -> list[ResultadoDesempenho]:
        _, modelos = _nomes_modelos([], pedidos)
        dados = self._simular(modelos)
        return [resultado_desempenho(dados[m.nome]) for m in modelos]


def _resumo_erro(log: str, max_linhas: int = 12) -> str:
    """Primeiras linhas de erro distintas do log do omc."""
    vistas, saida = set(), []
    for linha in log.splitlines():
        linha = linha.strip().strip('"')
        if re.search(r"error|erro|failed|falh", linha, re.I) and linha not in vistas:
            vistas.add(linha)
            saida.append(linha[:300])
    return "\n".join((saida or log.splitlines())[:max_linhas])


def gerar_pacote(pedidos_ciclo, pedidos_des) -> dict:
    """Código Modelica de todos os cenários (para visualização/exportação)."""
    mc, md = _nomes_modelos(pedidos_ciclo, pedidos_des)
    todos = mc + md
    return {
        "pacote": PACOTE,
        "codigo": pacote(todos) if todos else "",
        "modelos": [{"nome": m.nome, "descricao": m.descricao} for m in todos],
        "script": _script_exemplo(todos),
    }


def _script_exemplo(modelos: list[ModeloGerado]) -> str:
    linhas = [
        "// Execute com:  omc simular.mos",
        'loadFile("VeiculosLevesBR/package.mo"); getErrorString();',
        f'loadFile("{PACOTE}.mo"); getErrorString();',
    ]
    for m in modelos:
        linhas.append(f'simulate({PACOTE}.{m.nome}, outputFormat="csv"); getErrorString();')
    return "\n".join(linhas) + "\n"


def arquivos_biblioteca() -> list[dict]:
    return [
        {"caminho": f"VeiculosLevesBR/{p.name}", "conteudo": p.read_text(encoding="utf-8")}
        for p in sorted(BIBLIOTECA.iterdir())
        if p.is_file()
    ]
