// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import { create } from "zustand";
import { api } from "./api";
import type { Bloco, Catalogo, Params, Resultado, Status, Valor, Workflow } from "./tipos";

export type DadosNo = { tipo: string; rotulo: string; params: Params };
export type NoBloco = Node<DadosNo, "bloco">;
type Motor = "rapido" | "openmodelica";
type Foto = { nodes: NoBloco[]; edges: Edge[] };

const CHAVE_WORKFLOW = "omveiculos.workflow.v1";
const CHAVE_PREFS = "omveiculos.prefs.v1";

function lerLocal<T>(chave: string): T | null {
  try {
    const t = localStorage.getItem(chave);
    return t ? (JSON.parse(t) as T) : null;
  } catch {
    return null;
  }
}

function gravarLocal(chave: string, valor: unknown) {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    /* armazenamento indisponível (modo privado etc.) */
  }
}

const novoId = (tipo: string) => `${tipo}-${Math.random().toString(36).slice(2, 8)}`;

interface Estado {
  catalogo: Catalogo | null;
  blocos: Record<string, Bloco>;
  status: Status | null;
  erroCarga: string | null;

  nodes: NoBloco[];
  edges: Edge[];
  selecionado: string | null;
  modeloAtual: string | null;

  resultado: Resultado | null;
  versao: number;
  versaoResultado: number;
  simulando: boolean;
  erroSimulacao: string | null;
  motor: Motor;
  aoVivo: boolean;
  tema: "escuro" | "claro";
  resultadosAbertos: boolean;
  mostrarAvancados: boolean;
  modalCodigo: boolean;

  passado: Foto[];
  futuro: Foto[];

  iniciar: () => Promise<void>;
  aplicarModelo: (id: string) => void;
  carregarWorkflow: (wf: Workflow, modeloId?: string | null) => void;
  paraWorkflow: () => Workflow;

  onNodesChange: (c: NodeChange<NoBloco>[]) => void;
  onEdgesChange: (c: EdgeChange[]) => void;
  conexaoValida: (c: Connection | Edge) => boolean;
  conectar: (c: Connection) => void;
  adicionarBloco: (tipo: string, preset: string | null, posicao: { x: number; y: number }) => string;
  atualizarParam: (id: string, chave: string, valor: Valor) => void;
  aplicarPreset: (id: string, preset: string) => void;
  renomear: (id: string, rotulo: string) => void;
  remover: (ids: string[]) => void;
  duplicar: (id: string) => void;
  selecionar: (id: string | null) => void;
  focar: (id: string) => void;
  registrarHistorico: () => void;
  desfazer: () => void;
  refazer: () => void;

  simular: () => Promise<void>;
  definirMotor: (m: Motor) => void;
  alternarAoVivo: () => void;
  alternarTema: () => void;
  abrirResultados: (aberto: boolean) => void;
  alternarAvancados: () => void;
  abrirCodigo: (aberto: boolean) => void;
}

let controlador: AbortController | null = null;
let ultimaEdicao = { chave: "", t: 0 };

