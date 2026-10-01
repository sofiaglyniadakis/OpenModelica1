// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01
within VeiculosLevesBR;
package Icones "Ícones da biblioteca"
  extends Pacote;

  partial package Pacote "Ícone de pacote"
    annotation(Icon(coordinateSystem(preserveAspectRatio = false, extent = {{-100, -100}, {100, 100}}), graphics = {
      Rectangle(lineColor = {14, 116, 144}, fillColor = {236, 254, 255}, fillPattern = FillPattern.Solid, extent = {{-100, -100}, {100, 100}}, radius = 25),
      Polygon(lineColor = {14, 116, 144}, fillColor = {6, 182, 212}, fillPattern = FillPattern.Solid, points = {{-70, -30}, {-60, 10}, {-30, 20}, {20, 20}, {50, 0}, {70, -5}, {70, -30}, {-70, -30}}),
      Ellipse(lineColor = {15, 23, 42}, fillColor = {15, 23, 42}, fillPattern = FillPattern.Solid, extent = {{-55, -45}, {-25, -15}}),
      Ellipse(lineColor = {15, 23, 42}, fillColor = {15, 23, 42}, fillPattern = FillPattern.Solid, extent = {{25, -45}, {55, -15}})}));
  end Pacote;

  partial function Funcao "Ícone de função"
    annotation(Icon(graphics = {
      Ellipse(lineColor = {14, 116, 144}, fillColor = {236, 254, 255}, fillPattern = FillPattern.Solid, extent = {{-100, -100}, {100, 100}}),
      Text(textColor = {14, 116, 144}, extent = {{-90, -60}, {90, 60}}, textString = "f")}));
  end Funcao;

  partial record Registro "Ícone de registro de dados"
    annotation(Icon(graphics = {
      Rectangle(lineColor = {14, 116, 144}, fillColor = {236, 254, 255}, fillPattern = FillPattern.Solid, extent = {{-100, -100}, {100, 100}}, radius = 10),
      Line(points = {{-100, 40}, {100, 40}}, color = {14, 116, 144}),
      Line(points = {{-100, -20}, {100, -20}}, color = {14, 116, 144}),
      Line(points = {{0, 100}, {0, -100}}, color = {14, 116, 144})}));
  end Registro;

  partial model Experimento "Ícone de experimento"
    annotation(Icon(graphics = {
      Rectangle(lineColor = {14, 116, 144}, fillColor = {255, 255, 255}, fillPattern = FillPattern.Solid, extent = {{-100, -100}, {100, 100}}, radius = 20),
      Polygon(lineColor = {6, 182, 212}, fillColor = {6, 182, 212}, fillPattern = FillPattern.Solid, points = {{-40, 60}, {60, 0}, {-40, -60}, {-40, 60}})}));
  end Experimento;
end Icones;
