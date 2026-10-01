"""Gera VeiculosLevesBR/Ciclos.mo a partir dos CSVs de ciclos do backend.

Uso:  python3 OMVeiculos/scripts/gerar_ciclos_modelica.py
"""

__author__ = "Sofia Glyniadakis"

from pathlib import Path
import sys

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

from omveiculos import ciclos  # noqa: E402

DESTINO = RAIZ / "modelica" / "VeiculosLevesBR" / "Ciclos.mo"


def vetor(nome: str, valores, descricao: str) -> str:
    itens = [f"{x:.4f}" for x in valores]
    linhas = [", ".join(itens[i:i + 10]) for i in range(0, len(itens), 10)]
    corpo = ",\n      ".join(linhas)
    return f'  constant Real {nome}[{len(itens)}](each unit="km/h") = {{\n      {corpo}}}\n    "{descricao}";\n'


def main() -> None:
    ftp = ciclos.obter("ftp75").v_kmh
    hw = ciclos.obter("hwfet").v_kmh
    us = ciclos.obter("us06").v_kmh
    texto = f'''// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Ciclos "Ciclos de condução a 1 Hz (km/h)"
  extends Icones.Pacote;

  // ARQUIVO GERADO por OMVeiculos/scripts/gerar_ciclos_modelica.py - não edite à mão.
  // Fonte: EPA Dynamometer Driver's Aid schedules (domínio público).

{vetor("FTP75", ftp, "Urbano FTP-75 (ABNT NBR 6601): UDDS + repetição dos primeiros 505 s")}
{vetor("HWFET", hw, "Estrada HWFET (ABNT NBR 7024)")}
{vetor("US06", us, "Agressivo US06")}
  function velocidade "Velocidade do ciclo (km/h) no instante inteiro k"
    extends Icones.Funcao;
    input Integer ciclo "1 FTP-75, 2 HWFET, 3 US06, 4 constante, 0 personalizado";
    input Integer k "instante (s)";
    input Real vConstante "km/h";
    input Real personalizado[:] "km/h a 1 Hz";
    output Real v "km/h";
  algorithm
    if ciclo == 1 then
      v := if k >= 0 and k < size(FTP75, 1) then FTP75[k + 1] else 0;
    elseif ciclo == 2 then
      v := if k >= 0 and k < size(HWFET, 1) then HWFET[k + 1] else 0;
    elseif ciclo == 3 then
      v := if k >= 0 and k < size(US06, 1) then US06[k + 1] else 0;
    elseif ciclo == 4 then
      v := vConstante;
    else
      v := if k >= 0 and k < size(personalizado, 1) then personalizado[k + 1] else 0;
    end if;
  end velocidade;

  function duracao "Duração do ciclo (s)"
    extends Icones.Funcao;
    input Integer ciclo;
    input Real duracaoConstante;
    input Integer nPersonalizado;
    output Real d;
  algorithm
    if ciclo == 1 then
      d := size(FTP75, 1) - 1;
    elseif ciclo == 2 then
      d := size(HWFET, 1) - 1;
    elseif ciclo == 3 then
      d := size(US06, 1) - 1;
    elseif ciclo == 4 then
      d := duracaoConstante;
    else
      d := nPersonalizado - 1;
    end if;
  end duracao;
end Ciclos;
'''
    DESTINO.write_text(texto, encoding="utf-8")
    print(f"escrito {DESTINO} ({len(ftp)}, {len(hw)}, {len(us)} pontos)")


if __name__ == "__main__":
    main()