export const useEstado = create<Estado>((set, get) => {
  const prefs = lerLocal<{ tema?: "escuro" | "claro"; aoVivo?: boolean }>(CHAVE_PREFS) ?? {};
  const temaInicial =
    prefs.tema ?? (typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: light)").matches ? "claro" : "escuro");

  function corPorta(tipoBloco: string): string {
    const { blocos, catalogo } = get();
    const porta = blocos[tipoBloco]?.saidas[0]?.tipo;
    return (porta && catalogo?.portas[porta]?.cor) || "#64748b";
  }

  function aresta(origem: string, destino: string, entrada: string, tipoOrigem: string, id?: string): Edge {
    return {
      id: id ?? `${origem}->${destino}:${entrada}`,
      source: origem,
      target: destino,
      sourceHandle: "saida",
      targetHandle: entrada,
      style: { stroke: corPorta(tipoOrigem), strokeWidth: 2 },
    };
  }

  function foto(): Foto {
    const { nodes, edges } = get();
    return { nodes: nodes.map((n) => ({ ...n, data: { ...n.data, params: { ...n.data.params } } })), edges: [...edges] };
  }

  function mudou(parcial: Partial<Estado> = {}) {
    set((s) => ({ ...parcial, versao: s.versao + 1, futuro: [] }));
  }

  return {
    catalogo: null,
    blocos: {},
    status: null,
    erroCarga: null,
    nodes: [],
    edges: [],
    selecionado: null,
    modeloAtual: null,
    resultado: null,
    versao: 0,
    versaoResultado: -1,
    simulando: false,
    erroSimulacao: null,
    motor: "rapido",
    aoVivo: prefs.aoVivo ?? true,
    tema: temaInicial,
    resultadosAbertos: false,
    mostrarAvancados: false,
    modalCodigo: false,
    passado: [],
    futuro: [],

    iniciar: async () => {
      try {
        const [catalogo, status] = await Promise.all([api.catalogo(), api.status().catch(() => null)]);
        const blocos = Object.fromEntries(catalogo.blocos.map((b) => [b.tipo, b]));
        set({ catalogo, blocos, status, erroCarga: null });
        const salvo = lerLocal<{ workflow: Workflow; modelo: string | null }>(CHAVE_WORKFLOW);
        if (salvo?.workflow?.nos?.every((n) => blocos[n.tipo])) {
          get().carregarWorkflow(salvo.workflow, salvo.modelo);
        } else {
          get().aplicarModelo(catalogo.modelos[0].id);
        }
      } catch (e) {
        set({ erroCarga: (e as Error).message });
      }
    },

    aplicarModelo: (id) => {
      const m = get().catalogo?.modelos.find((x) => x.id === id);
      if (!m) return;
      get().registrarHistorico();
      get().carregarWorkflow(m, m.id);
    },

    carregarWorkflow: (wf, modeloId = null) => {
      const { blocos } = get();
      const nodes: NoBloco[] = wf.nos
        .filter((n) => blocos[n.tipo])
        .map((n) => ({
          id: n.id,
          type: "bloco",
          position: { ...n.posicao },
          data: { tipo: n.tipo, rotulo: n.rotulo, params: { ...n.params } },
        }));
      const tipos = Object.fromEntries(nodes.map((n) => [n.id, n.data.tipo]));
      const edges = wf.arestas
        .filter((a) => tipos[a.origem] && tipos[a.destino])
        .map((a) => aresta(a.origem, a.destino, a.entrada, tipos[a.origem], a.id));
      mudou({ nodes, edges, selecionado: null, modeloAtual: modeloId });
    },

    paraWorkflow: () => {
      const { nodes, edges } = get();
      return {
        nos: nodes.map((n) => ({
          id: n.id,
          tipo: n.data.tipo,
          rotulo: n.data.rotulo,
          params: n.data.params,
          posicao: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
        })),
        arestas: edges.map((e) => ({ id: e.id, origem: e.source, destino: e.target, entrada: e.targetHandle ?? "" })),
      };
    },

    onNodesChange: (changes) => {
      const remocoes = changes.filter((c) => c.type === "remove");
      if (remocoes.length) get().registrarHistorico();
      const nodes = applyNodeChanges(changes, get().nodes);
      if (remocoes.length) {
        const ids = new Set(remocoes.map((c) => (c as { id: string }).id));
        const sel = get().selecionado;
        mudou({
          nodes,
          edges: get().edges.filter((e) => !ids.has(e.source) && !ids.has(e.target)),
          selecionado: sel && ids.has(sel) ? null : sel,
        });
      } else {
        set({ nodes });
      }
    },

    onEdgesChange: (changes) => {
      const remove = changes.some((c) => c.type === "remove");
      if (remove) get().registrarHistorico();
      const edges = applyEdgeChanges(changes, get().edges);
      if (remove) mudou({ edges });
      else set({ edges });
    },

    conexaoValida: (c) => {
      const { nodes, blocos } = get();
      if (!c.source || !c.target || c.source === c.target) return false;
      const origem = nodes.find((n) => n.id === c.source);
      const destino = nodes.find((n) => n.id === c.target);
      if (!origem || !destino) return false;
      const saida = blocos[origem.data.tipo]?.saidas[0];
      const entrada = blocos[destino.data.tipo]?.entradas.find((p) => p.id === c.targetHandle);
      return !!saida && !!entrada && saida.tipo === entrada.tipo;
    },

    conectar: (c) => {
      if (!get().conexaoValida(c)) return;
      const { nodes, edges, blocos } = get();
      const destino = nodes.find((n) => n.id === c.target)!;
      const origem = nodes.find((n) => n.id === c.source)!;
      const porta = blocos[destino.data.tipo].entradas.find((p) => p.id === c.targetHandle)!;
      if (edges.some((e) => e.source === c.source && e.target === c.target && e.targetHandle === c.targetHandle)) return;
      get().registrarHistorico();
      const restantes = porta.multiplas
        ? edges
        : edges.filter((e) => !(e.target === c.target && e.targetHandle === c.targetHandle));
      mudou({ edges: [...restantes, aresta(c.source, c.target, c.targetHandle!, origem.data.tipo)] });
    },

    adicionarBloco: (tipo, preset, posicao) => {
      const bloco = get().blocos[tipo];
      const params: Params = Object.fromEntries(bloco.parametros.map((p) => [p.chave, p.padrao]));
      const pr = preset ? bloco.presets.find((p) => p.nome === preset) : null;
      if (pr) Object.assign(params, pr.params);
      const id = novoId(tipo);
      const rotulo = pr && bloco.presets.length > 1 ? pr.nome : bloco.nome;
      get().registrarHistorico();
      const nodes = get().nodes.map((n) => (n.selected ? { ...n, selected: false } : n));
      mudou({
        nodes: [...nodes, { id, type: "bloco", position: posicao, selected: true, data: { tipo, rotulo, params } }],
        selecionado: id,
      });
      return id;
    },

    atualizarParam: (id, chave, valor) => {
      const agora = Date.now();
      const k = `${id}:${chave}`;
      if (ultimaEdicao.chave !== k || agora - ultimaEdicao.t > 1500) get().registrarHistorico();
      ultimaEdicao = { chave: k, t: agora };
      const { catalogo } = get();
      mudou({
        nodes: get().nodes.map((n) => {
          if (n.id !== id) return n;
          const params = { ...n.data.params, [chave]: valor };
          // ao trocar o tipo de combustível, acompanha o preço de referência se ele não foi editado
          if (n.data.tipo === "combustivel" && chave === "tipo" && catalogo) {
            const ref = catalogo.precos_referencia;
            const antigo = String(n.data.params.tipo);
            if (Number(n.data.params.preco) === ref[antigo]) params.preco = ref[String(valor)] ?? params.preco;
          }
          return { ...n, data: { ...n.data, params } };
        }),
      });
    },

    aplicarPreset: (id, preset) => {
      const n = get().nodes.find((x) => x.id === id);
      if (!n) return;
      const pr = get().blocos[n.data.tipo].presets.find((p) => p.nome === preset);
      if (!pr) return;
      get().registrarHistorico();
      mudou({
        nodes: get().nodes.map((x) =>
          x.id === id ? { ...x, data: { ...x.data, params: { ...x.data.params, ...pr.params } } } : x,
        ),
      });
    },

    renomear: (id, rotulo) => {
      const agora = Date.now();
      const k = `${id}:__rotulo`;
      if (ultimaEdicao.chave !== k || agora - ultimaEdicao.t > 1500) get().registrarHistorico();
      ultimaEdicao = { chave: k, t: agora };
      mudou({ nodes: get().nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, rotulo } } : n)) });
    },

    remover: (ids) => {
      if (!ids.length) return;
      get().registrarHistorico();
      const s = new Set(ids);
      mudou({
        nodes: get().nodes.filter((n) => !s.has(n.id)),
        edges: get().edges.filter((e) => !s.has(e.source) && !s.has(e.target)),
        selecionado: null,
      });
    },

    duplicar: (id) => {
      const n = get().nodes.find((x) => x.id === id);
      if (!n) return;
      get().registrarHistorico();
      const novo: NoBloco = {
        ...n,
        id: novoId(n.data.tipo),
        position: { x: n.position.x + 40, y: n.position.y + 40 },
        selected: true,
        data: { ...n.data, rotulo: `${n.data.rotulo} (cópia)`, params: { ...n.data.params } },
      };
      mudou({ nodes: [...get().nodes.map((x) => ({ ...x, selected: false })), novo], selecionado: novo.id });
    },

    selecionar: (id) => set({ selecionado: id }),
    focar: (id) => set({ selecionado: id, nodes: get().nodes.map((n) => ({ ...n, selected: n.id === id })) }),

    registrarHistorico: () => set((s) => ({ passado: [...s.passado.slice(-49), foto()], futuro: [] })),

    desfazer: () => {
      const { passado } = get();
      if (!passado.length) return;
      const anterior = passado[passado.length - 1];
      const atual = foto();
      set((s) => ({
        ...anterior,
        passado: s.passado.slice(0, -1),
        futuro: [atual, ...s.futuro],
        versao: s.versao + 1,
        selecionado: null,
      }));
    },

    refazer: () => {
      const { futuro } = get();
      if (!futuro.length) return;
      const proximo = futuro[0];
      const atual = foto();
      set((s) => ({ ...proximo, futuro: s.futuro.slice(1), passado: [...s.passado, atual], versao: s.versao + 1, selecionado: null }));
    },

    simular: async () => {
      controlador?.abort();
      const meu = new AbortController();
      controlador = meu;
      const versao = get().versao;
      set({ simulando: true, erroSimulacao: null });
      try {
        const resultado = await api.simular(get().paraWorkflow(), get().motor, meu.signal);
        if (controlador !== meu) return;
        const primeira = get().resultado === null;
        set({
          resultado,
          versaoResultado: versao,
          simulando: false,
          resultadosAbertos: get().resultadosAbertos || (primeira && resultado.cenarios.length > 0),
        });
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        set({ simulando: false, erroSimulacao: (e as Error).message });
      }
    },

    definirMotor: (motor) => set({ motor }),
    alternarAoVivo: () => {
      const aoVivo = !get().aoVivo;
      set({ aoVivo });
      gravarLocal(CHAVE_PREFS, { tema: get().tema, aoVivo });
    },
    alternarTema: () => {
      const tema = get().tema === "escuro" ? "claro" : "escuro";
      set({ tema });
      gravarLocal(CHAVE_PREFS, { tema, aoVivo: get().aoVivo });
    },
    abrirResultados: (aberto) => set({ resultadosAbertos: aberto }),
    alternarAvancados: () => set((s) => ({ mostrarAvancados: !s.mostrarAvancados })),
    abrirCodigo: (aberto) => set({ modalCodigo: aberto }),
  };
});

