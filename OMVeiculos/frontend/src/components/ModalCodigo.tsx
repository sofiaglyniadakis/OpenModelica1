// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { Check, Copy, Download, LoaderCircle, X } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { useEstado } from "../lib/store";
import type { CodigoModelica } from "../lib/tipos";


function realcar(codigo: string): ReactNode[] {
  // realce simples: comentários, strings, palavras-chave e números
  const partes: ReactNode[] = [];
  const re = /(\/\/[^\n]*)|("(?:[^"\\]|\\.)*")|(\b\d+(?:\.\d+)?(?:e[-+]?\d+)?\b)|\b(model|package|end|extends|annotation|within|parameter|true|false|uses|experiment)\b/g;
  let ultimo = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(codigo))) {
    if (m.index > ultimo) partes.push(codigo.slice(ultimo, m.index));
    const cls = m[1] ? "com" : m[2] ? "str" : m[3] ? "num" : "kw";
    partes.push(
      <span key={k++} className={cls}>
        {m[0]}
      </span>,
    );
    ultimo = m.index + m[0].length;
  }
  partes.push(codigo.slice(ultimo));
  return partes;
}

function baixar(nome: string, conteudo: string) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([conteudo], { type: "text/plain;charset=utf-8" }));
  a.download = nome;
  a.click();
  URL.revokeObjectURL(a.href);
}

export function ModalCodigo() {
  const aberto = useEstado((s) => s.modalCodigo);
  const { abrirCodigo, paraWorkflow } = useEstado.getState();
  const [dados, setDados] = useState<CodigoModelica | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  useEffect(() => {
    if (!aberto) return;
    setDados(null);
    setErro(null);
    api.modelica(paraWorkflow()).then(setDados, (e: Error) => setErro(e.message));
    const esc = (e: KeyboardEvent) => e.key === "Escape" && abrirCodigo(false);
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto, abrirCodigo, paraWorkflow]);

  const realcado = useMemo(() => (dados?.codigo ? realcar(dados.codigo) : null), [dados]);
  if (!aberto) return null;

  return (
    <div className="fundo-modal" onMouseDown={(e) => e.target === e.currentTarget && abrirCodigo(false)}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Código Modelica">
        <div className="modal-cabeca">
          <h2>Código Modelica dos cenários</h2>
          {dados?.codigo && (
            <>
              <button
                className="botao"
                onClick={async () => {
                  await navigator.clipboard.writeText(dados.codigo);
                  setCopiado(true);
                  setTimeout(() => setCopiado(false), 1500);
                }}
              >
                {copiado ? <Check size={15} /> : <Copy size={15} />} Copiar
              </button>
              <button className="botao" onClick={() => baixar(`${dados.pacote}.mo`, dados.codigo)}>
                <Download size={15} /> {dados.pacote}.mo
              </button>
              <button className="botao" onClick={() => baixar("simular.mos", dados.script)}>
                <Download size={15} /> simular.mos
              </button>
            </>
          )}
          <button className="botao icone fantasma" onClick={() => abrirCodigo(false)} title="Fechar (Esc)">
            <X size={16} />
          </button>
        </div>
        <div className="modal-corpo">
          <p style={{ marginTop: 0, color: "var(--texto-2)", lineHeight: 1.55 }}>
            Cada cenário do workflow vira um modelo que estende os experimentos da biblioteca <b>VeiculosLevesBR</b> (pasta{" "}
            <code>OMVeiculos/modelica</code>). Abra no OpenModelica com <code>loadFile</code> ou rode o script <code>simular.mos</code> com{" "}
            <code>omc simular.mos</code>.
          </p>
          {!dados && !erro && (
            <p>
              <LoaderCircle size={16} className="girando" /> Gerando…
            </p>
          )}
          {erro && <div className="mensagem erro">{erro}</div>}
          {dados && dados.erros.length > 0 && (
            <div className="mensagens">
              {dados.erros.map((m, i) => (
                <div key={i} className="mensagem erro">
                  {m.mensagem}
                </div>
              ))}
            </div>
          )}
          {dados && !dados.codigo && <p>Nenhum cenário completo para gerar código.</p>}
          {realcado && <pre className="codigo">{realcado}</pre>}
        </div>
      </div>
    </div>
  );
}
