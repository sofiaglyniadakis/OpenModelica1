// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

// Paleta categórica de referência (validada para daltonismo nos modos claro e escuro),
// atribuída em ordem fixa: a cor acompanha o cenário, nunca a posição no ranking.
const CLARO = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"];
const ESCURO = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"];

export function corSerie(indice: number, escuro: boolean): string {
  const p = escuro ? ESCURO : CLARO;
  return p[indice % p.length];
}

export const MAX_SERIES = CLARO.length;
