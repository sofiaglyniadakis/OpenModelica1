// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Funcoes "Funções físicas compartilhadas pelos experimentos"
  extends Icones.Pacote;

  function densidadeAr "Densidade do ar seco pela atmosfera padrão (kg/m3)"
    extends Icones.Funcao;
    input Real temperatura "°C";
    input Real altitude "m";
    output Real rho;
  algorithm
    rho := 101325*(1 - 2.25577e-5*altitude)^5.25588/(287.05*(temperatura + 273.15));
  end densidadeAr;

  function forcas "Forças de rolamento, aerodinâmica e de rampa (N)"
    extends Icones.Funcao;
    input Real v "m/s";
    input Dados.Veiculo veiculo;
    input Real rho "kg/m3";
    input Real theta "rad";
    output Real fRol;
    output Real fAero;
    output Real fRampa;
  protected
    Real m;
    Real mov;
    Real vk;
  algorithm
    m := veiculo.massa + veiculo.carga;
    mov := if v > 1e-3 then 1 else 0;
    fRampa := m*g*sin(theta);
    if veiculo.modoResistencia == 2 then
      vk := v*3.6;
      fRol := mov*(veiculo.F0 + veiculo.F1*vk);
      fAero := veiculo.F2*vk*vk;
    else
      fRol := mov*veiculo.Cr*m*g*cos(theta);
      fAero := 0.5*rho*veiculo.Cd*veiculo.areaFrontal*v*v;
    end if;
  end forcas;

  function forcaResistencia "Soma das forças de resistência (N)"
    extends Icones.Funcao;
    input Real v;
    input Dados.Veiculo veiculo;
    input Real rho;
    input Real theta;
    output Real f;
  protected
    Real fRol;
    Real fAero;
    Real fRampa;
  algorithm
    (fRol, fAero, fRampa) := forcas(v, veiculo, rho, theta);
    f := fRol + fAero + fRampa;
  end forcaResistencia;

  function torqueMax "Curva de torque a plena carga do motor a combustão (N.m)"
    extends Icones.Funcao;
    input Real w "rad/s";
    input Dados.MotorCombustao motor;
    input Real pMax "W";
    input Real tMax "N.m";
    output Real t;
  protected
    Real rpm;
    Real r1;
    Real r2;
    Real rp;
    Real tP;
  algorithm
    rpm := min(max(w*30/pi, motor.rpmLenta), motor.rpmMax);
    r1 := max(motor.rpmTorqueIni, motor.rpmLenta + 1);
    r2 := max(motor.rpmTorqueFim, r1);
    rp := max(motor.rpmPotencia, r2 + 1);
    tP := pMax/(rp*pi/30);
    if rpm <= r1 then
      t := tMax*(0.55 + 0.45*(rpm - motor.rpmLenta)/(r1 - motor.rpmLenta));
    elseif rpm <= r2 then
      t := tMax;
    elseif rpm <= rp then
      t := tMax + (tP - tMax)*(rpm - r2)/(rp - r2);
    else
      t := tP*(1 - 0.6*(rpm - rp)/max(motor.rpmMax - rp, 1));
    end if;
    t := min(t, pMax/(rpm*pi/30));
  end torqueMax;

  function potenciaPerdas "Atrito + bombeamento (W)"
    extends Icones.Funcao;
    input Real w "rad/s";
    input Real carga "fração da carga plena";
    input Dados.MotorCombustao motor;
    output Real p;
  protected
    Real krpm;
    Real fmep;
    Real pmep;
  algorithm
    krpm := w*30/pi/1000;
    fmep := motor.fmep0 + motor.fmep1*krpm + motor.fmep2*krpm*krpm;
    pmep := motor.pmep0*(1 - min(max(carga, 0), 1));
    p := (fmep + pmep)*1e5*motor.cilindrada*1e-3*w/(4*pi);
  end potenciaPerdas;

  function potenciaCombustivel "Potência química do combustível (W) - linha de Willans"
    extends Icones.Funcao;
    input Real w "rad/s";
    input Real pEixo "W";
    input Real tMaxW "torque máximo na rotação w";
    input Real etaI "eficiência indicada";
    input Dados.MotorCombustao motor;
    output Real p;
  protected
    Real carga;
  algorithm
    carga := if tMaxW > 0 then pEixo/w/tMaxW else 0;
    p := max(pEixo + potenciaPerdas(w, carga, motor), 0)/etaI;
  end potenciaCombustivel;

  function torqueEletrico "Torque disponível do motor elétrico (N.m)"
    extends Icones.Funcao;
    input Real w "rad/s";
    input Dados.MotorEletrico eletrico;
    output Real t;
  algorithm
    if w > eletrico.rpmMax*pi/30 then
      t := 0;
    else
      t := min(eletrico.torqueMax, eletrico.potenciaMax/max(w, 1e-6));
    end if;
  end torqueEletrico;

  function escolherRelacao "Marcha (ou relação do CVT) para o intervalo de 1 s"
    extends Icones.Funcao;
    input Dados.Transmissao tr;
    input Dados.MotorCombustao motor;
    input Boolean usaMotor "false: veículo elétrico (usa a primeira relação)";
    input Boolean parado;
    input Real wRoda "rad/s";
    input Real pEntrada "potência na entrada da transmissão (W)";
    input Real pMax;
    input Real tMax;
    output Integer marcha;
    output Real rel "relação total (inclui diferencial)";
  protected
    Real frac;
    Real wAlvo;
    Real rMin;
    Real rMax;
    Real wE;
    Real wMax;
    Boolean achou;
  algorithm
    marcha := 1;
    rel := tr.relacoes[1]*tr.diferencial;
    if parado then
      marcha := 0;
      rel := 1;
    elseif tr.tipo == 4 or not usaMotor then
      marcha := 1;
      rel := tr.relacoes[1]*tr.diferencial;
    else
      frac := if pMax > 0 then min(max(pEntrada/pMax, 0), 1) else 0;
      wAlvo := (tr.rpmTrocaMin + (tr.rpmTrocaMax - tr.rpmTrocaMin)*frac)*pi/30;
      wMax := motor.rpmMax*pi/30;
      if tr.tipo == 3 then
        rMin := tr.cvtMin*tr.diferencial;
        rMax := tr.cvtMax*tr.diferencial;
        rel := if wRoda < 1e-3 then rMax else min(max(wAlvo/wRoda, rMin), rMax);
      else
        achou := false;
        for i in tr.nMarchas:-1:1 loop
          if not achou then
            wE := wRoda*tr.relacoes[i]*tr.diferencial;
            if wE >= wAlvo and wE <= wMax then
              if not (pEntrada > 0 and pEntrada/wE > 0.95*torqueMax(wE, motor, pMax, tMax)) then
                achou := true;
                marcha := i;
                rel := tr.relacoes[i]*tr.diferencial;
              end if;
            end if;
          end if;
        end for;
        if not achou then
          for i in 1:tr.nMarchas loop
            if not achou and wRoda*tr.relacoes[i]*tr.diferencial <= wMax then
              achou := true;
              marcha := i;
              rel := tr.relacoes[i]*tr.diferencial;
            end if;
          end for;
        end if;
        if not achou then
          marcha := tr.nMarchas;
          rel := tr.relacoes[tr.nMarchas]*tr.diferencial;
        end if;
      end if;
    end if;
  end escolherRelacao;

  function forcaTracaoMaxima "Força de tração máxima na roda (N) com troca de marcha ideal"
    extends Icones.Funcao;
    input Real v "m/s";
    input Integer arquitetura "1 combustão, 2 elétrico, 3 híbrido";
    input Dados.Veiculo veiculo;
    input Dados.Transmissao tr;
    input Dados.MotorCombustao motor;
    input Dados.MotorEletrico eletrico;
    input Real pMax;
    input Real tMax;
    input Real mu "coeficiente de atrito pneu-pista";
    output Real f;
  protected
    Real wRoda;
    Real rel;
    Real wIn;
    Real torque;
    Integer n;
    Boolean unica;
  algorithm
    wRoda := v/veiculo.raio;
    f := 0;
    unica := tr.tipo == 4 or tr.tipo == 3 or arquitetura == 2;
    n := if unica then 1 else tr.nMarchas;
    for i in 1:n loop
      if tr.tipo == 4 or arquitetura == 2 then
        rel := tr.relacoes[1]*tr.diferencial;
      elseif tr.tipo == 3 then
        rel := if wRoda < 1e-3 then tr.cvtMax*tr.diferencial else min(max(motor.rpmPotencia*pi/30/wRoda, tr.cvtMin*tr.diferencial), tr.cvtMax*tr.diferencial);
      else
        rel := tr.relacoes[i]*tr.diferencial;
      end if;
      wIn := wRoda*rel;
      if not (arquitetura <> 2 and wIn > motor.rpmMax*pi/30) then
        torque := 0;
        if arquitetura <> 2 then
          torque := torqueMax(max(wIn, tr.rpmPartida*pi/30), motor, pMax, tMax);
        end if;
        if arquitetura <> 1 then
          torque := torque + torqueEletrico(wIn, eletrico);
        end if;
        f := max(f, torque*rel*tr.eficiencia/veiculo.raio);
      end if;
    end for;
    f := min(f, mu*(veiculo.massa + veiculo.carga)*g*veiculo.fracaoEixoMotriz);
  end forcaTracaoMaxima;

  function aceleracaoMaxima "Aceleração plena (m/s2) na melhor marcha, com a inércia do motor refletida na roda"
    extends Icones.Funcao;
    input Real v "m/s";
    input Integer arquitetura "1 combustão, 2 elétrico, 3 híbrido";
    input Dados.Veiculo veiculo;
    input Dados.Transmissao tr;
    input Dados.MotorCombustao motor;
    input Dados.MotorEletrico eletrico;
    input Real pMax;
    input Real tMax;
    input Real mu;
    input Real rho;
    input Real theta;
    output Real a;
  protected
    Real wRoda;
    Real rel;
    Real wIn;
    Real torque;
    Real inercia;
    Real forca;
    Real aG;
    Real fRes;
    Real mEq;
    Real limite;
    Integer n;
    Boolean achou;
  algorithm
    wRoda := v/veiculo.raio;
    fRes := forcaResistencia(v, veiculo, rho, theta);
    mEq := (veiculo.massa + veiculo.carga)*(1 + veiculo.fatorInercia);
    limite := mu*(veiculo.massa + veiculo.carga)*g*veiculo.fracaoEixoMotriz;
    a := -fRes/mEq;
    achou := false;
    n := if tr.tipo == 4 or tr.tipo == 3 or arquitetura == 2 then 1 else tr.nMarchas;
    for i in 1:n loop
      if tr.tipo == 4 or arquitetura == 2 then
        rel := tr.relacoes[1]*tr.diferencial;
      elseif tr.tipo == 3 then
        rel := if wRoda < 1e-3 then tr.cvtMax*tr.diferencial else min(max(motor.rpmPotencia*pi/30/wRoda, tr.cvtMin*tr.diferencial), tr.cvtMax*tr.diferencial);
      else
        rel := tr.relacoes[i]*tr.diferencial;
      end if;
      wIn := wRoda*rel;
      if not (arquitetura <> 2 and wIn > motor.rpmMax*pi/30) then
        torque := 0;
        inercia := 0;
        if arquitetura <> 2 then
          torque := torqueMax(max(wIn, tr.rpmPartida*pi/30), motor, pMax, tMax);
          inercia := motor.inercia;
        end if;
        if arquitetura <> 1 then
          torque := torque + torqueEletrico(wIn, eletrico);
          inercia := inercia + eletrico.inercia;
        end if;
        forca := min(torque*rel*tr.eficiencia/veiculo.raio, limite);
        aG := (forca - fRes)/(mEq + inercia*(rel/veiculo.raio)^2);
        if not achou or aG > a then
          a := aG;
          achou := true;
        end if;
      end if;
    end for;
  end aceleracaoMaxima;

  function velocidadeMaxima "Velocidade máxima (km/h): equilíbrio entre tração e resistência"
    extends Icones.Funcao;
    input Integer arquitetura;
    input Dados.Veiculo veiculo;
    input Dados.Transmissao tr;
    input Dados.MotorCombustao motor;
    input Dados.MotorEletrico eletrico;
    input Real pMax;
    input Real tMax;
    input Real mu;
    input Real rho;
    input Real theta;
    output Real vMax;
  protected
    Real v;
    Real lo;
    Real hi;
    Real mid;
    Boolean fim;
  algorithm
    vMax := 0;
    if forcaTracaoMaxima(1, arquitetura, veiculo, tr, motor, eletrico, pMax, tMax, mu) - forcaResistencia(1, veiculo, rho, theta) <= 0 then
      vMax := 0;
    else
      v := 1;
      fim := false;
      while v < 120 and not fim loop
        v := v + 0.25;
        if forcaTracaoMaxima(v, arquitetura, veiculo, tr, motor, eletrico, pMax, tMax, mu) - forcaResistencia(v, veiculo, rho, theta) <= 0 then
          lo := v - 0.25;
          hi := v;
          for k in 1:40 loop
            mid := 0.5*(lo + hi);
            if forcaTracaoMaxima(mid, arquitetura, veiculo, tr, motor, eletrico, pMax, tMax, mu) - forcaResistencia(mid, veiculo, rho, theta) > 0 then
              lo := mid;
            else
              hi := mid;
            end if;
          end for;
          vMax := lo*3.6;
          fim := true;
        end if;
      end while;
      if not fim then
        vMax := v*3.6;
      end if;
    end if;
  end velocidadeMaxima;
end Funcoes;