/** Salva o workflow no navegador e dispara a simulação "ao vivo" após alterações. */
export function ligarEfeitos() {
  let tSalvar: ReturnType<typeof setTimeout> | undefined;
  let tSimular: ReturnType<typeof setTimeout> | undefined;
  let assinaturaAnterior = "";
  return useEstado.subscribe((s, ant) => {
    if (s.nodes !== ant.nodes || s.edges !== ant.edges || s.modeloAtual !== ant.modeloAtual) {
      clearTimeout(tSalvar);
      tSalvar = setTimeout(() => gravarLocal(CHAVE_WORKFLOW, { workflow: s.paraWorkflow(), modelo: s.modeloAtual }), 400);
    }
    if (s.versao !== ant.versao && s.catalogo) {
      // posição dos blocos não altera o resultado: compara só a parte semântica
      const wf = s.paraWorkflow();
      const assinatura = JSON.stringify([wf.nos.map((n) => [n.id, n.tipo, n.rotulo, n.params]), wf.arestas]);
      if (assinatura === assinaturaAnterior) {
        // mudança sem efeito no cálculo: o resultado continua válido
        if (ant.versaoResultado === ant.versao) useEstado.setState({ versaoResultado: s.versao });
        return;
      }
      assinaturaAnterior = assinatura;
      if (s.aoVivo && s.motor === "rapido") {
        clearTimeout(tSimular);
        tSimular = setTimeout(() => useEstado.getState().simular(), 450);
      }
    }
  });
}

export const resultadoDesatualizado = (s: Estado) => s.resultado !== null && s.versaoResultado !== s.versao;
