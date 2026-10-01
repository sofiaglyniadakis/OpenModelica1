// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import type { Params, Valor } from "./tipos";

const cache = new Map<string, Intl.NumberFormat>();

export function num(v: number | null | undefined, casas = 1, minimo?: number): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  const chave = `${casas}-${minimo ?? casas}`;
  let f = cache.get(chave);
  if (!f) {
    f = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: casas, minimumFractionDigits: minimo ?? casas });
    cache.set(chave, f);
  }
  return f.format(v);
}

export const reais = (v: number | null | undefined, casas = 2) =>
  v === null || v === undefined || !Number.isFinite(v) ? "—" : `R$ ${num(v, casas)}`;

export const pct = (v: number | null | undefined, casas = 1) =>
  v === null || v === undefined ? "—" : `${num(v * 100, casas)}%`;

/** Número para campos editáveis: vírgula decimal, sem separador de milhar. */
export function numEntrada(v: number, casas: number): string {
  if (!Number.isFinite(v)) return "";
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: casas, useGrouping: false }).format(v);
}

/** Converte texto digitado (aceita vírgula ou ponto decimal) em número. */
export function lerNumero(texto: string): number | null {
  const t = texto.trim().replace(/\s/g, "").replace(",", ".");
  if (t === "" || t === "-" || t === ".") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

export function raioPneu(codigo: string): number | null {
  const m = /(\d{3})\s*\/\s*(\d{2})\s*[A-Za-z]*\s*(\d{2})/.exec(codigo ?? "");
  if (!m) return null;
  const [l, p, a] = [Number(m[1]), Number(m[2]), Number(m[3])];
  return 0.975 * ((a * 0.0254) / 2 + (l * p) / 100 / 1000);
}

const n = (p: Params, k: string) => Number(p[k] ?? 0);

/** Conversões exibidas abaixo do campo (ficha técnica -> SI). */
export function conversao(unidade: string | undefined, valor: Valor): string | null {
  const v = Number(valor);
  if (!Number.isFinite(v)) return null;
  if (unidade === "cv") return `${num(v * 0.73549875, 1)} kW`;
  if (unidade === "kgfm") return `${num(v * 9.80665, 1)} N·m`;
  return null;
}

/** Resumo de uma linha exibido no cartão do bloco. */
export function resumoBloco(tipo: string, p: Params, nomeCiclo?: (id: string) => string): string[] {
  switch (tipo) {
    case "combustivel": {
      const t = p.tipo;
      const un = t === "gnv" ? "m³" : "L";
      const nome =
        t === "gasolina" ? `E${num(n(p, "teor_etanol"), 0)}` : t === "etanol" ? "EHC" : t === "diesel" ? `B${num(n(p, "teor_biodiesel"), 0)}` : "GNV";
      return [nome, `${num(n(p, "preco"), 2)} R$/${un}`];
    }
    case "motor_combustao": {
      const flex = p.tipo === "flex";
      const pot = flex ? `${num(n(p, "potencia_g"), 0)}/${num(n(p, "potencia_e"), 0)} cv` : `${num(n(p, "potencia_g"), 0)} cv`;
      const tq = flex ? `${num(n(p, "torque_g"), 1)}/${num(n(p, "torque_e"), 1)} kgfm` : `${num(n(p, "torque_g"), 1)} kgfm`;
      const tipoTxt = p.tipo === "flex" ? "Flex" : p.tipo === "diesel" ? "Diesel" : "Gasolina";
      return [`${num(n(p, "cilindrada"), 1)} L ${tipoTxt}`, pot, tq].concat(p.start_stop ? ["start-stop"] : []);
    }
    case "motor_eletrico":
      return [`${num(n(p, "potencia"), 0)} cv`, `${num(n(p, "torque"), 1)} kgfm`];
    case "bateria":
      return [`${num(n(p, "capacidade"), 1)} kWh`, `SOC ${num(n(p, "soc_min"), 0)}–${num(n(p, "soc_max"), 0)}%`];
    case "transmissao": {
      const rel = String(p.relacoes ?? "").split(";").filter((s) => s.trim()).length;
      const tipo = { manual: `Manual ${rel}M`, automatica: `Automática ${rel}M`, cvt: "CVT", redutor: "Redutor" }[String(p.tipo)] ?? "";
      return [tipo, `dif. ${num(n(p, "diferencial"), 2)}`];
    }
    case "veiculo": {
      const ex = [`${num(n(p, "massa"), 0)} kg`, String(p.pneu ?? "")];
      if (p.modo_resistencia === "fisico") ex.push(`Cd ${num(n(p, "cd"), 2)}`);
      if (p.ar_condicionado) ex.push("A/C ligado");
      return ex;
    }
    case "ensaio_pbev":
      return ["FTP-75 + HWFET", "combinado 55/45"];
    case "ciclo": {
      const c = String(p.ciclo);
      const extra = c === "constante" ? [`${num(n(p, "velocidade_constante"), 0)} km/h`] : [];
      const amb = n(p, "inclinacao") !== 0 ? [`rampa ${num(n(p, "inclinacao"), 1)}%`] : [];
      return [nomeCiclo ? nomeCiclo(c) : c, ...extra, `${num(n(p, "temperatura"), 0)} °C`, ...amb];
    }
    case "desempenho":
      return ["0–100 · 80–120", "vel. máxima"];
    case "painel":
      return [`${num(n(p, "km_mes"), 0)} km/mês`];
    default:
      return [];
  }
}

export const NOME_ARQ: Record<string, string> = { combustao: "Combustão", eletrico: "Elétrico", hibrido: "Híbrido" };
export const NOME_ENERGETICO: Record<string, string> = {
  gasolina: "Gasolina C",
  etanol: "Etanol",
  diesel: "Diesel",
  gnv: "GNV",
  eletricidade: "Eletricidade",
};
