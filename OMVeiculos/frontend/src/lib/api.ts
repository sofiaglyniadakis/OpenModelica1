// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import type { Catalogo, CodigoModelica, Resultado, Status, Workflow } from "./tipos";

async function pedir<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) {
    let detalhe = `${r.status} ${r.statusText}`;
    try {
      const corpo = await r.json();
      if (corpo?.detail) detalhe = typeof corpo.detail === "string" ? corpo.detail : JSON.stringify(corpo.detail);
    } catch {
      /* corpo não é JSON */
    }
    throw new Error(detalhe);
  }
  return r.json() as Promise<T>;
}

export const api = {
  status: () => pedir<Status>("/api/status"),
  catalogo: () => pedir<Catalogo>("/api/catalogo"),
  simular: (workflow: Workflow, motor: "rapido" | "openmodelica", sinal?: AbortSignal) =>
    pedir<Resultado>("/api/simular", { method: "POST", body: JSON.stringify({ workflow, motor }), signal: sinal }),
  modelica: (workflow: Workflow) =>
    pedir<CodigoModelica>("/api/modelica", { method: "POST", body: JSON.stringify(workflow) }),
};
