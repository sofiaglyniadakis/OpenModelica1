// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  Check,
  ChevronDown,
  CodeXml,
  Cpu,
  Download,
  LayoutTemplate,
  LoaderCircle,
  Moon,
  Play,
  Redo2,
  Sun,
  Undo2,
  Upload,
  Zap,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useEstado } from "../lib/store";
import type { Workflow } from "../lib/tipos";

const ENSAIOS = ["ensaio_pbev", "ciclo", "desempenho"];

function Passos({ aoDestacar }: { aoDestacar: (cat: string | null) => void }) {
  const nodes = useEstado((s) => s.nodes);
  const edges = useEstado((s) => s.edges);
  const resultado = useEstado((s) => s.resultado);
  const feito = useMemo(() => {
    const tipo = Object.fromEntries(nodes.map((n) => [n.id, n.data.tipo]));
    const temEntrada = (t: string) => edges.some((e) => tipo[e.target] === t);
    return [
      temEntrada("veiculo") && temEntrada("transmissao"),
      ENSAIOS.some((t) => temEntrada(t)),
      temEntrada("painel") || temEntrada("exergia") || (resultado?.cenarios.length ?? 0) > 0,
    ];
  }, [nodes, edges, resultado]);
  const passos: [string, string][] = [
    ["Monte o veículo", "Trem de força"],
    ["Escolha o ensaio", "Ensaios"],
    ["Analise", "Análise"],
  ];
  return (
    <div className="passos" onMouseLeave={() => aoDestacar(null)}>
      {passos.map(([nome, cat], i) => (
        <span key={nome} style={{ display: "contents" }}>
          {i > 0 && <span className="passo-seta">›</span>}
          <button
            className={`passo ${feito[i] ? "feito" : ""}`}
            onMouseEnter={() => aoDestacar(cat)}
            onFocus={() => aoDestacar(cat)}
            title={`Blocos da categoria "${cat}" ficam destacados na paleta`}
          >
            <span className="bolinha">{feito[i] ? <Check size={13} strokeWidth={3} /> : i + 1}</span>
            {nome}
          </button>
        </span>
      ))}
    </div>
  );
}

function MenuModelos() {
  const modelos = useEstado((s) => s.catalogo?.modelos ?? []);
  const atual = useEstado((s) => s.modeloAtual);
  const { aplicarModelo, carregarWorkflow, paraWorkflow } = useEstado.getState();
  const [aberto, setAberto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const arquivo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fechar = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setAberto(false);
    };
    document.addEventListener("mousedown", fechar);
    return () => document.removeEventListener("mousedown", fechar);
  }, []);

  const exportar = () => {
    const blob = new Blob([JSON.stringify(paraWorkflow(), null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "workflow-omveiculos.json";
    a.click();
    URL.revokeObjectURL(a.href);
    setAberto(false);
  };

  return (
    <div className="menu" ref={ref}>
      <button className="botao" onClick={() => setAberto(!aberto)}>
        <LayoutTemplate size={16} /> Modelos <ChevronDown size={14} />
      </button>
      {aberto && (
        <div className="menu-lista">
          {modelos.map((m) => (
            <button
              key={m.id}
              className={`menu-item ${m.id === atual ? "ativo" : ""}`}
              onClick={() => {
                aplicarModelo(m.id);
                setAberto(false);
              }}
            >
              <b>{m.nome}</b>
              <span>{m.descricao}</span>
            </button>
          ))}
          <div className="menu-sep" />
          <button className="menu-item" onClick={exportar}>
            <b>
              <Download size={13} /> Exportar workflow (.json)
            </b>
          </button>
          <button className="menu-item" onClick={() => arquivo.current?.click()}>
            <b>
              <Upload size={13} /> Importar workflow…
            </b>
          </button>
          <input
            ref={arquivo}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={async (e) => {
              const f = e.target.files?.[0];
              e.target.value = "";
              if (!f) return;
              try {
                const wf = JSON.parse(await f.text()) as Workflow;
                if (!Array.isArray(wf.nos) || !Array.isArray(wf.arestas)) throw new Error();
                useEstado.getState().registrarHistorico();
                carregarWorkflow(wf, null);
                setAberto(false);
              } catch {
                alert("Arquivo de workflow inválido.");
              }
            }}
          />
        </div>
      )}
    </div>
  );
}

export function Topo({ aoDestacar }: { aoDestacar: (cat: string | null) => void }) {
  const motor = useEstado((s) => s.motor);
  const status = useEstado((s) => s.status);
  const simulando = useEstado((s) => s.simulando);
  const aoVivo = useEstado((s) => s.aoVivo);
  const tema = useEstado((s) => s.tema);
  const podeDesfazer = useEstado((s) => s.passado.length > 0);
  const podeRefazer = useEstado((s) => s.futuro.length > 0);
  const { simular, definirMotor, alternarAoVivo, alternarTema, desfazer, refazer, abrirCodigo } = useEstado.getState();
  const omc = status?.openmodelica;

  return (
    <header className="topo">
      <div className="marca">
        <div className="marca-logo">
          <Zap size={18} strokeWidth={2.5} />
        </div>
        <div className="marca-texto">
          <b>OM Veículos Leves</b>
          <span>OpenModelica · contexto brasileiro</span>
        </div>
      </div>
      <MenuModelos />
      <button className="botao icone fantasma" title="Desfazer (Ctrl Z)" disabled={!podeDesfazer} onClick={desfazer}>
        <Undo2 size={16} />
      </button>
      <button className="botao icone fantasma" title="Refazer (Ctrl ⇧ Z)" disabled={!podeRefazer} onClick={refazer}>
        <Redo2 size={16} />
      </button>
      <div className="topo-meio">
        <Passos aoDestacar={aoDestacar} />
      </div>
      <div className="topo-acoes">
        <button className="botao" onClick={() => abrirCodigo(true)} title="Ver o código Modelica gerado para os cenários">
          <CodeXml size={16} /> <span className="rotulo-largo">Modelica</span>
        </button>
        <div className="separador" />
        <div className="segmentado" role="radiogroup" aria-label="Motor de cálculo">
          <button
            className={motor === "rapido" ? "ativo" : ""}
            onClick={() => definirMotor("rapido")}
            title="Motor rápido em Python: resultados instantâneos"
          >
            <Zap size={14} /> Rápido
          </button>
          <button
            className={motor === "openmodelica" ? "ativo" : ""}
            onClick={() => definirMotor("openmodelica")}
            disabled={!omc?.disponivel}
            title={
              omc?.disponivel
                ? `Compila e simula com o OpenModelica (${omc.versao ?? "omc"})`
                : "OpenModelica (omc) não encontrado no servidor"
            }
          >
            <Cpu size={14} /> OpenModelica
          </button>
        </div>
        <label className="interruptor" title="Recalcular automaticamente a cada alteração (motor rápido)">
          <input type="checkbox" checked={aoVivo} onChange={alternarAoVivo} disabled={motor !== "rapido"} />
          <span className="trilho" />
          <span className="rotulo-largo">Ao vivo</span>
        </label>
        <button className="botao primario" onClick={() => simular()} disabled={simulando} title="Simular (Ctrl ↵)">
          {simulando ? <LoaderCircle size={16} className="girando" /> : <Play size={16} fill="currentColor" />}
          Simular
        </button>
        <button className="botao icone fantasma" onClick={alternarTema} title="Alternar tema claro/escuro">
          {tema === "escuro" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
