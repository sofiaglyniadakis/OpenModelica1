// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  ChartColumn,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  Download,
  Fuel,
  LoaderCircle,
  Maximize2,
  Minimize2,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { corSerie } from "../lib/cores";
import { NOME_ARQ, NOME_ENERGETICO, num, reais } from "../lib/formato";
import { resultadoDesatualizado, useEstado } from "../lib/store";
import type { Cenario, IndCiclo, IndCombinado, IndDesempenho, IndPBEV, Painel, Paridade, Serie } from "../lib/tipos";
import { BarraEmpilhada, BarrasCenarios, LinhasTempo, useTemaGrafico } from "./graficos";

type CenarioCor = Cenario & { cor: string };

const principal = (c: Cenario): IndCombinado | IndCiclo | null =>
  c.ensaio_tipo === "ensaio_pbev"
    ? (c.indicadores as IndPBEV).combinado
    : c.ensaio_tipo === "ciclo"
      ? (c.indicadores as { ciclo: IndCiclo }).ciclo
      : null;

/** Rótulos curtos para eixos: remove as partes do nome comuns a todos os cenários. */
function rotulosCurtos(cs: Cenario[], incluirEnsaio: boolean): Map<string, string> {
  const partes = cs.map((c) => [...c.nome.split(" · "), ...(incluirEnsaio ? [c.ensaio_nome] : [])]);
  const comuns = new Set(partes[0]?.filter((p) => partes.every((ps) => ps.includes(p))) ?? []);
  return new Map(
    cs.map((c, i) => {
      const resto = partes[i].filter((p) => !comuns.has(p));
      return [c.id, resto.length ? resto.join(" · ") : c.nome];
    }),
  );
}

function baixarCSV(nome: string, linhas: (string | number | null | undefined)[][]) {
  const fmt = (v: string | number | null | undefined) =>
    v === null || v === undefined ? "" : typeof v === "number" ? String(v).replace(".", ",") : `"${v.replace(/"/g, '""')}"`;
  const csv = "﻿" + linhas.map((l) => l.map(fmt).join(";")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = nome;
  a.click();
  URL.revokeObjectURL(a.href);
}

function HeroiParidade({ p, pg, pe }: { p: Paridade; pg: number; pe: number }) {
  const etanol = p.compensa === "etanol";
  const posPreco = Math.min(Math.max((p.relacao_preco - 0.5) / 0.4, 0), 1) * 100;
  const posLimite = Math.min(Math.max((p.relacao_consumo - 0.5) / 0.4, 0), 1) * 100;
  return (
    <div className="heroi-paridade">
      <div className="icone-grande" style={{ background: etanol ? "#16a34a" : "#ea580c" }}>
        <Fuel size={24} />
      </div>
      <div>
        <h3>
          {p.veiculo}: abasteça com {etanol ? "etanol" : "gasolina"}
        </h3>
        <p>
          Neste carro o etanol rende <b>{num(p.relacao_consumo * 100, 1)}%</b> da gasolina, então compensa enquanto custar até{" "}
          <b>{reais(p.preco_max_etanol)}/L</b> (gasolina a {reais(pg)}). Com os preços informados ({reais(pe)} ÷ {reais(pg)} ={" "}
          <b>{num(p.relacao_preco * 100, 1)}%</b>) a economia é de cerca de <b>{reais(p.economia_mensal, 0)}/mês</b>.
        </p>
        <div className="regua" aria-hidden>
          <i style={{ left: `${posLimite}%`, background: "var(--texto-2)" }} title="Limite deste carro" />
          <i style={{ left: `${posPreco}%`, background: etanol ? "#16a34a" : "#ea580c" }} title="Relação de preços atual" />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--texto-3)", marginTop: 6 }}>
          <span>50%</span>
          <span>limite deste carro: {num(p.relacao_consumo * 100, 1)}% · regra popular: 70%</span>
          <span>90%</span>
        </div>
      </div>
      <div className="heroi-numero">
        <b>{num(p.relacao_consumo * 100, 1)}%</b>
        <span>paridade etanol/gasolina</span>
      </div>
    </div>
  );
}

