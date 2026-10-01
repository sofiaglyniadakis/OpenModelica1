// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { num } from "../lib/formato";
import { useEstado } from "../lib/store";

export function useTemaGrafico() {
  const escuro = useEstado((s) => s.tema === "escuro");
  return escuro
    ? { escuro, grade: "#263045", eixo: "#3a4560", texto: "#8d97ab", superficie: "#141b2a", cursor: "rgba(255,255,255,0.06)" }
    : { escuro, grade: "#e1e0d9", eixo: "#c3c2b7", texto: "#6b6a65", superficie: "#fcfcfb", cursor: "rgba(15,23,42,0.05)" };
}

const truncar = (t: string, n = 26) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);

interface ItemBarra {
  nome: string;
  valor: number | null;
  cor: string;
}

export function BarrasCenarios({
  titulo,
  subtitulo,
  dados,
  casas = 1,
  prefixo = "",
}: {
  titulo: string;
  subtitulo?: string;
  dados: ItemBarra[];
  casas?: number;
  prefixo?: string;
}) {
  const t = useTemaGrafico();
  const validos = dados.filter((d) => d.valor !== null && Number.isFinite(d.valor));
  const fmt = (v: number) => `${prefixo}${num(v, casas)}`;
  const altura = 34 + validos.length * 34;
  if (validos.length && validos.every((d) => d.valor === 0)) {
    return (
      <div className="grafico">
        <h4>{titulo}</h4>
        {subtitulo && <p>{subtitulo}</p>}
        <div className="vazio-resultados" style={{ padding: 18 }}>
          Zero em todos os cenários ({fmt(0)}).
        </div>
      </div>
    );
  }
  return (
    <div className="grafico">
      <h4>{titulo}</h4>
      {subtitulo && <p>{subtitulo}</p>}
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={validos} layout="vertical" margin={{ top: 4, right: 64, bottom: 4, left: 4 }} barCategoryGap={8}>
          <CartesianGrid horizontal={false} stroke={t.grade} />
          <XAxis
            type="number"
            tick={{ fill: t.texto, fontSize: 11 }}
            stroke={t.eixo}
            tickFormatter={(v: number) => num(v, v >= 100 ? 0 : casas, 0)}
            domain={[0, "auto"]}
          />
          <YAxis
            type="category"
            dataKey="nome"
            width={190}
            tick={{ fill: t.texto, fontSize: 11.5 }}
            tickFormatter={(v: string) => truncar(v, 30)}
            stroke={t.eixo}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: t.cursor }}
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="dica-tooltip">
                  <div className="linha">
                    <span>
                      <i className="marcador" style={{ background: (payload[0].payload as ItemBarra).cor }} />
                      {(payload[0].payload as ItemBarra).nome}
                    </span>
                  </div>
                  <b style={{ fontSize: 15 }}>{fmt(Number(payload[0].value))}</b>
                </div>
              ) : null
            }
          />
          <Bar dataKey="valor" barSize={16} radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {validos.map((d) => (
              <Cell key={d.nome} fill={d.cor} />
            ))}
            <LabelList
              dataKey="valor"
              position="right"
              formatter={(v: unknown) => fmt(Number(v))}
              style={{ fill: t.texto, fontSize: 11.5, fontWeight: 600 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface SerieLinha {
  chave: string;
  nome: string;
  cor: string;
}

export function LinhasTempo({
  titulo,
  subtitulo,
  dados,
  series,
  unidade,
  casas = 1,
  syncId,
  altura = 170,
  xChave = "t",
  xUnidade = "s",
}: {
  titulo: string;
  subtitulo?: string;
  dados: Record<string, number>[];
  series: SerieLinha[];
  unidade: string;
  casas?: number;
  syncId?: string;
  altura?: number;
  xChave?: string;
  xUnidade?: string;
}) {
  const t = useTemaGrafico();
  return (
    <div className="grafico">
      <h4>
        {titulo} <span style={{ color: "var(--texto-3)", fontWeight: 400 }}>({unidade})</span>
      </h4>
      {subtitulo && <p>{subtitulo}</p>}
      {series.length > 1 && (
        <div className="legenda-cenarios" style={{ marginBottom: 4 }}>
          {series.map((s) => (
            <span key={s.chave}>
              <i className="marcador linha" style={{ background: s.cor }} />
              {s.nome}
            </span>
          ))}
        </div>
      )}
      <ResponsiveContainer width="100%" height={altura}>
        <LineChart data={dados} syncId={syncId} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke={t.grade} />
          <XAxis
            dataKey={xChave}
            type="number"
            domain={["dataMin", "dataMax"]}
            tick={{ fill: t.texto, fontSize: 11 }}
            stroke={t.eixo}
            tickFormatter={(v: number) => num(v, 0)}
            unit={` ${xUnidade}`}
          />
          <YAxis tick={{ fill: t.texto, fontSize: 11 }} stroke={t.eixo} width={44} tickFormatter={(v: number) => num(v, 0)} />
          <Tooltip
            cursor={{ stroke: t.eixo, strokeWidth: 1 }}
            content={({ active, payload, label }) =>
              active && payload?.length ? (
                <div className="dica-tooltip">
                  <div className="t">
                    {num(Number(label), 1)} {xUnidade}
                  </div>
                  {payload.map((p) => {
                    const s = series.find((x) => x.chave === p.dataKey);
                    return (
                      <div className="linha" key={String(p.dataKey)}>
                        <span>
                          <i className="marcador linha" style={{ background: s?.cor }} />
                          {s?.nome}
                        </span>
                        <b>
                          {num(Number(p.value), casas)} {unidade}
                        </b>
                      </div>
                    );
                  })}
                </div>
              ) : null
            }
          />
          {series.map((s) => (
            <Line
              key={s.chave}
              dataKey={s.chave}
              stroke={s.cor}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
              strokeLinejoin="round"
              strokeLinecap="round"
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/** Barra empilhada simples (HTML) para o balanço de energia de um cenário. */
export function BarraEmpilhada({ partes }: { partes: { nome: string; valor: number; cor: string }[] }) {
  const total = partes.reduce((a, p) => a + Math.max(p.valor, 0), 0) || 1;
  return (
    <div>
      <div style={{ display: "flex", gap: 2, height: 18, borderRadius: 5, overflow: "hidden", margin: "6px 0 10px" }}>
        {partes
          .filter((p) => p.valor > 0)
          .map((p) => (
            <div
              key={p.nome}
              title={`${p.nome}: ${num(p.valor, 2)} MJ (${num((p.valor / total) * 100, 0)}%)`}
              style={{ width: `${(p.valor / total) * 100}%`, background: p.cor }}
            />
          ))}
      </div>
      <div className="legenda-cenarios" style={{ marginBottom: 0 }}>
        {partes.map((p) => (
          <span key={p.nome}>
            <i className="marcador" style={{ background: p.cor }} />
            {p.nome}: <b style={{ color: "var(--texto)" }}>{num(p.valor, 2)} MJ</b> ({num((Math.max(p.valor, 0) / total) * 100, 0)}%)
          </span>
        ))}
      </div>
    </div>
  );
}
