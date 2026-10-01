// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

export type TipoParam = "numero" | "selecao" | "booleano" | "texto" | "lista" | "csv";
export type Valor = string | number | boolean;
export type Params = Record<string, Valor>;

export interface SpecParam {
  chave: string;
  rotulo: string;
  tipo: TipoParam;
  padrao: Valor;
  unidade?: string;
  min?: number | null;
  max?: number | null;
  passo?: number | null;
  grupo: string;
  avancado: boolean;
  escala?: number;
  ajuda?: string;
  visivel_se?: Record<string, string[]> | null;
  opcoes?: { valor: string; rotulo: string }[];
}

export interface Porta {
  id: string;
  tipo: string;
  rotulo: string;
  multiplas?: boolean;
}

export interface Bloco {
  tipo: string;
  categoria: string;
  nome: string;
  icone: string;
  cor: string;
  descricao: string;
  entradas: Porta[];
  saidas: Porta[];
  parametros: SpecParam[];
  presets: { nome: string; params: Params }[];
}

export interface NoWF {
  id: string;
  tipo: string;
  rotulo: string;
  params: Params;
  posicao: { x: number; y: number };
}

export interface ArestaWF {
  id?: string;
  origem: string;
  destino: string;
  entrada: string;
}

export interface Workflow {
  nos: NoWF[];
  arestas: ArestaWF[];
}

export interface ModeloWorkflow extends Workflow {
  id: string;
  nome: string;
  descricao: string;
}

export interface Catalogo {
  portas: Record<string, { nome: string; cor: string }>;
  blocos: Bloco[];
  modelos: ModeloWorkflow[];
  ciclos: { id: string; nome: string; duracao_s: number; distancia_km: number; v_media_kmh: number; v_max_kmh: number }[];
  precos_referencia: Record<string, number>;
}

export interface Status {
  versao: string;
  openmodelica: { disponivel: boolean; caminho: string | null; versao: string | null };
}

export interface Mensagem {
  no: string | null;
  mensagem: string;
}

export interface IndCiclo {
  ciclo: string;
  ciclo_nome: string;
  distancia_km: number;
  duracao_s: number;
  v_media_kmh: number;
  tempo_excedido_s: number;
  energias_mj: Record<string, number>;
  energetico: string;
  unidade: string;
  km_por_unidade: number;
  unidade_por_100km: number;
  mj_km: number;
  co2_fossil_g_km: number;
  co2_total_g_km: number;
  co2_wtw_g_km: number;
  custo_r_km: number;
  combustivel_total: number;
  eficiencia_media_motor?: number;
  rpm_medio?: number;
  soc_inicial?: number;
  soc_final?: number;
}

export interface IndCombinado {
  km_por_unidade: number | null;
  unidade_por_100km: number | null;
  mj_km: number | null;
  co2_fossil_g_km: number | null;
  co2_total_g_km: number | null;
  co2_wtw_g_km: number | null;
  custo_r_km: number | null;
  unidade: string;
  autonomia_km?: number | null;
}

export interface IndPBEV {
  urbano: IndCiclo;
  estrada: IndCiclo;
  combinado: IndCombinado;
  uso_real_estimado?: {
    urbano_km_por_unidade: number;
    estrada_km_por_unidade: number;
    combinado_km_por_unidade: number;
    metodo: string;
  };
}

export interface IndDesempenho {
  t_0_100_s: number | null;
  t_80_120_s: number | null;
  v_max_kmh: number;
  potencia_cv: number;
  peso_potencia_kg_cv: number | null;
}

export interface Serie {
  t: number[];
  v_kmh: number[];
  p_roda_kw?: number[];
  rpm?: number[];
  marcha?: number[];
  p_motor_kw?: number[];
  combustivel_acumulado?: number[];
  p_eletrico_kw?: number[];
  soc?: number[];
}

export interface Cenario {
  id: string;
  nome: string;
  ensaio_id: string;
  ensaio_tipo: "ensaio_pbev" | "ciclo" | "desempenho";
  ensaio_nome: string;
  veiculo_id: string;
  veiculo_nome: string;
  combustivel_id: string | null;
  energetico: string;
  arquitetura: "combustao" | "eletrico" | "hibrido";
  preco: number;
  indicadores: IndPBEV | { ciclo: IndCiclo } | IndDesempenho;
  series: Record<string, Serie>;
}

export interface Paridade {
  relacao_consumo: number;
  relacao_preco: number;
  compensa: "etanol" | "gasolina";
  preco_max_etanol: number;
  economia_mensal: number;
  veiculo: string;
  ensaio: string;
  cenario_gasolina: string;
  cenario_etanol: string;
}

export interface Painel {
  id: string;
  nome: string;
  km_mes: number;
  cenarios: string[];
  paridades: Paridade[];
}

export interface Resultado {
  motor: "rapido" | "openmodelica";
  tempo_s: number;
  erros: Mensagem[];
  avisos: Mensagem[];
  cenarios: Cenario[];
  paineis: Painel[];
}

export interface CodigoModelica {
  pacote: string;
  codigo: string;
  script: string;
  modelos: { nome: string; descricao: string }[];
  erros: Mensagem[];
}