function CartaoCenario({ c, kmMes }: { c: CenarioCor; kmMes: number }) {
  const ind = principal(c)!;
  const un = ind.unidade;
  const pbev = c.ensaio_tipo === "ensaio_pbev" ? (c.indicadores as IndPBEV) : null;
  return (
    <div className="cartao">
      <div className="cartao-cabeca">
        <i className="marcador" style={{ background: c.cor }} />
        <b title={c.nome}>{c.nome}</b>
        <small>{NOME_ARQ[c.arquitetura]}</small>
      </div>
      <div className="metrica-principal">
        {num(ind.km_por_unidade, 1)}
        <small>km/{un}</small>
      </div>
      <div className="metrica-rotulo">
        {pbev ? "combinado 55% urbano + 45% estrada" : (ind as IndCiclo).ciclo_nome}
        {pbev?.uso_real_estimado && <> · uso real ≈ {num(pbev.uso_real_estimado.combinado_km_por_unidade, 1)}</>}
      </div>
      <div className="metricas">
        <div>
          <b>{reais(ind.custo_r_km !== null ? ind.custo_r_km * kmMes : null, 0)}</b>
          <span>por mês ({num(kmMes, 0)} km)</span>
        </div>
        <div>
          <b>{num(ind.mj_km, 2)} MJ/km</b>
          <span>consumo energético</span>
        </div>
        <div>
          <b>{num(ind.co2_fossil_g_km, 0)} g/km</b>
          <span>CO₂ fóssil (escapamento)</span>
        </div>
        <div>
          <b>{num(ind.co2_wtw_g_km, 0)} g/km</b>
          <span>CO₂e do poço à roda</span>
        </div>
        {"autonomia_km" in ind && ind.autonomia_km != null && (
          <div>
            <b>{num(ind.autonomia_km, 0)} km</b>
            <span>autonomia</span>
          </div>
        )}
        <div>
          <b>{reais(ind.custo_r_km, 2)}</b>
          <span>por km ({NOME_ENERGETICO[c.energetico]})</span>
        </div>
      </div>
    </div>
  );
}

