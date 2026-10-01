// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Dados "Registros de parâmetros (unidades SI, exceto onde indicado)"
  extends Icones.Pacote;

  record Veiculo "Carroceria e resistências ao movimento"
    extends Icones.Registro;
    parameter Real massa(unit = "kg") = 1050 "massa em ordem de marcha";
    parameter Real carga(unit = "kg") = 136 "ocupantes e carga (ensaio: +136 kg)";
    parameter Real fatorInercia = 0.03 "acréscimo de massa equivalente das partes girantes";
    parameter Integer modoResistencia = 1 "1: física (Cd, A, Cr); 2: coast-down (F0, F1, F2)";
    parameter Real Cd = 0.32 "coeficiente de arrasto";
    parameter Real areaFrontal(unit = "m2") = 2.1;
    parameter Real Cr = 0.011 "coeficiente de resistência ao rolamento";
    parameter Real F0(unit = "N") = 110;
    parameter Real F1 = 0 "N/(km/h)";
    parameter Real F2 = 0.035 "N/(km/h)^2";
    parameter Real raio(unit = "m") = 0.30 "raio dinâmico do pneu";
    parameter Real fracaoEixoMotriz = 0.6 "fração do peso sobre o eixo motriz";
    parameter Real potenciaAcessorios(unit = "W") = 300 "acessórios + ar-condicionado";
  end Veiculo;

  record Ambiente "Condições do ensaio"
    extends Icones.Registro;
    parameter Real temperatura(unit = "degC") = 25;
    parameter Real altitude(unit = "m") = 0;
    parameter Real inclinacao = 0 "inclinação da via (%)";
  end Ambiente;

  record Combustivel "Propriedades do combustível"
    extends Icones.Registro;
    parameter Real densidade(unit = "kg/l") = 0.7588;
    parameter Real pci(unit = "MJ/kg") = 38.28 "poder calorífico inferior";
    parameter Real fracaoEtanolVol = 0.30 "fração volumétrica de etanol";
    parameter Boolean classificacaoEtanol = false "usar potência/torque declarados para etanol (motor flex)";
    parameter Real fatorPotencia = 1.0 "potência relativa (ex.: GNV)";
  end Combustivel;

  record GasolinaC "Gasolina C com 30 % de etanol anidro (E30)"
    extends Combustivel(densidade = 0.7588, pci = 38.28, fracaoEtanolVol = 0.30);
  end GasolinaC;

  record EtanolHidratado "Etanol hidratado combustível (93,5 % m/m)"
    extends Combustivel(densidade = 0.8096, pci = 24.90, fracaoEtanolVol = 0.957, classificacaoEtanol = true);
  end EtanolHidratado;

  record DieselB15 "Diesel S10 com 15 % de biodiesel"
    extends Combustivel(densidade = 0.8460, pci = 41.76, fracaoEtanolVol = 0);
  end DieselB15;

  record GNV "Gás natural veicular (densidade em kg/m3)"
    extends Combustivel(densidade = 0.766, pci = 47.5, fracaoEtanolVol = 0, fatorPotencia = 0.85);
  end GNV;

  record MotorCombustao "Motor de combustão interna (modelo de Willans com atrito e bombeamento)"
    extends Icones.Registro;
    parameter Real cilindrada(unit = "l") = 1.0;
    parameter Real potenciaG(unit = "W") = 75*cv "potência máxima com gasolina C / diesel";
    parameter Real potenciaE(unit = "W") = 77*cv "potência máxima com etanol";
    parameter Real torqueG(unit = "N.m") = 10.0*kgfm;
    parameter Real torqueE(unit = "N.m") = 10.4*kgfm;
    parameter Real rpmLenta = 850;
    parameter Real rpmTorqueIni = 3500;
    parameter Real rpmTorqueFim = 4000;
    parameter Real rpmPotencia = 6000;
    parameter Real rpmMax = 6500;
    parameter Real eficienciaIndicada = 0.37 "referência gasolina sem etanol";
    parameter Real fmep0 = 0.97 "atrito (bar)";
    parameter Real fmep1 = 0.15 "atrito (bar/krpm)";
    parameter Real fmep2 = 0.05 "atrito (bar/krpm^2)";
    parameter Real pmep0 = 0.6 "bombeamento em carga nula (bar)";
    parameter Real ganhoEtanol = 0.04 "ganho relativo de eficiência por fração volumétrica de etanol";
    parameter Boolean startStop = false;
    parameter Boolean corteCombustivel = true "corte de injeção em desaceleração";
    parameter Real rpmCorte = 1100;
    parameter Real inercia(unit = "kg.m2") = 0.15 "motor + volante (ensaio de desempenho)";
  end MotorCombustao;

  record MotorEletrico "Motor elétrico + inversor"
    extends Icones.Registro;
    parameter Real potenciaMax(unit = "W") = 95*cv;
    parameter Real torqueMax(unit = "N.m") = 18.3*kgfm;
    parameter Real rpmMax = 12000;
    parameter Real eficiencia = 0.90 "eficiência média motor + inversor";
    parameter Real fracaoRegeneracao = 0.7 "fração da energia de frenagem recuperável";
    parameter Real vMinRegeneracao = 5 "km/h";
    parameter Real inercia(unit = "kg.m2") = 0.04 "rotor (ensaio de desempenho)";
  end MotorEletrico;

  record Bateria "Bateria de tração"
    extends Icones.Registro;
    parameter Real capacidade = 44.9 "kWh";
    parameter Real socInicial = 90 "%";
    parameter Real socMin = 10 "%";
    parameter Real socMax = 95 "%";
    parameter Real eficiencia = 0.96 "eficiência de carga/descarga";
    parameter Real eficienciaCarregador = 0.90 "tomada -> bateria";
  end Bateria;

  record Hibrido "Estratégia do híbrido paralelo (P2)"
    extends Icones.Registro;
    parameter Real vMaxEletrico = 50 "km/h, velocidade máxima no modo elétrico";
    parameter Real pMaxEletrico = 12 "kW, potência máxima no modo elétrico";
    parameter Real socAlvo = 55 "%";
    parameter Real pCargaMax = 6 "kW, recarga máxima pelo motor a combustão";
  end Hibrido;

  record Transmissao "Transmissão e diferencial"
    extends Icones.Registro;
    parameter Integer tipo = 1 "1 manual, 2 automática, 3 CVT, 4 redutor fixo";
    parameter Integer nMarchas = 5;
    parameter Real relacoes[10] = {3.73, 2.05, 1.32, 0.97, 0.76, 0, 0, 0, 0, 0};
    parameter Real diferencial = 4.07;
    parameter Real eficiencia = 0.96;
    parameter Real cvtMin = 0.40;
    parameter Real cvtMax = 2.60;
    parameter Real rpmTrocaMin = 1600 "rotação mínima após troca em carga baixa";
    parameter Real rpmTrocaMax = 4500 "rotação mínima após troca em carga plena";
    parameter Real rpmPartida = 1300 "rotação de arrancada no ensaio de desempenho";
  end Transmissao;
end Dados;
