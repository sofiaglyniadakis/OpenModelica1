// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { corSerie } from "../lib/cores";
import { NOME_ARQ, num } from "../lib/formato";
import type { BalancoExergia, Cenario, Painel } from "../lib/tipos";
import { useTemaGrafico } from "./graficos";

// Ordem fixa: a cor acompanha a categoria em todos os gráficos deste painel.
const GRUPOS: [string, string][] = [
  ["motor_destruicao", "Motor: combustão e atrito"],
  ["calor_rejeitado", "Calor rejeitado (escape + arrefecimento)"],
  ["trem_eletrico", "Trem elétrico (motor, bateria, carregador)"],
  ["transmissao", "Transmissão e embreagem"],
  ["acessorios", "Acessórios e ar-condicionado"],
  ["resistencias", "Aerodinâmica e rolamento"],
  ["frenagem", "Freios e freio-motor"],
  ["armazenada", "Armazenada (rampa, bateria)"],
];

const ITENS: [string, string, string][] = [
  ["motor_destruicao", "Destruição na combustão, atrito e bombeamento", "Motor a combustão"],
  ["escape", "Exergia perdida nos gases de escape", "Motor a combustão"],
  ["arrefecimento", "Exergia perdida no arrefecimento", "Motor a combustão"],
  ["carregador", "Carregador (tomada → bateria)", "Trem elétrico"],
  ["bateria", "Perdas na bateria", "Trem elétrico"],
  ["motor_eletrico", "Motor elétrico e inversor", "Trem elétrico"],
  ["transmissao", "Transmissão e embreagem", "Transmissão"],
  ["acessorios", "Acessórios e ar-condicionado", "Consumidores"],
  ["aerodinamica", "Arrasto aerodinâmico", "Rodas"],
  ["rolamento", "Resistência ao rolamento", "Rodas"],
  ["freios", "Freios de atrito e freio-motor", "Rodas"],
  ["rampa", "Energia potencial (rampa)", "Armazenada"],
  ["armazenada_bateria", "Carga líquida da bateria", "Armazenada"],
];

type Vista = "principal" | "urbano" | "estrada";

