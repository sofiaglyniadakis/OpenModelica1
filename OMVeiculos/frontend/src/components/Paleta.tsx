// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { Search } from "lucide-react";
import { useMemo, useState, type DragEvent } from "react";
import { useEstado } from "../lib/store";
import { IconeBloco } from "./Icone";

export const MIME_BLOCO = "application/x-omveiculos-bloco";
const ORDEM = ["Energia", "Trem de força", "Veículo", "Ensaios", "Análise"];

function iniciarArraste(e: DragEvent, tipo: string, preset: string | null) {
  e.dataTransfer.setData(MIME_BLOCO, JSON.stringify({ tipo, preset }));
  e.dataTransfer.effectAllowed = "move";
}

export function Paleta({ destaque, aoAdicionar }: { destaque: string | null; aoAdicionar: (tipo: string, preset: string | null) => void }) {
  const catalogo = useEstado((s) => s.catalogo);
  const [busca, setBusca] = useState("");

  const grupos = useMemo(() => {
    const q = busca.trim().toLowerCase();
    const blocos = (catalogo?.blocos ?? []).filter(
      (b) =>
        !q ||
        b.nome.toLowerCase().includes(q) ||
        b.descricao.toLowerCase().includes(q) ||
        b.presets.some((p) => p.nome.toLowerCase().includes(q)),
    );
    return ORDEM.map((cat) => ({ cat, blocos: blocos.filter((b) => b.categoria === cat) })).filter((g) => g.blocos.length);
  }, [catalogo, busca]);

  return (
    <aside className="lateral">
      <div className="lateral-cabeca">
        <h2>Blocos</h2>
        <p>Arraste para a área de trabalho e conecte as portas coloridas.</p>
        <label className="busca">
          <Search size={15} />
          <input placeholder="Buscar bloco ou modelo…" value={busca} onChange={(e) => setBusca(e.target.value)} />
        </label>
      </div>
      <div className="rolagem">
        {grupos.map((g) => (
          <div className="categoria" key={g.cat}>
            <div className="categoria-titulo">{g.cat}</div>
            {g.blocos.map((b) => (
              <div className={`item-bloco ${destaque === g.cat ? "destacado" : ""}`} key={b.tipo}>
                <div
                  className="item-cabeca"
                  draggable
                  onDragStart={(e) => iniciarArraste(e, b.tipo, null)}
                  onDoubleClick={() => aoAdicionar(b.tipo, null)}
                  title="Arraste para a área de trabalho (ou dê dois cliques)"
                >
                  <IconeBloco nome={b.icone} cor={b.cor} />
                  <div className="info">
                    <b>{b.nome}</b>
                    <small>{b.descricao}</small>
                  </div>
                </div>
                {b.presets.length > 1 && (
                  <div className="presets">
                    {b.presets.map((p) => (
                      <span
                        key={p.nome}
                        className="chip-preset"
                        draggable
                        onDragStart={(e) => iniciarArraste(e, b.tipo, p.nome)}
                        onDoubleClick={() => aoAdicionar(b.tipo, p.nome)}
                        title="Arraste esta predefinição"
                      >
                        {p.nome}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
        <div className="dica-paleta">
          Monte o fluxo da esquerda para a direita: <b>energia → motor → transmissão → veículo → ensaio → painel</b>. Ligue dois
          combustíveis ao mesmo motor flex para comparar etanol e gasolina.
        </div>
      </div>
    </aside>
  );
}
