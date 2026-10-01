// Autora: Sofia Glyniadakis
// Criado em: 2026-10-01

import {
  BadgeCheck,
  BatteryCharging,
  Car,
  ChartColumn,
  Cog,
  Flame,
  Fuel,
  Gauge,
  Route,
  Zap,
  type LucideIcon,
} from "lucide-react";

const MAPA: Record<string, LucideIcon> = {
  fuel: Fuel,
  battery: BatteryCharging,
  engine: Flame,
  zap: Zap,
  gears: Cog,
  car: Car,
  badge: BadgeCheck,
  route: Route,
  gauge: Gauge,
  chart: ChartColumn,
};

export function IconeBloco({ nome, cor, tamanho = 30 }: { nome: string; cor: string; tamanho?: number }) {
  const I = MAPA[nome] ?? Cog;
  return (
    <span className="icone-bloco" style={{ background: cor, width: tamanho, height: tamanho }}>
      <I size={Math.round(tamanho * 0.55)} strokeWidth={2.2} />
    </span>
  );
}
