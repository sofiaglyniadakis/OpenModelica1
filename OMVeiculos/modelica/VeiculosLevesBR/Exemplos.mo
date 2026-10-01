// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Exemplos "Exemplos prontos para simular"
  extends Icones.Pacote;

  model HatchFlexEtanolUrbano "Hatch 1.0 flex com etanol no ciclo urbano FTP-75"
    extends Experimentos.CicloCombustao(
      ciclo = 1,
      veiculo(massa = 1000, Cd = 0.33, areaFrontal = 2.05, Cr = 0.010, raio = 0.2913),
      motor(cilindrada = 1.0, potenciaG = 71*cv, potenciaE = 75*cv, torqueG = 10.0*kgfm, torqueE = 10.4*kgfm, rpmPotencia = 6200),
      combustivel = Dados.EtanolHidratado());
    annotation(experiment(StopTime = 1874, Interval = 0.5));
  end HatchFlexEtanolUrbano;

  model EletricoCompactoEstrada "Elétrico compacto no ciclo estrada HWFET"
    extends Experimentos.CicloEletrico(
      ciclo = 2,
      veiculo(massa = 1405, Cd = 0.30, areaFrontal = 2.3, Cr = 0.009, raio = 0.317));
    annotation(experiment(StopTime = 765, Interval = 0.5));
  end EletricoCompactoEstrada;

  model HibridoFlexUrbano "Híbrido flex (paralelo) com gasolina C no FTP-75"
    extends Experimentos.CicloHibrido(
      ciclo = 1,
      veiculo(massa = 1420, Cd = 0.31, areaFrontal = 2.3, Cr = 0.009, raio = 0.317),
      motor(cilindrada = 1.8, potenciaG = 98*cv, potenciaE = 101*cv, torqueG = 14.5*kgfm, torqueE = 14.5*kgfm, rpmTorqueIni = 3600, rpmTorqueFim = 4000, rpmPotencia = 5200, rpmMax = 5600, eficienciaIndicada = 0.40, pmep0 = 0.3),
      eletrico(potenciaMax = 72*cv, torqueMax = 16.6*kgfm, rpmMax = 13000));
    annotation(experiment(StopTime = 1874, Interval = 0.5));
  end HibridoFlexUrbano;

  model DesempenhoHatch "0-100 km/h de um hatch 1.0 flex com gasolina"
    extends Experimentos.Desempenho(
      veiculo(massa = 1000, Cd = 0.33, areaFrontal = 2.05, Cr = 0.010, raio = 0.2913),
      motor(cilindrada = 1.0, potenciaG = 71*cv, potenciaE = 75*cv, torqueG = 10.0*kgfm, torqueE = 10.4*kgfm, rpmPotencia = 6200),
      transmissao(rpmPartida = 3000));
    annotation(experiment(StopTime = 30, Interval = 0.1));
  end DesempenhoHatch;
end Exemplos;