const pctNum = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${num(v * 100, 1)}%`);

export function VistaExergia({ painel, cenarios }: { painel: Painel; cenarios: Cenario[] }) {
  const t = useTemaGrafico();
  const [vista, setVista] = useState<Vista>("principal");
  const dados = painel.exergia ?? {};
  const cs = cenarios.filter((c) => dados[c.id]);
  const temPbev = cs.some((c) => dados[c.id].urbano);
  const balanco = (c: Cenario): BalancoExergia => {
    const d = dados[c.id];
    return (vista !== "principal" && d[vista]) || d.principal;
  };
  const cor = (i: number) => corSerie(i, t.escuro);
  const linhas: Record<string, number | string>[] = cs.map((c) => {
    const b = balanco(c);
    return { nome: c.nome, ...Object.fromEntries(GRUPOS.map(([k]) => [k, Math.max(b.grupos_mj_km[k] ?? 0, 0)])) };
  });
  const gruposPresentes = GRUPOS.filter(([k]) => linhas.some((l) => Number(l[k]) > 1e-4));
  const p = painel.parametros ?? {};

  if (!cs.length) {
    return (
      <div className="vazio-resultados">
        Conecte um Ensaio PBEV ou um Ciclo de condução à entrada deste bloco. O ensaio de desempenho não entra na análise exergética.
      </div>
    );
  }

  return (
    <>
      <div className="secao-titulo" style={{ marginBottom: 12 }}>
        <h3>Análise exergética (tanque/tomada → roda)</h3>
        <span>
          T₀ = {num(p.t0_c, 0)} °C · escape {num(p.t_escape_c, 0)} °C · arrefecimento {num(p.t_arrefecimento_c, 0)} °C ·{" "}
          {num((p.fracao_escape ?? 0.5) * 100, 0)}% do calor pelo escape
        </span>
        {temPbev && (
          <div className="acoes">
            <div className="segmentado">
              {(
                [
                  ["principal", "Combinado 55/45"],
                  ["urbano", "Urbano"],
                  ["estrada", "Estrada"],
                ] as [Vista, string][]
              ).map(([k, r]) => (
                <button key={k} className={vista === k ? "ativo" : ""} onClick={() => setVista(k)}>
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grade-cartoes">
        {cs.map((c) => {
          const b = balanco(c);
          return (
            <div className="cartao" key={c.id}>
              <div className="cartao-cabeca">
                <b title={c.nome}>{c.nome}</b>
                <small>{NOME_ARQ[c.arquitetura]}</small>
              </div>
              <div className="metrica-principal">
                {pctNum(b.eficiencia_2a_lei)}
              </div>
              <div className="metrica-rotulo">eficiência de 2ª lei (exergia nas rodas ÷ exergia de entrada)</div>
              <div className="metricas">
                <div>
                  <b>{pctNum(b.eficiencia_1a_lei)}</b>
                  <span>eficiência de 1ª lei (energia)</span>
                </div>
                <div>
                  <b>{num(b.entrada_mj_km, 2)} MJ/km</b>
                  <span>exergia de entrada</span>
                </div>
                <div>
                  <b>{num(b.trabalho_rodas_mj_km, 3)} MJ/km</b>
                  <span>trabalho nas rodas</span>
                </div>
                <div>
                  <b>{pctNum(b.fracao_renovavel)}</b>
                  <span>da exergia é renovável</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="secao">
        <div className="secao-titulo">
          <h3>Para onde vai a exergia</h3>
          <span>destruição e perdas por km; a soma é a exergia de entrada</span>
        </div>
        <div className="grafico">
          <div className="legenda-cenarios" style={{ marginBottom: 6 }}>
            {gruposPresentes.map(([k, nome]) => (
              <span key={k}>
                <i className="marcador" style={{ background: cor(GRUPOS.findIndex((g) => g[0] === k)) }} />
                {nome}
              </span>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={40 + cs.length * 42}>
            <BarChart data={linhas} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }} barCategoryGap={10}>
              <CartesianGrid horizontal={false} stroke={t.grade} />
              <XAxis
                type="number"
                tick={{ fill: t.texto, fontSize: 11 }}
                stroke={t.eixo}
                tickFormatter={(v: number) => num(v, 1, 0)}
                unit=" MJ/km"
              />
              <YAxis
                type="category"
                dataKey="nome"
                width={200}
                tick={{ fill: t.texto, fontSize: 11.5 }}
                tickFormatter={(v: string) => (v.length > 32 ? `${v.slice(0, 31)}…` : v)}
                stroke={t.eixo}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: t.cursor }}
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const total = payload.reduce((a, x) => a + Number(x.value ?? 0), 0);
                  return (
                    <div className="dica-tooltip">
                      <div className="t">{label}</div>
                      {[...payload].reverse().map((x) => {
                        const i = GRUPOS.findIndex((g) => g[0] === x.dataKey);
                        return Number(x.value) > 1e-4 ? (
                          <div className="linha" key={String(x.dataKey)}>
                            <span>
                              <i className="marcador" style={{ background: cor(i) }} />
                              {GRUPOS[i][1]}
                            </span>
                            <b>
                              {num(Number(x.value), 3)} ({num((Number(x.value) / total) * 100, 0)}%)
                            </b>
                          </div>
                        ) : null;
                      })}
                    </div>
                  );
                }}
              />
              {GRUPOS.map(([k], i) => (
                <Bar key={k} dataKey={k} stackId="ex" fill={cor(i)} stroke={t.superficie} strokeWidth={2} barSize={20} isAnimationActive={false} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="secao">
        <div className="secao-titulo">
          <h3>Balanço detalhado</h3>
          <span>MJ/km e % da exergia de entrada</span>
        </div>
        <div className="tabela-wrap">
          <table className="tabela">
            <thead>
              <tr>
                <th>Item</th>
                {cs.map((c) => (
                  <th key={c.id} title={c.nome}>
                    {c.nome.length > 28 ? `${c.nome.slice(0, 27)}…` : c.nome}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <b>Exergia de entrada</b>
                </td>
                {cs.map((c) => (
                  <td key={c.id}>
                    <b>{num(balanco(c).entrada_mj_km, 3)}</b>
                  </td>
                ))}
              </tr>
              {ITENS.filter(([k]) => cs.some((c) => Math.abs(balanco(c).itens_mj_km[k] ?? 0) > 1e-4)).map(([k, nome, grupo]) => (
                <tr key={k}>
                  <td>
                    {nome} <span style={{ color: "var(--texto-3)" }}>· {grupo}</span>
                  </td>
                  {cs.map((c) => {
                    const b = balanco(c);
                    const v = b.itens_mj_km[k] ?? 0;
                    return (
                      <td key={c.id}>
                        {num(v, 3)} <span style={{ color: "var(--texto-3)" }}>({num((v / b.entrada_mj_km) * 100, 1)}%)</span>
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr>
                <td>
                  <b>Trabalho entregue às rodas</b>
                </td>
                {cs.map((c) => (
                  <td key={c.id}>
                    <b>{num(balanco(c).trabalho_rodas_mj_km, 3)}</b>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
        <p style={{ color: "var(--texto-3)", fontSize: 12, lineHeight: 1.5, marginTop: 10 }}>
          O trabalho nas rodas é depois dissipado em arrasto, rolamento e frenagem (linhas “Rodas”), por isso a soma das linhas
          de perdas iguala a exergia de entrada. Exergia química dos combustíveis por φ = ex/PCI (etanol 1,10; gasolina e diesel
          ~1,07; GNV 1,04); eletricidade é exergia pura. A divisão do calor do motor entre escape e arrefecimento é uma hipótese
          (ajuste no bloco). No PBEV, o combinado pondera urbano e estrada por km (55/45), sem ponderação de fases do FTP-75.
        </p>
      </div>
    </>
  );
}
