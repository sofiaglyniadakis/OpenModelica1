// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import { ChevronDown, ChevronRight, Copy, FileUp, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { conversao, lerNumero, num, numEntrada, raioPneu } from "../lib/formato";
import { useEstado } from "../lib/store";
import type { Params, SpecParam, Valor } from "../lib/tipos";
import { IconeBloco } from "./Icone";

function visivel(spec: SpecParam, params: Params): boolean {
  if (!spec.visivel_se) return true;
  return Object.entries(spec.visivel_se).every(([k, vals]) => vals.includes(String(params[k])));
}

function CampoNumero({ spec, valor, aoMudar }: { spec: SpecParam; valor: Valor; aoMudar: (v: number) => void }) {
  const casas = spec.passo && spec.passo < 1 ? Math.min(4, Math.ceil(-Math.log10(spec.passo))) : 0;
  const formatar = (v: Valor) => numEntrada(Number(v), casas);
  const [texto, setTexto] = useState(formatar(valor));
  const [foco, setFoco] = useState(false);
  useEffect(() => {
    if (!foco) setTexto(formatar(valor));
  }, [valor, foco]); // eslint-disable-line
  const n = lerNumero(texto);
  const fora = n !== null && ((spec.min != null && n < spec.min) || (spec.max != null && n > spec.max));
  const confirmar = () => {
    setFoco(false);
    if (n === null) return setTexto(formatar(valor));
    let v = n;
    if (spec.min != null) v = Math.max(spec.min, v);
    if (spec.max != null) v = Math.min(spec.max, v);
    if (v !== Number(valor)) aoMudar(v);
    setTexto(formatar(v));
  };
  return (
    <div className={`entrada ${fora || n === null ? "invalida" : ""}`}>
      <input
        inputMode="decimal"
        value={texto}
        onFocus={() => setFoco(true)}
        onChange={(e) => {
          setTexto(e.target.value);
          const v = lerNumero(e.target.value);
          if (v !== null && !(spec.min != null && v < spec.min) && !(spec.max != null && v > spec.max)) aoMudar(v);
        }}
        onBlur={confirmar}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          if (e.key === "ArrowUp" || e.key === "ArrowDown") {
            e.preventDefault();
            const passo = (spec.passo ?? 1) * (e.shiftKey ? 10 : 1) * (e.key === "ArrowUp" ? 1 : -1);
            let v = Number((Number(valor) + passo).toFixed(6));
            if (spec.min != null) v = Math.max(spec.min, v);
            if (spec.max != null) v = Math.min(spec.max, v);
            aoMudar(v);
            setTexto(formatar(v));
          }
        }}
        aria-label={spec.rotulo}
      />
      {spec.unidade && <span className="unidade">{spec.unidade}</span>}
    </div>
  );
}

function CampoTexto({ valor, aoMudar, rotulo }: { valor: Valor; aoMudar: (v: string) => void; rotulo: string }) {
  return (
    <div className="entrada">
      <input value={String(valor ?? "")} onChange={(e) => aoMudar(e.target.value)} aria-label={rotulo} />
    </div>
  );
}

function CampoCSV({ valor, aoMudar }: { valor: Valor; aoMudar: (v: string) => void }) {
  const arquivo = useRef<HTMLInputElement>(null);
  return (
    <>
      <textarea className="area" value={String(valor ?? "")} onChange={(e) => aoMudar(e.target.value)} spellCheck={false} />
      <button className="botao" style={{ marginTop: 6 }} onClick={() => arquivo.current?.click()}>
        <FileUp size={15} /> Importar CSV
      </button>
      <input
        ref={arquivo}
        type="file"
        accept=".csv,.txt"
        hidden
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (f) aoMudar(await f.text());
          e.target.value = "";
        }}
      />
    </>
  );
}

function Campo({ spec, params, aoMudar }: { spec: SpecParam; params: Params; aoMudar: (v: Valor) => void }) {
  const valor = params[spec.chave] ?? spec.padrao;
  let extra: string | null = conversao(spec.unidade, valor);
  if (spec.chave === "pneu") {
    const r = raioPneu(String(valor));
    extra = r ? `raio dinâmico ${num(r * 1000, 0)} mm` : "medida inválida";
  }
  let controle;
  if (spec.tipo === "numero") controle = <CampoNumero spec={spec} valor={valor} aoMudar={aoMudar} />;
  else if (spec.tipo === "booleano")
    controle = (
      <label className="interruptor">
        <input type="checkbox" checked={Boolean(valor)} onChange={(e) => aoMudar(e.target.checked)} />
        <span className="trilho" />
        {valor ? "Sim" : "Não"}
      </label>
    );
  else if (spec.tipo === "selecao")
    controle =
      (spec.opcoes?.length ?? 0) <= 3 && spec.opcoes!.reduce((n, o) => n + o.rotulo.length, 0) <= 34 ? (
        <div className="segmentado largo">
          {spec.opcoes!.map((o) => (
            <button key={o.valor} className={String(valor) === o.valor ? "ativo" : ""} onClick={() => aoMudar(o.valor)}>
              {o.rotulo}
            </button>
          ))}
        </div>
      ) : (
        <select className="selecao" value={String(valor)} onChange={(e) => aoMudar(e.target.value)}>
          {spec.opcoes!.map((o) => (
            <option key={o.valor} value={o.valor}>
              {o.rotulo}
            </option>
          ))}
        </select>
      );
  else if (spec.tipo === "csv") controle = <CampoCSV valor={valor} aoMudar={aoMudar} />;
  else controle = <CampoTexto valor={valor} aoMudar={aoMudar} rotulo={spec.rotulo} />;

  return (
    <div className="campo">
      {spec.tipo !== "booleano" ? (
        <label>
          <span>{spec.rotulo}</span>
          {extra && <span className="conv">{extra}</span>}
        </label>
      ) : (
        <label>
          <span>{spec.rotulo}</span>
        </label>
      )}
      {controle}
      {spec.ajuda && <div className="ajuda">{spec.ajuda}</div>}
    </div>
  );
}

