// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
package VeiculosLevesBR "Análise de consumo, emissões e desempenho de veículos leves no contexto brasileiro"
  extends Icones.Pacote;

  constant Real pi = 3.141592653589793;
  constant Real g(unit = "m/s2") = 9.80665 "aceleração da gravidade";
  constant Real cv(unit = "W") = 735.49875 "cavalo-vapor";
  constant Real kgfm(unit = "N.m") = 9.80665 "quilograma-força metro";

  annotation(
    version = "0.1.0",
    Documentation(info = "<html>
<p>Biblioteca autocontida (sem dependência da Modelica Standard Library) usada pelo
<b>OM Veículos Leves</b> como motor de simulação OpenModelica.</p>
<ul>
<li><b>Ciclos</b>: FTP-75 (ABNT NBR 6601), HWFET (ABNT NBR 7024), US06, velocidade constante e personalizado.</li>
<li><b>Dados</b>: registros de veículo, motor flex/diesel, motor elétrico, bateria, transmissão e
combustíveis brasileiros (gasolina C E30, etanol hidratado, diesel B15, GNV).</li>
<li><b>Experimentos</b>: veículo a combustão, elétrico e híbrido paralelo em ciclo de condução;
ensaio de desempenho (0-100 km/h, 80-120 km/h, velocidade máxima).</li>
</ul>
<p>Modelo quasi-estático: o veículo segue o perfil do ciclo; marcha/relação e o modo do híbrido
são decididos a cada 1 s (<code>sample</code>); vazão de combustível, energia e SOC são integrados
continuamente. As mesmas equações estão no motor rápido em Python
(<code>OMVeiculos/backend/omveiculos/simulador.py</code>).</p>
</html>"));
end VeiculosLevesBR;
