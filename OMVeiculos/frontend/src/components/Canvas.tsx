// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type OnSelectionChangeParams,
} from "@xyflow/react";
import { MousePointerClick } from "lucide-react";
import { useCallback, useEffect, useRef, type DragEvent } from "react";
import { useEstado, type NoBloco as TNoBloco } from "../lib/store";
import { NoBloco } from "./NoBloco";
import { MIME_BLOCO } from "./Paleta";

const tiposNo = { bloco: NoBloco };
const AJUSTE = { padding: 0.18, maxZoom: 1, duration: 350 };

export function Canvas() {
  const nodes = useEstado((s) => s.nodes);
  const edges = useEstado((s) => s.edges);
  const catalogo = useEstado((s) => s.catalogo);
  const blocos = useEstado((s) => s.blocos);
  const modeloAtual = useEstado((s) => s.modeloAtual);
  const simulando = useEstado((s) => s.simulando);
  const tema = useEstado((s) => s.tema);
  const { onNodesChange, onEdgesChange, conectar, conexaoValida, adicionarBloco, selecionar, registrarHistorico } =
    useEstado.getState();
  const { screenToFlowPosition, fitView } = useReactFlow();
  const ultimoModelo = useRef<string | null | undefined>(undefined);
  const usuarioMoveu = useRef(false);
  const caixa = useRef<HTMLDivElement>(null);

  // enquadra o fluxo ao carregar um modelo (não ao adicionar blocos depois)
  useEffect(() => {
    if (ultimoModelo.current === modeloAtual) return;
    ultimoModelo.current = modeloAtual;
    usuarioMoveu.current = useEstado.getState().nodes.length === 0;
    requestAnimationFrame(() => fitView(AJUSTE));
  }, [modeloAtual, fitView]);

  // reenquadra quando a área muda de tamanho (ex.: painel de resultados), se o usuário não moveu a vista
  useEffect(() => {
    if (!caixa.current) return;
    let t: ReturnType<typeof setTimeout> | undefined;
    const obs = new ResizeObserver(() => {
      clearTimeout(t);
      t = setTimeout(() => {
        if (!usuarioMoveu.current) fitView({ ...AJUSTE, duration: 200 });
      }, 120);
    });
    obs.observe(caixa.current);
    return () => {
      clearTimeout(t);
      obs.disconnect();
    };
  }, [fitView]);

  const aoSoltar = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      const bruto = e.dataTransfer.getData(MIME_BLOCO);
      if (!bruto) return;
      const { tipo, preset } = JSON.parse(bruto) as { tipo: string; preset: string | null };
      const pos = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      adicionarBloco(tipo, preset, { x: pos.x - 118, y: pos.y - 30 });
    },
    [screenToFlowPosition, adicionarBloco],
  );

  const aoSelecionar = useCallback(
    ({ nodes: sel }: OnSelectionChangeParams) => {
      const atual = useEstado.getState().selecionado;
      const novo = sel.length === 1 ? sel[0].id : sel.length ? atual : null;
      if (novo !== atual) selecionar(novo);
    },
    [selecionar],
  );

  return (
    <div ref={caixa} className={`canvas ${simulando ? "simulando" : ""}`} onDragOver={(e) => e.preventDefault()} onDrop={aoSoltar}>
      <ReactFlow<TNoBloco>
        nodes={nodes}
        edges={edges}
        nodeTypes={tiposNo}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={conectar}
        isValidConnection={conexaoValida}
        onSelectionChange={aoSelecionar}
        onNodeDragStart={() => registrarHistorico()}
        onMoveStart={(evento) => {
          if (evento) usuarioMoveu.current = true;
        }}
        colorMode={tema === "escuro" ? "dark" : "light"}
        deleteKeyCode={["Delete", "Backspace"]}
        defaultEdgeOptions={{ type: "default" }}
        connectionRadius={36}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
        fitView
        fitViewOptions={{ padding: 0.18, maxZoom: 1 }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1.4} color="var(--grade)" />
        <Controls showInteractive={false} position="bottom-left" />
        <MiniMap
          style={{ width: 170, height: 110 }}
          pannable
          zoomable
          position="bottom-right"
          nodeColor={(n) => blocos[(n as TNoBloco).data.tipo]?.cor ?? "#64748b"}
          nodeBorderRadius={6}
          maskColor={tema === "escuro" ? "rgba(11,15,23,0.65)" : "rgba(243,245,249,0.7)"}
        />
      </ReactFlow>
      {catalogo && (
        <div className="legenda-portas" aria-label="Tipos de conexão">
          {Object.entries(catalogo.portas).map(([k, p]) => (
            <span key={k}>
              <i style={{ background: p.cor }} />
              {p.nome}
            </span>
          ))}
        </div>
      )}
      {nodes.length === 0 && (
        <div className="vazio-canvas">
          <div>
            <MousePointerClick size={34} />
            <b>Área de trabalho vazia</b>
            Arraste blocos da paleta à esquerda ou escolha um modelo pronto em <i>Modelos</i>.
          </div>
        </div>
      )}
    </div>
  );
}