function TabelaConsumo({ cs, kmMes }: { cs: CenarioCor[]; kmMes: number }) {
  const temPbev = cs.some((c) => c.ensaio_tipo === "ensaio_pbev");
  const linhas = cs.map((c) => {
    const p = c.ensaio_tipo === "ensaio_pbev" ? (c.indicadores as IndPBEV) : null;
    const ind = principal(c)!;
    return {
      c,
      urb: p?.urbano.km_por_unidade ?? null,
      est: p?.estrada.km_por_unidade ?? null,
      comb: ind.km_por_unidade,
      un: ind.unidade,
      por100: ind.unidade_por_100km,
      mj: ind.mj_km,
      fossil: ind.co2_fossil_g_km,
      wtw: ind.co2_wtw_g_km,
      rkm: ind.custo_r_km,
      mes: ind.custo_r_km !== null ? ind.custo_r_km * kmMes : null,
      aut: "autonomia_km" in ind ? ind.autonomia_km ?? null : null,
      real: p?.uso_real_estimado?.combinado_km_por_unidade ?? null,
    };
  });
  const exportar = () =>
    baixarCSV("resultados-consumo.csv", [
      ["Cenário", "Ensaio", "Arquitetura", "Unidade", "Urbano (km/un)", "Estrada (km/un)", "Combinado/ciclo (km/un)", "un/100 km", "MJ/km", "CO2 fóssil (g/km)", "CO2e poço-roda (g/km)", "R$/km", `R$/mês (${kmMes} km)`, "Autonomia (km)"],
      ...linhas.map((l) => [l.c.nome, l.c.ensaio_nome, NOME_ARQ[l.c.arquitetura], l.un, l.urb, l.est, l.comb, l.por100, l.mj, l.fossil, l.wtw, l.rkm, l.mes, l.aut]),
    ]);
  return (
    <div className="secao">
      <div className="secao-titulo">
        <h3>Tabela de resultados</h3>
        <span>valores de laboratório; “uso real” usa as fórmulas de ajuste da EPA (indicativo)</span>
        <div className="acoes">
          <button className="botao" onClick={exportar}>
            <Download size={15} /> CSV
          </button>
        </div>
      </div>
      <div className="tabela-wrap">
        <table className="tabela">
          <thead>
            <tr>
              <th>Cenário</th>
              {temPbev && <th>Urbano</th>}
              {temPbev && <th>Estrada</th>}
              <th>{temPbev ? "Combinado" : "Ciclo"}</th>
              {temPbev && <th>Uso real*</th>}
              <th>un/100 km</th>
              <th>MJ/km</th>
              <th>CO₂ fóssil</th>
              <th>CO₂e poço-roda</th>
              <th>R$/km</th>
              <th>R$/mês</th>
              <th>Autonomia</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.c.id}>
                <td>
                  <span className="nome">
                    <i className="marcador" style={{ background: l.c.cor }} />
                    {l.c.nome}
                  </span>
                </td>
                {temPbev && <td>{num(l.urb, 2)}</td>}
                {temPbev && <td>{num(l.est, 2)}</td>}
                <td>
                  <b>{num(l.comb, 2)}</b> km/{l.un}
                </td>
                {temPbev && <td>{num(l.real, 1)}</td>}
                <td>
                  {num(l.por100, 2)} {l.un}
                </td>
                <td>{num(l.mj, 3)}</td>
                <td>{num(l.fossil, 0)} g/km</td>
                <td>{num(l.wtw, 0)} g/km</td>
                <td>{reais(l.rkm, 3)}</td>
                <td>{reais(l.mes, 0)}</td>
                <td>{l.aut !== null ? `${num(l.aut, 0)} km` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SecaoDesempenho({ cs }: { cs: CenarioCor[] }) {
  const dados = useMemo(() => {
    const ts = new Map<number, Record<string, number>>();
    cs.forEach((c, i) => {
      const s = c.series.desempenho;
      s.t.forEach((t, k) => {
        if (t > 40) return;
        const chave = Math.round(t * 5) / 5;
        if (!ts.has(chave)) ts.set(chave, { t: chave });
        ts.get(chave)![`c${i}`] = s.v_kmh[k];
      });
    });
    return [...ts.values()].sort((a, b) => a.t - b.t);
  }, [cs]);
  return (
    <div className="secao">
      <div className="secao-titulo">
        <h3>Desempenho</h3>
        <span>aceleração plena com troca de marcha ideal</span>
      </div>
      <div className="grade-graficos" style={{ gridTemplateColumns: "minmax(300px, 1fr) minmax(300px, 1.3fr)" }}>
        <div className="tabela-wrap" style={{ alignSelf: "start" }}>
          <table className="tabela">
            <thead>
              <tr>
                <th>Cenário</th>
                <th>0–100 km/h</th>
                <th>80–120 km/h</th>
                <th>Vel. máx.</th>
                <th>Peso/potência</th>
              </tr>
            </thead>
            <tbody>
              {cs.map((c) => {
                const d = c.indicadores as IndDesempenho;
                return (
                  <tr key={c.id}>
                    <td>
                      <span className="nome">
                        <i className="marcador" style={{ background: c.cor }} />
                        {c.nome}
                      </span>
                    </td>
                    <td>
                      <b>{d.t_0_100_s !== null ? `${num(d.t_0_100_s, 1)} s` : "—"}</b>
                    </td>
                    <td>{d.t_80_120_s !== null ? `${num(d.t_80_120_s, 1)} s` : "—"}</td>
                    <td>{num(d.v_max_kmh, 0)} km/h</td>
                    <td>{num(d.peso_potencia_kg_cv, 1)} kg/cv</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <LinhasTempo
          titulo="Velocidade em aceleração plena"
          dados={dados}
          series={cs.map((c, i) => ({ chave: `c${i}`, nome: c.nome, cor: c.cor }))}
          unidade="km/h"
          altura={220}
        />
      </div>
    </div>
  );
}

function amostrar(s: Serie, max = 900): Record<string, number>[] {
  const passo = Math.max(1, Math.ceil(s.t.length / max));
  const out: Record<string, number>[] = [];
  for (let i = 0; i < s.t.length; i += passo) {
    const r: Record<string, number> = { t: s.t[i], v: s.v_kmh[i] };
    if (s.p_motor_kw) r.pm = s.p_motor_kw[i];
    if (s.p_eletrico_kw) r.pe = s.p_eletrico_kw[i];
    if (s.rpm) r.rpm = s.rpm[i];
    if (s.soc) r.soc = s.soc[i];
    if (s.marcha) r.marcha = s.marcha[i];
    out.push(r);
  }
  return out;
}

function SecaoDetalhe({ cs }: { cs: CenarioCor[] }) {
  const t = useTemaGrafico();
  const [sel, setSel] = useState(0);
  const c = cs[Math.min(sel, cs.length - 1)];
  const ciclos = Object.keys(c.series);
  const [ciclo, setCiclo] = useState(ciclos[0]);
  const cicloAtual = ciclos.includes(ciclo) ? ciclo : ciclos[0];
  const serie = c.series[cicloAtual];
  const dados = useMemo(() => amostrar(serie), [serie]);
  const ind =
    c.ensaio_tipo === "ensaio_pbev"
      ? (c.indicadores as IndPBEV)[cicloAtual as "urbano" | "estrada"]
      : (c.indicadores as { ciclo: IndCiclo }).ciclo;
  const slot = (i: number) => corSerie(i, t.escuro);
  const potencias = [
    ...(serie.p_motor_kw ? [{ chave: "pm", nome: "Motor a combustão", cor: slot(1) }] : []),
    ...(serie.p_eletrico_kw ? [{ chave: "pe", nome: "Motor elétrico (negativo = regeneração)", cor: slot(2) }] : []),
  ];
  const nomesCiclo: Record<string, string> = { urbano: "Urbano (FTP-75)", estrada: "Estrada (HWFET)", ciclo: ind.ciclo_nome };
  const e = ind.energias_mj;

  return (
    <div className="secao">
      <div className="secao-titulo">
        <h3>Detalhe no tempo</h3>
        <span>gráficos sincronizados — passe o mouse para ler todos no mesmo instante</span>
        <div className="acoes">
          <select className="selecao" style={{ width: 260 }} value={sel} onChange={(ev) => setSel(Number(ev.target.value))}>
            {cs.map((x, i) => (
              <option key={x.id} value={i}>
                {x.nome} · {x.ensaio_nome}
              </option>
            ))}
          </select>
          {ciclos.length > 1 && (
            <div className="segmentado">
              {ciclos.map((k) => (
                <button key={k} className={k === cicloAtual ? "ativo" : ""} onClick={() => setCiclo(k)}>
                  {nomesCiclo[k] ?? k}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="grade-graficos">
        <LinhasTempo titulo="Velocidade do ciclo" dados={dados} series={[{ chave: "v", nome: "Velocidade", cor: slot(0) }]} unidade="km/h" syncId="detalhe" />
        {potencias.length > 0 && (
          <LinhasTempo titulo="Potência no eixo" dados={dados} series={potencias} unidade="kW" syncId="detalhe" />
        )}
        {serie.rpm && (
          <LinhasTempo titulo="Rotação do motor" dados={dados} series={[{ chave: "rpm", nome: "Rotação", cor: slot(3) }]} unidade="rpm" casas={0} syncId="detalhe" />
        )}
        {serie.soc && (
          <LinhasTempo titulo="Estado de carga da bateria" dados={dados} series={[{ chave: "soc", nome: "SOC", cor: slot(2) }]} unidade="%" syncId="detalhe" />
        )}
        <div className="grafico">
          <h4>Para onde vai a energia nas rodas</h4>
          <p>
            {nomesCiclo[cicloAtual]} · {num(ind.distancia_km, 2)} km · média {num(ind.v_media_kmh, 1)} km/h
            {ind.eficiencia_media_motor ? ` · eficiência média do motor ${num(ind.eficiencia_media_motor * 100, 1)}%` : ""}
          </p>
          <BarraEmpilhada
            partes={[
              { nome: "Aerodinâmica", valor: e.aerodinamica ?? 0, cor: slot(0) },
              { nome: "Rolamento", valor: e.rolamento ?? 0, cor: slot(1) },
              { nome: "Frenagem", valor: e.frenagem ?? 0, cor: slot(2) },
              ...((e.rampa ?? 0) > 0.001 ? [{ nome: "Rampa", valor: e.rampa, cor: slot(3) }] : []),
            ]}
          />
          {ind.tempo_excedido_s > 1 && (
            <div className="aviso-topo" style={{ marginTop: 10 }}>
              <TriangleAlert size={15} /> O trem de força não acompanhou o ciclo por {num(ind.tempo_excedido_s, 0)} s.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function VistaPainel({ painel, cenarios }: { painel: Painel; cenarios: CenarioCor[] }) {
  const cs = cenarios.filter((c) => painel.cenarios.includes(c.id));
  const consumo = cs.filter((c) => c.ensaio_tipo !== "desempenho" && principal(c)?.km_por_unidade != null);
  const desempenho = cs.filter((c) => c.ensaio_tipo === "desempenho");
  const variosEnsaios = new Set(consumo.map((c) => c.ensaio_id)).size > 1;
  const precos = Object.fromEntries(cs.map((c) => [c.id, c.preco]));

  if (!cs.length) return <div className="vazio-resultados">Nenhum cenário chega a este painel. Conecte um ensaio à sua entrada.</div>;

  const rotulos = rotulosCurtos(consumo, variosEnsaios);
  const barras = (f: (c: CenarioCor) => number | null) =>
    consumo.map((c) => ({ nome: rotulos.get(c.id) ?? c.nome, valor: f(c), cor: c.cor }));

  return (
    <>
      <div className="legenda-cenarios">
        {cs
          .filter((c, i, a) => a.findIndex((x) => x.nome === c.nome) === i)
          .map((c) => (
            <span key={c.id}>
              <i className="marcador" style={{ background: c.cor }} />
              {c.nome}
            </span>
          ))}
      </div>
      {painel.paridades.map((p) => (
        <HeroiParidade key={p.cenario_gasolina} p={p} pg={precos[p.cenario_gasolina]} pe={precos[p.cenario_etanol]} />
      ))}
      {consumo.length > 0 && (
        <>
          <div className="grade-cartoes">
            {consumo.map((c) => (
              <CartaoCenario key={c.id} c={c} kmMes={painel.km_mes} />
            ))}
          </div>
          <div className="secao">
            <div className="secao-titulo">
              <h3>Comparativo</h3>
              <span>a cor identifica o cenário em todos os gráficos</span>
            </div>
            <div className="grade-graficos duas">
              <BarrasCenarios
                titulo={`Custo mensal com energia (${num(painel.km_mes, 0)} km/mês)`}
                subtitulo="preços informados nos blocos de combustível e bateria"
                dados={barras((c) => (principal(c)!.custo_r_km !== null ? principal(c)!.custo_r_km! * painel.km_mes : null))}
                casas={0}
                prefixo="R$ "
              />
              <BarrasCenarios
                titulo="Consumo energético (MJ/km)"
                subtitulo="métrica do PBEV e das metas do programa Mover"
                dados={barras((c) => principal(c)!.mj_km)}
                casas={2}
              />
              <BarrasCenarios
                titulo="CO₂ fóssil de escapamento (g/km)"
                subtitulo="etanol e biodiesel contam como biogênicos, como na etiqueta do PBEV"
                dados={barras((c) => principal(c)!.co2_fossil_g_km)}
                casas={0}
              />
              <BarrasCenarios
                titulo="CO₂e do poço à roda (g/km)"
                subtitulo="inclui produção do combustível ou geração elétrica"
                dados={barras((c) => principal(c)!.co2_wtw_g_km)}
                casas={0}
              />
            </div>
          </div>
          <TabelaConsumo cs={consumo} kmMes={painel.km_mes} />
        </>
      )}
      {desempenho.length > 0 && <SecaoDesempenho cs={desempenho} />}
      {consumo.length > 0 && <SecaoDetalhe cs={consumo} />}
    </>
  );
}

export function Resultados() {
  const resultado = useEstado((s) => s.resultado);
  const aberto = useEstado((s) => s.resultadosAbertos);
  const simulando = useEstado((s) => s.simulando);
  const desatualizado = useEstado(resultadoDesatualizado);
  const erroSimulacao = useEstado((s) => s.erroSimulacao);
  const { abrirResultados, focar } = useEstado.getState();
  const t = useTemaGrafico();
  const [altura, setAltura] = useState(() => Math.round(window.innerHeight * 0.44));
  const [maximizado, setMaximizado] = useState(false);
  const [aba, setAba] = useState(0);
  const arrastando = useRef(false);
  const [arrasteAtivo, setArrasteAtivo] = useState(false);

  useEffect(() => {
    const mover = (e: PointerEvent) => {
      if (!arrastando.current) return;
      setAltura(Math.min(Math.max(window.innerHeight - e.clientY, 160), window.innerHeight - 140));
    };
    const soltar = () => {
      arrastando.current = false;
      setArrasteAtivo(false);
    };
    window.addEventListener("pointermove", mover);
    window.addEventListener("pointerup", soltar);
    return () => {
      window.removeEventListener("pointermove", mover);
      window.removeEventListener("pointerup", soltar);
    };
  }, []);

  const cenarios: CenarioCor[] = useMemo(() => {
    const ordem: string[] = [];
    for (const c of resultado?.cenarios ?? []) if (!ordem.includes(c.nome)) ordem.push(c.nome);
    // a cor acompanha o cenário (veículo + energético), igual em todos os ensaios
    return (resultado?.cenarios ?? []).map((c) => ({ ...c, cor: corSerie(ordem.indexOf(c.nome), t.escuro) }));
  }, [resultado, t.escuro]);

  const paineis = resultado?.paineis ?? [];
  const painel = paineis[Math.min(aba, Math.max(paineis.length - 1, 0))];
  const mensagens = [
    ...(resultado?.erros ?? []).map((m) => ({ ...m, tipo: "erro" as const })),
    ...(resultado?.avisos ?? []).map((m) => ({ ...m, tipo: "aviso" as const })),
  ];
  const h = !aberto ? 48 : maximizado ? "calc(100vh - 120px)" : altura;

  return (
    <section className="gaveta" style={{ height: h }}>
      {aberto && !maximizado && (
        <div
          className={`gaveta-alca ${arrasteAtivo ? "ativa" : ""}`}
          onPointerDown={() => {
            arrastando.current = true;
            setArrasteAtivo(true);
          }}
          role="separator"
          aria-label="Redimensionar resultados"
        />
      )}
      <div className="gaveta-cabeca">
        <h2>
          <ChartColumn size={17} /> Resultados
        </h2>
        {simulando && <LoaderCircle size={15} className="girando" />}
        {resultado && (
          <span className="meta">
            {resultado.cenarios.length} cenário{resultado.cenarios.length === 1 ? "" : "s"} · {num(resultado.tempo_s, 2)} s
          </span>
        )}
        {resultado && (
          <span className={`selo ${resultado.motor === "openmodelica" ? "omc" : "rapido"}`}>
            {resultado.motor === "openmodelica" ? "OpenModelica" : "motor rápido"}
          </span>
        )}
        {desatualizado && !simulando && <span className="selo desatualizado">desatualizado — clique em Simular</span>}
        {mensagens.length > 0 && (
          <span className="selo desatualizado" style={{ background: "var(--erro-suave)", color: "var(--erro)" }}>
            {mensagens.length} alerta{mensagens.length > 1 ? "s" : ""}
          </span>
        )}
        {aberto && paineis.length > 1 && (
          <div className="abas">
            {paineis.map((p, i) => (
              <button key={p.id} className={`aba ${i === aba ? "ativa" : ""}`} onClick={() => setAba(i)}>
                {p.nome}
              </button>
            ))}
          </div>
        )}
        <div style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
          {aberto && (
            <button className="botao icone fantasma" title={maximizado ? "Restaurar" : "Maximizar"} onClick={() => setMaximizado(!maximizado)}>
              {maximizado ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          )}
          <button className="botao icone fantasma" title={aberto ? "Recolher" : "Expandir"} onClick={() => abrirResultados(!aberto)}>
            {aberto ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
        </div>
      </div>
      {aberto && (
        <div className={`gaveta-corpo ${simulando ? "carregando" : ""}`}>
          {erroSimulacao && (
            <div className="mensagem erro" style={{ marginBottom: 12 }}>
              <CircleAlert size={15} style={{ flex: "none" }} /> {erroSimulacao}
            </div>
          )}
          {mensagens.length > 0 && (
            <div className="mensagens">
              {mensagens.map((m, i) => (
                <button key={i} className={`mensagem ${m.tipo}`} onClick={() => m.no && focar(m.no)}>
                  {m.tipo === "erro" ? <CircleAlert size={15} style={{ flex: "none" }} /> : <TriangleAlert size={15} style={{ flex: "none" }} />}
                  {m.mensagem}
                </button>
              ))}
            </div>
          )}
          {!resultado && !erroSimulacao && (
            <div className="vazio-resultados">Monte um workflow e clique em Simular para ver consumo, custos, CO₂ e desempenho.</div>
          )}
          {painel && <VistaPainel painel={painel} cenarios={cenarios} />}
        </div>
      )}
    </section>
  );
}