export function Inspetor() {
  const id = useEstado((s) => s.selecionado);
  const no = useEstado((s) => s.nodes.find((n) => n.id === s.selecionado));
  const bloco = useEstado((s) => (no ? s.blocos[no.data.tipo] : undefined));
  const avancados = useEstado((s) => s.mostrarAvancados);
  const { atualizarParam, renomear, remover, duplicar, aplicarPreset, alternarAvancados } = useEstado.getState();
  const [fechados, setFechados] = useState<Record<string, boolean>>({});

  const grupos = useMemo(() => {
    if (!bloco || !no) return [];
    const mapa = new Map<string, SpecParam[]>();
    for (const p of bloco.parametros) {
      if ((p.avancado && !avancados) || !visivel(p, no.data.params)) continue;
      if (!mapa.has(p.grupo)) mapa.set(p.grupo, []);
      mapa.get(p.grupo)!.push(p);
    }
    return [...mapa.entries()];
  }, [bloco, no, avancados]);

  if (!no || !bloco || !id) {
    return (
      <aside className="lateral direita">
        <div className="inspetor-vazio">
          <h3>Propriedades</h3>
          Selecione um bloco para editar seus parâmetros. As unidades seguem as fichas técnicas brasileiras (cv, kgfm, km/h) e
          aceitam vírgula decimal.
          <div className="atalhos">
            <kbd>Ctrl ↵</kbd> <span>Simular</span>
            <kbd>Ctrl Z</kbd> <span>Desfazer</span>
            <kbd>Ctrl ⇧ Z</kbd> <span>Refazer</span>
            <kbd>Ctrl D</kbd> <span>Duplicar bloco</span>
            <kbd>Del</kbd> <span>Remover seleção</span>
            <kbd>↑ ↓</kbd> <span>Ajustar número (⇧ = ×10)</span>
          </div>
        </div>
      </aside>
    );
  }

  const temAvancados = bloco.parametros.some((p) => p.avancado);
  return (
    <aside className="lateral direita">
      <div className="insp-cabeca">
        <div className="insp-titulo">
          <IconeBloco nome={bloco.icone} cor={bloco.cor} tamanho={34} />
          <input value={no.data.rotulo} onChange={(e) => renomear(id, e.target.value)} aria-label="Nome do bloco" />
        </div>
        <p className="insp-desc">{bloco.descricao}</p>
        <div className="insp-acoes">
          {bloco.presets.length > 1 && (
            <select
              className="selecao"
              value=""
              onChange={(e) => {
                if (e.target.value) aplicarPreset(id, e.target.value);
              }}
            >
              <option value="">Aplicar predefinição…</option>
              {bloco.presets.map((p) => (
                <option key={p.nome} value={p.nome}>
                  {p.nome}
                </option>
              ))}
            </select>
          )}
          <button className="botao icone" title="Duplicar (Ctrl D)" onClick={() => duplicar(id)}>
            <Copy size={15} />
          </button>
          <button className="botao icone perigo" title="Remover (Del)" onClick={() => remover([id])}>
            <Trash2 size={15} />
          </button>
        </div>
      </div>
      <div className="rolagem">
        {grupos.map(([nome, specs]) => (
          <div className="grupo" key={nome}>
            <button className="grupo-cabeca" onClick={() => setFechados((f) => ({ ...f, [nome]: !f[nome] }))}>
              {nome}
              {fechados[nome] ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
            </button>
            {!fechados[nome] && (
              <div className="grupo-corpo">
                {specs.map((s) => (
                  <Campo key={s.chave} spec={s} params={no.data.params} aoMudar={(v) => atualizarParam(id, s.chave, v)} />
                ))}
              </div>
            )}
          </div>
        ))}
        {temAvancados && (
          <div className="alternar-avancados">
            <label className="interruptor">
              <input type="checkbox" checked={avancados} onChange={alternarAvancados} />
              <span className="trilho" />
              Mostrar parâmetros de calibração
            </label>
          </div>
        )}
      </div>
    </aside>
  );
}
