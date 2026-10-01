// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { CircleAlert, Sparkles, TriangleAlert } from "lucide-react";
import { memo, useMemo } from "react";
import { num, resumoBloco } from "../lib/formato";
import { useEstado, type NoBloco as TNoBloco } from "../lib/store";
import type { Cenario, IndPBEV } from "../lib/tipos";
import { IconeBloco } from "./Icone";

function destaqueResultado(cenarios: Cenario[]): string | null {
  if (!cenarios.length) return null;
  const c = cenarios[0];
  if (c.ensaio_tipo === "desempenho") {
    const ind = c.indicadores as { t_0_100_s: number | null };
    return ind.t_0_100_s ? `0–100 em ${num(ind.t_0_100_s, 1)} s` : null;
  }
  const ind = c.ensaio_tipo === "ensaio_pbev" ? (c.indicadores as IndPBEV).combinado : (c.indicadores as { ciclo: IndPBEV["urbano"] }).ciclo;
  if (!ind?.km_por_unidade) return null;
  return `${num(ind.km_por_unidade, 1)} km/${ind.unidade}`;
}

function NoBlocoBase({ id, data, selected }: NodeProps<TNoBloco>) {
  const bloco = useEstado((s) => s.blocos[data.tipo]);
  const portas = useEstado((s) => s.catalogo?.portas);
  const ciclos = useEstado((s) => s.catalogo?.blocos.find((b) => b.tipo === "ciclo")?.parametros.find((p) => p.chave === "ciclo")?.opcoes);
  const resultado = useEstado((s) => s.resultado);

  const erro = resultado?.erros.find((m) => m.no === id);
  const aviso = resultado?.avisos.find((m) => m.no === id);
  const resumo = useMemo(
    () => resumoBloco(data.tipo, data.params, (c) => ciclos?.find((o) => o.valor === c)?.rotulo ?? c),
    [data.tipo, data.params, ciclos],
  );
  const destaque = useMemo(() => {
    if (!resultado) return null;
    if (data.tipo === "veiculo") {
      const cs = resultado.cenarios.filter((c) => c.veiculo_id === id && c.ensaio_tipo !== "desempenho");
      if (cs.length > 1) return `${cs.length} cenários simulados`;
      return destaqueResultado(cs);
    }
    if (["ensaio_pbev", "ciclo", "desempenho"].includes(data.tipo)) {
      const n = resultado.cenarios.filter((c) => c.ensaio_id === id).length;
      return n ? `${n} cenário${n > 1 ? "s" : ""} simulado${n > 1 ? "s" : ""}` : null;
    }
    return null;
  }, [resultado, data.tipo, id]);

  if (!bloco) return null;
  const entrada = bloco.entradas[0];
  const saida = bloco.saidas[0];
  const cor = (t?: string) => (t && portas?.[t]?.cor) || "#64748b";

  return (
    <div className={`no ${selected ? "selecionado" : ""} ${erro ? "com-erro" : ""}`}>
      <div className="no-faixa" style={{ background: bloco.cor }} />
      <div className="no-cabeca">
        <IconeBloco nome={bloco.icone} cor={bloco.cor} />
        <div className="titulo">
          <b title={data.rotulo}>{data.rotulo}</b>
          <small>{bloco.nome}</small>
        </div>
      </div>
      <div className="no-corpo">
        {resumo.filter(Boolean).map((r, i) => (
          <span className="etiqueta" key={i}>
            {r}
          </span>
        ))}
      </div>
      {erro && (
        <div className="no-alerta erro">
          <CircleAlert size={14} style={{ flex: "none", marginTop: 1 }} />
          {erro.mensagem}
        </div>
      )}
      {!erro && aviso && (
        <div className="no-alerta aviso">
          <TriangleAlert size={14} style={{ flex: "none", marginTop: 1 }} />
          {aviso.mensagem}
        </div>
      )}
      {!erro && destaque && (
        <div className="no-resultado">
          <Sparkles size={13} />
          {destaque}
        </div>
      )}
      {entrada && (
        <Handle
          type="target"
          position={Position.Left}
          id={entrada.id}
          className="porta"
          style={{ background: cor(entrada.tipo) }}
          title={`${entrada.rotulo}${entrada.multiplas ? " (aceita várias conexões)" : ""}`}
        >
          <span className="porta-rotulo esq">{entrada.rotulo}</span>
        </Handle>
      )}
      {saida && (
        <Handle type="source" position={Position.Right} id={saida.id} className="porta" style={{ background: cor(saida.tipo) }} title={saida.rotulo} />
      )}
    </div>
  );
}

export const NoBloco = memo(NoBlocoBase);
