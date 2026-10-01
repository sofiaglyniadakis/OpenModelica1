// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Experimentos "Modelos simuláveis (usados pelo OM Veículos Leves)"
  extends Icones.Pacote;

  partial model BaseCiclo "Base: veículo seguindo exatamente um ciclo de condução"
    extends Icones.Experimento;
    parameter Dados.Veiculo veiculo;
    parameter Dados.Transmissao transmissao;
    parameter Dados.Ambiente ambiente;
    parameter Integer ciclo = 1 "1 FTP-75, 2 HWFET, 3 US06, 4 constante, 0 personalizado";
    parameter Real vConstante = 100 "km/h (ciclo 4)";
    parameter Real duracaoConstante = 600 "s (ciclo 4)";
    parameter Real vPersonalizado[:] = {0, 0} "km/h a 1 Hz (ciclo 0)";
    final parameter Real rho = Funcoes.densidadeAr(ambiente.temperatura, ambiente.altitude);
    final parameter Real theta = atan(ambiente.inclinacao/100);
    final parameter Real mEq = (veiculo.massa + veiculo.carga)*(1 + veiculo.fatorInercia);
    final parameter Real duracao = Ciclos.duracao(ciclo, duracaoConstante, size(vPersonalizado, 1)) "s";
    final parameter Real etaT = transmissao.eficiencia;
    final parameter Real pAcc = veiculo.potenciaAcessorios;

    // decisões discretas, tomadas no início de cada intervalo de 1 s
    discrete Integer k(start = -1, fixed = true) "intervalo atual [k, k+1]";
    discrete Real tk(start = 0, fixed = true);
    discrete Real v0(start = 0, fixed = true) "velocidade no início do intervalo (m/s)";
    discrete Real v1(start = 0, fixed = true) "velocidade no fim do intervalo (m/s)";
    discrete Boolean parado(start = true, fixed = true);
    discrete Real vRep(start = 0, fixed = true) "velocidade média do intervalo (m/s)";
    discrete Real pRep(start = 0, fixed = true) "potência média estimada na roda (W)";
    discrete Real pEntRep(start = 0, fixed = true) "idem, na entrada da transmissão (W)";
    discrete Integer marcha(start = 0, fixed = true);
    discrete Real rel(start = 1, fixed = true) "relação total";

    Real v "m/s";
    Real a "m/s2";
    Real vKmh "km/h";
    Real fRol "N";
    Real fAero "N";
    Real fRampa "N";
    Real f "força de tração na roda (N)";
    Real pRoda "W";
    Real wIn "rotação na entrada da transmissão (rad/s)";
    Real distancia(start = 0, fixed = true) "m";
    Real eRol(start = 0, fixed = true) "J";
    Real eAero(start = 0, fixed = true) "J";
    Real eRampa(start = 0, fixed = true) "J";
    Real eFreio(start = 0, fixed = true) "J";
    // saídas comuns, definidas nos modelos derivados
    Real massaCombustivel(start = 0, fixed = true) "kg";
    Real energiaBateria(start = 0, fixed = true) "energia interna líquida retirada da bateria (J)";
    Real soc "%";
    Real rpm "rotação do motor a combustão";
    Real pIce "potência no eixo do motor a combustão (W)";
    Real pEm "potência mecânica do motor elétrico (W)";
    Real energiaMecanica(start = 0, fixed = true) "trabalho positivo do motor a combustão (J)";
    Real tempoExcedido(start = 0, fixed = true) "tempo em que a demanda excede o trem de força (s)";
  equation
    when {initial(), sample(1, 1)} then
      k = pre(k) + 1;
      tk = time;
      v0 = Ciclos.velocidade(ciclo, k, vConstante, vPersonalizado)/3.6;
      v1 = Ciclos.velocidade(ciclo, k + 1, vConstante, vPersonalizado)/3.6;
      parado = v0 < 0.1 and v1 < 0.1;
      vRep = 0.5*(v0 + v1);
      pRep = (mEq*(v1 - v0) + Funcoes.forcaResistencia(vRep, veiculo, rho, theta))*vRep;
      pEntRep = if pRep > 0 then pRep/etaT else pRep*etaT;
    end when;
    a = v1 - v0;
    v = v0 + a*(time - tk);
    vKmh = v*3.6;
    (fRol, fAero, fRampa) = Funcoes.forcas(v, veiculo, rho, theta);
    f = mEq*a + fRol + fAero + fRampa;
    pRoda = if parado then 0 else f*v;
    wIn = v/veiculo.raio*rel;
    der(distancia) = v;
    der(eRol) = if parado then 0 else fRol*v;
    der(eAero) = if parado then 0 else fAero*v;
    der(eRampa) = if parado then 0 else fRampa*v;
    der(eFreio) = noEvent(if not parado and f < 0 then -f*v else 0);
    annotation(Documentation(info = "<html>
<p>O perfil de velocidade é linear em cada intervalo de 1 s (aceleração constante). No início
de cada intervalo (<code>sample(1, 1)</code>) são calculadas as grandezas representativas usadas
pelas estratégias de troca de marcha e de gerenciamento do híbrido.</p></html>"));
  end BaseCiclo;

  model CicloCombustao "Veículo a combustão (flex, gasolina, diesel ou GNV) em ciclo de condução"
    extends BaseCiclo;
    parameter Dados.MotorCombustao motor;
    parameter Dados.Combustivel combustivel "padrão: gasolina C (E30)";
    final parameter Real pMax = if combustivel.classificacaoEtanol then motor.potenciaE else motor.potenciaG*combustivel.fatorPotencia;
    final parameter Real tMax = if combustivel.classificacaoEtanol then motor.torqueE else motor.torqueG*combustivel.fatorPotencia;
    final parameter Real etaI = motor.eficienciaIndicada*(1 + motor.ganhoEtanol*combustivel.fracaoEtanolVol);
    final parameter Real wLenta = motor.rpmLenta*pi/30;
    final parameter Real wCorte = motor.rpmCorte*pi/30;
    Real corte "1 quando há corte de injeção em desaceleração";
    Real wE "rotação do motor (rad/s)";
    Real tIn "torque na entrada da transmissão (N.m)";
    Real tDisp "torque disponível a plena carga (N.m)";
    Real pFuel "potência química do combustível (W)";
  equation
    when {initial(), sample(1, 1)} then
      (marcha, rel) = Funcoes.escolherRelacao(transmissao, motor, true, parado, vRep/veiculo.raio, pEntRep, pMax, tMax);
    end when;
    corte = noEvent(if not parado and f < 0 and motor.corteCombustivel and wIn >= wCorte then 1 else 0);
    wE = noEvent(if parado then (if motor.startStop then 0 else wLenta) elseif f >= 0 then max(wIn, wLenta) elseif corte > 0.5 then wIn else wLenta);
    tIn = noEvent(if not parado and f >= 0 then f*veiculo.raio/(rel*etaT) else 0);
    tDisp = Funcoes.torqueMax(max(wE, wLenta), motor, pMax, tMax);
    pIce = noEvent(if parado then (if motor.startStop then 0 else pAcc) elseif f >= 0 then tIn*wE + pAcc elseif corte > 0.5 then pRoda*etaT else pAcc);
    pFuel = noEvent(if (parado and motor.startStop) or corte > 0.5 then 0 else Funcoes.potenciaCombustivel(max(wE, wLenta), pIce, tDisp, etaI, motor));
    der(massaCombustivel) = pFuel/(combustivel.pci*1e6);
    der(energiaMecanica) = noEvent(max(pIce, 0));
    der(tempoExcedido) = noEvent(if not parado and f >= 0 and tIn > tDisp then 1 else 0);
    rpm = wE*30/pi;
    pEm = 0;
    soc = 0;
    der(energiaBateria) = 0;
    annotation(experiment(StopTime = 1874, Interval = 0.5));
  end CicloCombustao;

  model CicloEletrico "Veículo elétrico a bateria em ciclo de condução"
    extends BaseCiclo(transmissao(tipo = 4, nMarchas = 1, relacoes = {1, 0, 0, 0, 0, 0, 0, 0, 0, 0}, diferencial = 9.6, eficiencia = 0.97));
    parameter Dados.MotorEletrico eletrico;
    parameter Dados.Bateria bateria;
    Real tIn "N.m";
    Real pRegen "W";
    Real pEl "potência elétrica do motor (W)";
    Real pBat "potência nos terminais da bateria (W)";
    Real pInt "potência interna da bateria (W)";
  initial equation
    soc = bateria.socInicial;
  equation
    when {initial(), sample(1, 1)} then
      marcha = if parado then 0 else 1;
      rel = if parado then 1 else transmissao.relacoes[1]*transmissao.diferencial;
    end when;
    tIn = noEvent(if not parado and f >= 0 then f*veiculo.raio/(rel*etaT) else 0);
    pRegen = noEvent(if v*3.6 <= eletrico.vMinRegeneracao or soc >= bateria.socMax then 0 else max(max(pRoda*etaT*eletrico.fracaoRegeneracao, -eletrico.potenciaMax), -Funcoes.torqueEletrico(wIn, eletrico)*wIn));
    pEm = noEvent(if parado then 0 elseif f >= 0 then tIn*wIn else pRegen);
    pEl = noEvent(if pEm >= 0 then pEm/eletrico.eficiencia else pEm*eletrico.eficiencia);
    pBat = pEl + pAcc;
    pInt = noEvent(if pBat >= 0 then pBat/bateria.eficiencia else pBat*bateria.eficiencia);
    der(energiaBateria) = pInt;
    der(soc) = -pInt/(bateria.capacidade*3.6e6)*100;
    der(tempoExcedido) = noEvent(if not parado and f >= 0 and tIn > Funcoes.torqueEletrico(wIn, eletrico) then 1 else 0);
    rpm = 0;
    pIce = 0;
    der(massaCombustivel) = 0;
    der(energiaMecanica) = 0;
    annotation(experiment(StopTime = 1874, Interval = 0.5));
  end CicloEletrico;

  model CicloHibrido "Híbrido paralelo (P2) flex em ciclo de condução"
    extends BaseCiclo(transmissao(tipo = 3));
    parameter Dados.MotorCombustao motor;
    parameter Dados.Combustivel combustivel "padrão: gasolina C (E30)";
    parameter Dados.MotorEletrico eletrico;
    parameter Dados.Bateria bateria(capacidade = 1.3, socInicial = 55, socMin = 30, socMax = 80);
    parameter Dados.Hibrido hibrido;
    final parameter Real pMax = if combustivel.classificacaoEtanol then motor.potenciaE else motor.potenciaG*combustivel.fatorPotencia;
    final parameter Real tMax = if combustivel.classificacaoEtanol then motor.torqueE else motor.torqueG*combustivel.fatorPotencia;
    final parameter Real etaI = motor.eficienciaIndicada*(1 + motor.ganhoEtanol*combustivel.fracaoEtanolVol);
    final parameter Real wLenta = motor.rpmLenta*pi/30;
    discrete Boolean iceLigado(start = false, fixed = true) "motor a combustão ligado no intervalo";
    discrete Real pCarga(start = 0, fixed = true) "potência de recarga pedida ao motor a combustão (W)";
    Real tracaoIce "1 quando o motor a combustão traciona";
    Real tIn "N.m";
    Real wE "rad/s";
    Real tDisp "N.m";
    Real tEmDisp "N.m";
    Real tIce0 "N.m";
    Real tEm0 "N.m";
    Real tEm "N.m";
    Real tIce "N.m";
    Real pRegen "W";
    Real pEl "W";
    Real pBat "W";
    Real pInt "W";
    Real pFuel "W";
  initial equation
    soc = bateria.socInicial;
  equation
    when {initial(), sample(1, 1)} then
      (marcha, rel) = Funcoes.escolherRelacao(transmissao, motor, true, parado, vRep/veiculo.raio, pEntRep, pMax, tMax);
      iceLigado = not parado and pRep > 0 and not (soc > bateria.socMin and vRep*3.6 <= hibrido.vMaxEletrico and pEntRep <= hibrido.pMaxEletrico*1000);
      pCarga = if not parado and pRep > 0 then min(max((hibrido.socAlvo - soc)/10, 0), 1)*hibrido.pCargaMax*1000 else 0;
    end when;
    tIn = noEvent(if not parado and f >= 0 then f*veiculo.raio/(rel*etaT) else 0);
    tracaoIce = noEvent(if iceLigado and not parado and f >= 0 then 1 else 0);
    wE = noEvent(if tracaoIce > 0.5 then max(wIn, wLenta) else 0);
    tDisp = Funcoes.torqueMax(max(wE, wLenta), motor, pMax, tMax);
    tEmDisp = Funcoes.torqueEletrico(wIn, eletrico);
    tIce0 = noEvent(if tracaoIce > 0.5 then min(tIn + pCarga/max(wE, wLenta), tDisp) else 0);
    tEm0 = noEvent(if tracaoIce > 0.5 and tIn - tIce0 > 0 and soc <= bateria.socMin then 0 else tIn - tIce0);
    tEm = noEvent(if tracaoIce > 0.5 then max(tEm0, -tEmDisp) else tIn);
    tIce = tIn - tEm;
    pIce = noEvent(if tracaoIce > 0.5 then tIce*wE else 0);
    pFuel = noEvent(if tracaoIce > 0.5 then Funcoes.potenciaCombustivel(max(wE, wLenta), pIce, tDisp, etaI, motor) else 0);
    pRegen = noEvent(if v*3.6 <= eletrico.vMinRegeneracao or soc >= bateria.socMax then 0 else max(max(pRoda*etaT*eletrico.fracaoRegeneracao, -eletrico.potenciaMax), -tEmDisp*wIn));
    pEm = noEvent(if parado then 0 elseif f >= 0 then tEm*wIn else pRegen);
    pEl = noEvent(if pEm >= 0 then pEm/eletrico.eficiencia else pEm*eletrico.eficiencia);
    pBat = pEl + pAcc;
    pInt = noEvent(if pBat >= 0 then pBat/bateria.eficiencia else pBat*bateria.eficiencia);
    der(energiaBateria) = pInt;
    der(soc) = -pInt/(bateria.capacidade*3.6e6)*100;
    der(massaCombustivel) = pFuel/(combustivel.pci*1e6);
    der(energiaMecanica) = noEvent(max(pIce, 0));
    der(tempoExcedido) = noEvent(if not parado and f >= 0 and tEm0 > tEmDisp then 1 else 0);
    rpm = wE*30/pi;
    annotation(experiment(StopTime = 1874, Interval = 0.5));
  end CicloHibrido;

  model Desempenho "Aceleração plena: 0-100 km/h, 80-120 km/h e velocidade máxima"
    extends Icones.Experimento;
    parameter Integer arquitetura = 1 "1 combustão, 2 elétrico, 3 híbrido";
    parameter Dados.Veiculo veiculo;
    parameter Dados.Transmissao transmissao;
    parameter Dados.Ambiente ambiente;
    parameter Dados.MotorCombustao motor;
    parameter Dados.Combustivel combustivel "padrão: gasolina C (E30)";
    parameter Dados.MotorEletrico eletrico;
    parameter Real mu = 0.9 "atrito pneu-pista";
    final parameter Real rho = Funcoes.densidadeAr(ambiente.temperatura, ambiente.altitude);
    final parameter Real theta = atan(ambiente.inclinacao/100);
    final parameter Real pMax = if combustivel.classificacaoEtanol then motor.potenciaE else motor.potenciaG*combustivel.fatorPotencia;
    final parameter Real tMax = if combustivel.classificacaoEtanol then motor.torqueE else motor.torqueG*combustivel.fatorPotencia;
    Real v(start = 0, fixed = true) "m/s";
    Real vKmh "km/h";
    Real fMax "N";
    Real fRes "N";
    discrete Real t80(start = -1, fixed = true) "instante em que atinge 80 km/h";
    discrete Real t100(start = -1, fixed = true) "instante em que atinge 100 km/h";
    discrete Real t120(start = -1, fixed = true) "instante em que atinge 120 km/h";
    discrete Real vMaxKmh(start = 0, fixed = true) "velocidade máxima (km/h)";
  equation
    when initial() then
      vMaxKmh = Funcoes.velocidadeMaxima(arquitetura, veiculo, transmissao, motor, eletrico, pMax, tMax, mu, rho, theta);
    end when;
    fMax = Funcoes.forcaTracaoMaxima(v, arquitetura, veiculo, transmissao, motor, eletrico, pMax, tMax, mu);
    fRes = Funcoes.forcaResistencia(v, veiculo, rho, theta);
    der(v) = Funcoes.aceleracaoMaxima(v, arquitetura, veiculo, transmissao, motor, eletrico, pMax, tMax, mu, rho, theta);
    vKmh = v*3.6;
    when vKmh >= 80 then
      t80 = time;
    end when;
    when vKmh >= 100 then
      t100 = time;
    end when;
    when vKmh >= 120 then
      t120 = time;
    end when;
    annotation(experiment(StopTime = 90, Interval = 0.1));
  end Desempenho;
end Experimentos;
