// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { ReactFlowProvider, useReactFlow } from "@xyflow/react";
import { LoaderCircle, ServerCrash } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Canvas } from "./components/Canvas";
import { Inspetor } from "./components/Inspetor";
import { ModalCodigo } from "./components/ModalCodigo";
import { Paleta } from "./components/Paleta";
import { Resultados } from "./components/Resultados";
import { Topo } from "./components/Topo";
import { ligarEfeitos, useEstado } from "./lib/store";

function editavel(alvo: EventTarget | null) {
  const el = alvo as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
}

function Area() {
  const [destaque, setDestaque] = useState<string | null>(null);
  const { screenToFlowPosition } = useReactFlow();
  const adicionarNoCentro = useCallback(
    (tipo: string, preset: string | null) => {
      const el = document.querySelector(".canvas")?.getBoundingClientRect();
      const centro = el ? { x: el.left + el.width / 2, y: el.top + el.height / 2 } : { x: 400, y: 300 };
      const pos = screenToFlowPosition(centro);
      useEstado.getState().adicionarBloco(tipo, preset, { x: pos.x - 118 + Math.random() * 40, y: pos.y - 40 + Math.random() * 40 });
    },
    [screenToFlowPosition],
  );

  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      const s = useEstado.getState();
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key === "Enter") {
        e.preventDefault();
        s.simular();
      } else if (editavel(e.target)) {
        return;
      } else if (mod && e.key.toLowerCase() === "z") {
        e.preventDefault();
        if (e.shiftKey) s.refazer();
        else s.desfazer();
      } else if (mod && e.key.toLowerCase() === "y") {
        e.preventDefault();
        s.refazer();
      } else if (mod && e.key.toLowerCase() === "d" && s.selecionado) {
        e.preventDefault();
        s.duplicar(s.selecionado);
      }
    };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  }, []);

  return (
    <div className="app">
      <Topo aoDestacar={setDestaque} />
      <div className="corpo">
        <Paleta destaque={destaque} aoAdicionar={adicionarNoCentro} />
        <main className="centro">
          <Canvas />
          <Resultados />
        </main>
        <Inspetor />
      </div>
      <ModalCodigo />
    </div>
  );
}

export default function App() {
  const catalogo = useEstado((s) => s.catalogo);
  const erroCarga = useEstado((s) => s.erroCarga);
  const tema = useEstado((s) => s.tema);

  useEffect(() => {
    document.documentElement.dataset.theme = tema;
  }, [tema]);

  useEffect(() => {
    const desligar = ligarEfeitos();
    useEstado.getState().iniciar();
    return desligar;
  }, []);

  if (erroCarga) {
    return (
      <div className="carregando-app">
        <div>
          <ServerCrash size={36} />
          <h2 style={{ color: "var(--texto)" }}>Não foi possível conectar ao servidor</h2>
          <p>
            Inicie a API com <code>python -m omveiculos</code> (pasta <code>OMVeiculos/backend</code>) e recarregue a página.
            <br />
            <small>{erroCarga}</small>
          </p>
          <button className="botao primario" onClick={() => useEstado.getState().iniciar()}>
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }
  if (!catalogo) {
    return (
      <div className="carregando-app">
        <div>
          <LoaderCircle size={28} className="girando" />
          <p>Carregando catálogo de blocos…</p>
        </div>
      </div>
    );
  }
  return (
    <ReactFlowProvider>
      <Area />
    </ReactFlowProvider>
  );
}
