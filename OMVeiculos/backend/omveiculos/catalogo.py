"""Catálogo de blocos do editor de workflow, predefinições e modelos de workflow.

A interface é gerada a partir deste catálogo (portas, formulários de
parâmetros, paleta e modelos prontos), de forma que um novo parâmetro precisa
ser declarado apenas aqui e na conversão de :mod:`omveiculos.workflow`.

Os veículos predefinidos são *arquétipos genéricos* de categorias comuns no
mercado brasileiro, e não reproduções de modelos comerciais específicos.
"""

from __future__ import annotations

__author__ = "Sofia Glyniadakis"

from copy import deepcopy

from . import ciclos
from .combustiveis import PRECOS_REFERENCIA

PORTAS = {
    "combustivel": {"nome": "Combustível", "cor": "#f59e0b"},
    "energia": {"nome": "Energia elétrica", "cor": "#22c55e"},
    "potencia": {"nome": "Potência mecânica", "cor": "#f43f5e"},
    "trem": {"nome": "Trem de força", "cor": "#a855f7"},
    "veiculo": {"nome": "Veículo", "cor": "#06b6d4"},
    "resultado": {"nome": "Resultados", "cor": "#3b82f6"},
}


def num(chave, rotulo, padrao, unidade="", minimo=None, maximo=None, passo=None, grupo="Geral",
        avancado=False, escala=1.0, ajuda="", visivel_se=None):
    return {
        "chave": chave, "rotulo": rotulo, "tipo": "numero", "padrao": padrao, "unidade": unidade,
        "min": minimo, "max": maximo, "passo": passo, "grupo": grupo, "avancado": avancado,
        "escala": escala, "ajuda": ajuda, "visivel_se": visivel_se,
    }


def sel(chave, rotulo, padrao, opcoes, grupo="Geral", ajuda="", visivel_se=None):
    return {
        "chave": chave, "rotulo": rotulo, "tipo": "selecao", "padrao": padrao,
        "opcoes": [{"valor": v, "rotulo": r} for v, r in opcoes], "grupo": grupo,
        "avancado": False, "ajuda": ajuda, "visivel_se": visivel_se,
    }


def boo(chave, rotulo, padrao, grupo="Geral", ajuda="", avancado=False, visivel_se=None):
    return {"chave": chave, "rotulo": rotulo, "tipo": "booleano", "padrao": padrao, "grupo": grupo,
            "avancado": avancado, "ajuda": ajuda, "visivel_se": visivel_se}


def txt(chave, rotulo, padrao, grupo="Geral", ajuda="", tipo="texto", visivel_se=None, avancado=False):
    return {"chave": chave, "rotulo": rotulo, "tipo": tipo, "padrao": padrao, "grupo": grupo,
            "avancado": avancado, "ajuda": ajuda, "visivel_se": visivel_se}


PCT = 0.01

BLOCOS = [
    {
        "tipo": "combustivel",
        "categoria": "Energia",
        "nome": "Combustível",
        "icone": "fuel",
        "cor": "#f59e0b",
        "descricao": "Combustível do mercado brasileiro. Conecte vários ao mesmo motor flex para comparar.",
        "entradas": [],
        "saidas": [{"id": "saida", "tipo": "combustivel", "rotulo": "Combustível"}],
        "parametros": [
            sel("tipo", "Combustível", "gasolina", [
                ("gasolina", "Gasolina C"), ("etanol", "Etanol hidratado (EHC)"),
                ("diesel", "Diesel S10 (B)"), ("gnv", "GNV")]),
            num("teor_etanol", "Etanol anidro na gasolina", 30, "% v/v", 0, 35, 1,
                ajuda="E30 desde 1/8/2025 (Lei 14.993/2024).", visivel_se={"tipo": ["gasolina"]}),
            num("teor_etanol_hidratado", "Teor alcoólico", 93.5, "% m/m", 92.5, 94.6, 0.1,
                ajuda="Faixa da especificação ANP: 92,5 a 94,6 % m/m.", visivel_se={"tipo": ["etanol"]}),
            num("teor_biodiesel", "Biodiesel no diesel", 15, "% v/v", 0, 25, 1,
                ajuda="B15 desde 1/8/2025.", visivel_se={"tipo": ["diesel"]}),
            num("preco", "Preço na bomba", PRECOS_REFERENCIA["gasolina"], "R$/unid.", 0, 20, 0.01,
                grupo="Custo", ajuda="Valor de referência - atualize com o preço do seu posto ou da ANP."),
        ],
        "presets": [
            {"nome": "Gasolina C (E30)", "params": {"tipo": "gasolina", "teor_etanol": 30, "preco": PRECOS_REFERENCIA["gasolina"]}},
            {"nome": "Etanol hidratado", "params": {"tipo": "etanol", "teor_etanol_hidratado": 93.5, "preco": PRECOS_REFERENCIA["etanol"]}},
            {"nome": "Diesel S10 (B15)", "params": {"tipo": "diesel", "teor_biodiesel": 15, "preco": PRECOS_REFERENCIA["diesel"]}},
            {"nome": "GNV", "params": {"tipo": "gnv", "preco": PRECOS_REFERENCIA["gnv"]}},
        ],
    },
    {
        "tipo": "bateria",
        "categoria": "Energia",
        "nome": "Bateria",
        "icone": "battery",
        "cor": "#22c55e",
        "descricao": "Bateria de tração. Em híbridos, define também a estratégia de uso da energia.",
        "entradas": [],
        "saidas": [{"id": "saida", "tipo": "energia", "rotulo": "Energia"}],
        "parametros": [
            num("capacidade", "Capacidade", 44.9, "kWh", 0.5, 200, 0.1),
            num("soc_inicial", "SOC inicial", 90, "%", 0, 100, 1),
            num("soc_min", "SOC mínimo", 10, "%", 0, 100, 1),
            num("soc_max", "SOC máximo", 95, "%", 0, 100, 1),
            num("eficiencia", "Eficiência carga/descarga", 96, "%", 50, 100, 0.5, escala=PCT, avancado=True),
            num("eficiencia_carregador", "Eficiência do carregador", 90, "%", 50, 100, 0.5, escala=PCT,
                ajuda="Perdas entre a tomada e a bateria.", avancado=True),
            num("preco_kwh", "Preço da energia", PRECOS_REFERENCIA["eletricidade"], "R$/kWh", 0, 5, 0.01, grupo="Custo"),
            num("fator_emissao", "Fator de emissão da rede", 40, "gCO₂/kWh", 0, 1000, 1, grupo="Custo",
                ajuda="Ordem de grandeza do fator médio do SIN (MCTI) em anos recentes - atualize."),
            num("v_max_eletrico", "Vel. máx. modo elétrico", 50, "km/h", 0, 200, 1, grupo="Estratégia híbrida"),
            num("p_max_eletrico", "Potência máx. modo elétrico", 12, "kW", 0, 200, 0.5, grupo="Estratégia híbrida"),
            num("soc_alvo", "SOC alvo", 55, "%", 0, 100, 1, grupo="Estratégia híbrida"),
            num("p_carga_max", "Recarga máx. pelo motor", 6, "kW", 0, 100, 0.5, grupo="Estratégia híbrida"),
        ],
        "presets": [
            {"nome": "44,9 kWh (compacto)", "params": {"capacidade": 44.9, "soc_inicial": 90, "soc_min": 10, "soc_max": 95}},
            {"nome": "60 kWh (SUV)", "params": {"capacidade": 60, "soc_inicial": 90, "soc_min": 10, "soc_max": 95}},
            {"nome": "1,3 kWh (híbrido)", "params": {"capacidade": 1.3, "soc_inicial": 55, "soc_min": 30, "soc_max": 80}},
        ],
    },
    {
        "tipo": "motor_combustao",
        "categoria": "Trem de força",
        "nome": "Motor a combustão",
        "icone": "engine",
        "cor": "#f43f5e",
        "descricao": "Motor flex, a gasolina ou diesel. Potência e torque como na ficha técnica (G/E).",
        "entradas": [{"id": "combustivel", "tipo": "combustivel", "rotulo": "Combustíveis", "multiplas": True}],
        "saidas": [{"id": "saida", "tipo": "potencia", "rotulo": "Potência"}],
        "parametros": [
            sel("tipo", "Tipo", "flex", [("flex", "Flex (gasolina/etanol)"), ("gasolina", "Somente gasolina"), ("diesel", "Diesel")]),
            num("cilindrada", "Cilindrada", 1.0, "L", 0.6, 6.0, 0.1),
            num("potencia_g", "Potência (gasolina/diesel)", 71, "cv", 20, 600, 1),
            num("potencia_e", "Potência (etanol)", 75, "cv", 20, 600, 1, visivel_se={"tipo": ["flex"]}),
            num("torque_g", "Torque (gasolina/diesel)", 10.0, "kgfm", 2, 100, 0.1),
            num("torque_e", "Torque (etanol)", 10.4, "kgfm", 2, 100, 0.1, visivel_se={"tipo": ["flex"]}),
            num("rpm_lenta", "Marcha lenta", 850, "rpm", 500, 1500, 10, grupo="Curva de torque"),
            num("rpm_torque_ini", "Torque máx. a partir de", 3500, "rpm", 800, 8000, 50, grupo="Curva de torque"),
            num("rpm_torque_fim", "Torque máx. até", 4000, "rpm", 800, 8000, 50, grupo="Curva de torque"),
            num("rpm_potencia", "Potência máx. a", 6200, "rpm", 1500, 9000, 50, grupo="Curva de torque"),
            num("rpm_max", "Rotação máxima", 6500, "rpm", 2000, 9500, 50, grupo="Curva de torque"),
            boo("start_stop", "Start-stop", False, grupo="Tecnologias"),
            boo("corte_combustivel", "Corte de injeção na desaceleração", True, grupo="Tecnologias"),
            num("eficiencia_indicada", "Eficiência indicada", 37, "%", 20, 55, 0.5, grupo="Calibração", avancado=True,
                escala=PCT, ajuda="Referência para gasolina sem etanol; o etanol aumenta conforme o ganho abaixo."),
            num("ganho_etanol", "Ganho de eficiência com etanol", 4, "%", 0, 15, 0.5, grupo="Calibração", avancado=True,
                escala=PCT, ajuda="Ganho relativo para 100 % de etanol (proporcional ao teor)."),
            num("fmep0", "Atrito FMEP₀", 0.97, "bar", 0, 5, 0.01, grupo="Calibração", avancado=True),
            num("fmep1", "Atrito FMEP₁", 0.15, "bar/krpm", 0, 2, 0.01, grupo="Calibração", avancado=True),
            num("fmep2", "Atrito FMEP₂", 0.05, "bar/krpm²", 0, 1, 0.01, grupo="Calibração", avancado=True),
            num("pmep0", "Bombeamento em carga nula", 0.6, "bar", 0, 2, 0.05, grupo="Calibração", avancado=True),
            num("rpm_corte", "Rotação mínima p/ corte", 1100, "rpm", 600, 3000, 50, grupo="Calibração", avancado=True),
            num("fator_gnv", "Potência com GNV", 85, "%", 50, 100, 1, grupo="Calibração", avancado=True, escala=PCT),
            num("inercia", "Inércia (motor + volante)", 0.15, "kg·m²", 0.01, 2, 0.01, grupo="Calibração", avancado=True,
                ajuda="Afeta a aceleração nas marchas baixas (ensaio de desempenho)."),
        ],
        "presets": [
            {"nome": "1.0 aspirado flex", "params": {"tipo": "flex", "cilindrada": 1.0, "potencia_g": 71, "potencia_e": 75, "torque_g": 10.0, "torque_e": 10.4, "rpm_torque_ini": 3500, "rpm_torque_fim": 4000, "rpm_potencia": 6200, "rpm_max": 6500}},
            {"nome": "1.0 turbo flex", "params": {"tipo": "flex", "cilindrada": 1.0, "potencia_g": 116, "potencia_e": 125, "torque_g": 16.8, "torque_e": 16.8, "rpm_torque_ini": 1750, "rpm_torque_fim": 3500, "rpm_potencia": 5500, "rpm_max": 6200, "eficiencia_indicada": 38, "pmep0": 0.45, "start_stop": True}},
            {"nome": "1.3 turbo flex", "params": {"tipo": "flex", "cilindrada": 1.3, "potencia_g": 176, "potencia_e": 185, "torque_g": 27.5, "torque_e": 27.5, "rpm_torque_ini": 1750, "rpm_torque_fim": 3500, "rpm_potencia": 5750, "rpm_max": 6250, "eficiencia_indicada": 38, "pmep0": 0.45, "start_stop": True}},
            {"nome": "1.6 aspirado flex", "params": {"tipo": "flex", "cilindrada": 1.6, "potencia_g": 110, "potencia_e": 117, "torque_g": 15.4, "torque_e": 16.1, "rpm_torque_ini": 3750, "rpm_torque_fim": 4250, "rpm_potencia": 5750, "rpm_max": 6300}},
            {"nome": "1.8 híbrido flex (Atkinson)", "params": {"tipo": "flex", "cilindrada": 1.8, "potencia_g": 98, "potencia_e": 101, "torque_g": 14.5, "torque_e": 14.5, "rpm_torque_ini": 3600, "rpm_torque_fim": 4000, "rpm_potencia": 5200, "rpm_max": 5600, "eficiencia_indicada": 40, "pmep0": 0.3}},
            {"nome": "2.8 turbodiesel", "params": {"tipo": "diesel", "cilindrada": 2.8, "potencia_g": 204, "potencia_e": 204, "torque_g": 51.0, "torque_e": 51.0, "rpm_lenta": 750, "inercia": 0.35, "rpm_torque_ini": 1600, "rpm_torque_fim": 2800, "rpm_potencia": 3400, "rpm_max": 4000, "eficiencia_indicada": 44, "fmep0": 1.2, "fmep1": 0.2, "fmep2": 0.06, "pmep0": 0.1, "rpm_corte": 1000}},
        ],
    },
    {
        "tipo": "motor_eletrico",
        "categoria": "Trem de força",
        "nome": "Motor elétrico",
        "icone": "zap",
        "cor": "#10b981",
        "descricao": "Motor de tração + inversor. Sozinho forma um elétrico; com motor a combustão, um híbrido.",
        "entradas": [{"id": "energia", "tipo": "energia", "rotulo": "Bateria"}],
        "saidas": [{"id": "saida", "tipo": "potencia", "rotulo": "Potência"}],
        "parametros": [
            num("potencia", "Potência de pico", 95, "cv", 5, 1000, 1),
            num("torque", "Torque de pico", 18.3, "kgfm", 1, 150, 0.1),
            num("rpm_max", "Rotação máxima", 12000, "rpm", 3000, 25000, 100),
            num("eficiencia", "Eficiência média (motor + inversor)", 90, "%", 50, 99, 0.5, escala=PCT),
            num("fracao_regeneracao", "Frenagem regenerativa", 70, "%", 0, 100, 1, escala=PCT,
                ajuda="Fração da energia de frenagem que pode ser recuperada."),
            num("v_min_regeneracao", "Vel. mínima de regeneração", 5, "km/h", 0, 30, 1, avancado=True),
            num("inercia", "Inércia do rotor", 0.04, "kg·m²", 0.0, 1, 0.005, avancado=True),
        ],
        "presets": [
            {"nome": "95 cv (compacto)", "params": {"potencia": 95, "torque": 18.3, "rpm_max": 12000}},
            {"nome": "72 cv (híbrido)", "params": {"potencia": 72, "torque": 16.6, "rpm_max": 13000}},
            {"nome": "204 cv (SUV)", "params": {"potencia": 204, "torque": 31.6, "rpm_max": 15000}},
        ],
    },
    {
        "tipo": "transmissao",
        "categoria": "Trem de força",
        "nome": "Transmissão",
        "icone": "gears",
        "cor": "#a855f7",
        "descricao": "Câmbio + diferencial. Recebe um motor a combustão, um elétrico ou ambos (híbrido).",
        "entradas": [{"id": "potencia", "tipo": "potencia", "rotulo": "Motores", "multiplas": True}],
        "saidas": [{"id": "saida", "tipo": "trem", "rotulo": "Trem de força"}],
        "parametros": [
            sel("tipo", "Tipo", "manual", [("manual", "Manual"), ("automatica", "Automática"), ("cvt", "CVT"), ("redutor", "Redutor fixo (elétrico)")]),
            txt("relacoes", "Relações das marchas", "3,73; 2,05; 1,32; 0,97; 0,76", tipo="lista",
                ajuda="Separe por ponto-e-vírgula. Para o redutor, informe 1.", visivel_se={"tipo": ["manual", "automatica", "redutor"]}),
            num("cvt_max", "Relação máxima (CVT)", 2.6, "", 0.5, 5, 0.01, visivel_se={"tipo": ["cvt"]}),
            num("cvt_min", "Relação mínima (CVT)", 0.4, "", 0.2, 2, 0.01, visivel_se={"tipo": ["cvt"]}),
            num("diferencial", "Diferencial", 4.07, "", 1, 15, 0.01),
            num("eficiencia", "Eficiência", 96, "%", 70, 100, 0.5, escala=PCT),
            num("rpm_troca_min", "Rotação de troca (carga baixa)", 1600, "rpm", 900, 5000, 50, grupo="Condução",
                ajuda="Rotação mínima após subir marcha em condução econômica."),
            num("rpm_troca_max", "Rotação de troca (carga plena)", 4500, "rpm", 1500, 8000, 50, grupo="Condução"),
            num("rpm_partida", "Rotação de arrancada", 3000, "rpm", 800, 6000, 50, grupo="Condução",
                ajuda="Usada no ensaio de desempenho (embreagem/conversor patinando)."),
        ],
        "presets": [
            {"nome": "Manual 5 marchas", "params": {"tipo": "manual", "relacoes": "3,73; 2,05; 1,32; 0,97; 0,76", "diferencial": 4.07, "eficiencia": 96, "rpm_troca_min": 1600, "rpm_partida": 3000}},
            {"nome": "Manual 6 marchas", "params": {"tipo": "manual", "relacoes": "3,73; 1,96; 1,32; 1,03; 0,82; 0,69", "diferencial": 4.06, "eficiencia": 96, "rpm_troca_min": 1600, "rpm_partida": 3000}},
            {"nome": "Automática 6 marchas", "params": {"tipo": "automatica", "relacoes": "4,46; 2,51; 1,56; 1,14; 0,85; 0,67", "diferencial": 3.68, "eficiencia": 93, "rpm_troca_min": 1300, "rpm_troca_max": 4500, "rpm_partida": 2400}},
            {"nome": "Automática 8 marchas", "params": {"tipo": "automatica", "relacoes": "4,71; 3,14; 2,11; 1,67; 1,29; 1,00; 0,84; 0,67", "diferencial": 3.42, "eficiencia": 92, "rpm_troca_min": 1200, "rpm_troca_max": 3200, "rpm_partida": 2000}},
            {"nome": "CVT", "params": {"tipo": "cvt", "cvt_min": 0.40, "cvt_max": 2.80, "diferencial": 5.0, "eficiencia": 92, "rpm_troca_min": 1300, "rpm_troca_max": 4500, "rpm_partida": 3500}},
            {"nome": "Redutor (elétrico)", "params": {"tipo": "redutor", "relacoes": "1", "diferencial": 9.6, "eficiencia": 97}},
        ],
    },
    {
        "tipo": "veiculo",
        "categoria": "Veículo",
        "nome": "Veículo",
        "icone": "car",
        "cor": "#06b6d4",
        "descricao": "Carroceria: massa, aerodinâmica, pneus e acessórios (inclusive ar-condicionado).",
        "entradas": [{"id": "trem", "tipo": "trem", "rotulo": "Trem de força"}],
        "saidas": [{"id": "saida", "tipo": "veiculo", "rotulo": "Veículo"}],
        "parametros": [
            num("massa", "Massa em ordem de marcha", 1000, "kg", 400, 4000, 5),
            num("carga", "Ocupantes e carga", 136, "kg", 0, 1500, 1, ajuda="Ensaios NBR 6601/7024 usam +136 kg."),
            txt("pneu", "Pneu", "175/65 R14", ajuda="Medida do pneu; o raio dinâmico é calculado."),
            sel("modo_resistencia", "Resistência ao movimento", "fisico", [("fisico", "Parâmetros físicos (Cd, A, Cr)"), ("coastdown", "Coast-down (F0, F1, F2)")], grupo="Resistências"),
            num("cd", "Coeficiente de arrasto (Cd)", 0.33, "", 0.15, 1.0, 0.005, grupo="Resistências", visivel_se={"modo_resistencia": ["fisico"]}),
            num("area_frontal", "Área frontal", 2.05, "m²", 1.0, 5.0, 0.01, grupo="Resistências", visivel_se={"modo_resistencia": ["fisico"]}),
            num("cr", "Coef. de rolamento (Cr)", 0.010, "", 0.004, 0.03, 0.0005, grupo="Resistências", visivel_se={"modo_resistencia": ["fisico"]}),
            num("f0", "F0", 110, "N", 0, 1000, 1, grupo="Resistências", visivel_se={"modo_resistencia": ["coastdown"]}),
            num("f1", "F1", 0.0, "N/(km/h)", -10, 10, 0.01, grupo="Resistências", visivel_se={"modo_resistencia": ["coastdown"]}),
            num("f2", "F2", 0.035, "N/(km/h)²", 0, 0.2, 0.0005, grupo="Resistências", visivel_se={"modo_resistencia": ["coastdown"]}),
            boo("ar_condicionado", "Ar-condicionado ligado", False, grupo="Acessórios"),
            num("potencia_ar", "Potência do ar-condicionado", 1500, "W", 0, 6000, 50, grupo="Acessórios"),
            num("potencia_acessorios", "Outros acessórios", 300, "W", 0, 3000, 10, grupo="Acessórios"),
            num("tanque", "Tanque", 47, "L ou m³", 0, 200, 1, grupo="Autonomia"),
            num("fator_inercia", "Inércia das partes girantes", 3, "% da massa", 0, 15, 0.5, grupo="Avançado", avancado=True, escala=PCT),
            num("fracao_eixo_motriz", "Peso no eixo motriz", 60, "%", 20, 100, 1, grupo="Avançado", avancado=True, escala=PCT,
                ajuda="Limita a tração no ensaio de desempenho."),
        ],
        "presets": [
            {"nome": "Hatch compacto", "params": {"massa": 1000, "pneu": "175/65 R14", "cd": 0.33, "area_frontal": 2.05, "cr": 0.010, "tanque": 47}},
            {"nome": "Sedã compacto", "params": {"massa": 1150, "pneu": "185/60 R15", "cd": 0.31, "area_frontal": 2.15, "cr": 0.0095, "tanque": 48}},
            {"nome": "SUV compacto", "params": {"massa": 1300, "pneu": "205/60 R16", "cd": 0.36, "area_frontal": 2.45, "cr": 0.0105, "tanque": 50}},
            {"nome": "Picape média", "params": {"massa": 2100, "pneu": "265/65 R17", "cd": 0.42, "area_frontal": 2.95, "cr": 0.011, "tanque": 80, "fracao_eixo_motriz": 45}},
            {"nome": "Elétrico compacto", "params": {"massa": 1405, "pneu": "205/50 R17", "cd": 0.30, "area_frontal": 2.3, "cr": 0.009, "tanque": 0, "fracao_eixo_motriz": 58}},
            {"nome": "Sedã híbrido", "params": {"massa": 1420, "pneu": "205/55 R16", "cd": 0.29, "area_frontal": 2.25, "cr": 0.009, "tanque": 43}},
        ],
    },
    {
        "tipo": "ensaio_pbev",
        "categoria": "Ensaios",
        "nome": "Ensaio PBEV",
        "icone": "badge",
        "cor": "#3b82f6",
        "descricao": "Consumo urbano (FTP-75, NBR 6601) + estrada (HWFET, NBR 7024) e combinado 55/45, como na etiqueta do Inmetro.",
        "entradas": [{"id": "veiculo", "tipo": "veiculo", "rotulo": "Veículos", "multiplas": True}],
        "saidas": [{"id": "saida", "tipo": "resultado", "rotulo": "Resultados"}],
        "parametros": [
            num("temperatura", "Temperatura", 25, "°C", -10, 50, 1, grupo="Ambiente"),
            num("altitude", "Altitude", 0, "m", 0, 3000, 10, grupo="Ambiente"),
        ],
        "presets": [{"nome": "Etiqueta Inmetro (PBEV)", "params": {}}],
    },
    {
        "tipo": "ciclo",
        "categoria": "Ensaios",
        "nome": "Ciclo de condução",
        "icone": "route",
        "cor": "#0ea5e9",
        "descricao": "Um ciclo isolado: FTP-75, HWFET, US06, velocidade constante ou seu próprio perfil (CSV).",
        "entradas": [{"id": "veiculo", "tipo": "veiculo", "rotulo": "Veículos", "multiplas": True}],
        "saidas": [{"id": "saida", "tipo": "resultado", "rotulo": "Resultados"}],
        "parametros": [
            sel("ciclo", "Ciclo", "ftp75", [(k, ciclos.NOMES[k]) for k in ("ftp75", "hwfet", "us06", "constante", "personalizado")]),
            num("velocidade_constante", "Velocidade", 100, "km/h", 10, 200, 1, visivel_se={"ciclo": ["constante"]}),
            num("duracao_constante", "Duração", 600, "s", 30, 7200, 10, visivel_se={"ciclo": ["constante"]}),
            txt("dados_personalizados", "Perfil (tempo_s; velocidade_kmh)", "0; 0\n10; 30\n40; 30\n60; 0", tipo="csv",
                ajuda="Cole ou importe um CSV com tempo (s) e velocidade (km/h).", visivel_se={"ciclo": ["personalizado"]}),
            num("temperatura", "Temperatura", 25, "°C", -10, 50, 1, grupo="Ambiente"),
            num("altitude", "Altitude", 0, "m", 0, 3000, 10, grupo="Ambiente"),
            num("inclinacao", "Inclinação da via", 0, "%", -15, 15, 0.5, grupo="Ambiente"),
        ],
        "presets": [
            {"nome": "Urbano FTP-75", "params": {"ciclo": "ftp75"}},
            {"nome": "Estrada HWFET", "params": {"ciclo": "hwfet"}},
            {"nome": "Agressivo US06", "params": {"ciclo": "us06"}},
            {"nome": "Rodovia a 110 km/h", "params": {"ciclo": "constante", "velocidade_constante": 110, "duracao_constante": 600}},
            {"nome": "Perfil personalizado", "params": {"ciclo": "personalizado"}},
        ],
    },
    {
        "tipo": "desempenho",
        "categoria": "Ensaios",
        "nome": "Desempenho",
        "icone": "gauge",
        "cor": "#6366f1",
        "descricao": "Aceleração plena: 0-100 km/h, retomada 80-120 km/h e velocidade máxima.",
        "entradas": [{"id": "veiculo", "tipo": "veiculo", "rotulo": "Veículos", "multiplas": True}],
        "saidas": [{"id": "saida", "tipo": "resultado", "rotulo": "Resultados"}],
        "parametros": [
            num("mu", "Atrito pneu-pista", 0.9, "", 0.3, 1.2, 0.05),
            num("temperatura", "Temperatura", 25, "°C", -10, 50, 1, grupo="Ambiente"),
            num("altitude", "Altitude", 0, "m", 0, 3000, 10, grupo="Ambiente"),
        ],
        "presets": [{"nome": "Aceleração 0-100 km/h", "params": {}}],
    },
    {
        "tipo": "painel",
        "categoria": "Análise",
        "nome": "Painel de resultados",
        "icone": "chart",
        "cor": "#2563eb",
        "descricao": "Reúne e compara resultados: consumo, custo mensal, CO₂ e a paridade etanol × gasolina.",
        "entradas": [{"id": "resultado", "tipo": "resultado", "rotulo": "Resultados", "multiplas": True}],
        "saidas": [],
        "parametros": [
            num("km_mes", "Quilometragem mensal", 1000, "km/mês", 0, 20000, 50),
        ],
        "presets": [{"nome": "Painel de resultados", "params": {}}],
    },
]

BLOCOS_POR_TIPO = {b["tipo"]: b for b in BLOCOS}


def parametros_padrao(tipo: str, preset: str | None = None) -> dict:
    bloco = BLOCOS_POR_TIPO[tipo]
    p = {s["chave"]: s["padrao"] for s in bloco["parametros"]}
    if preset is not None:
        for pr in bloco["presets"]:
            if pr["nome"] == preset:
                p.update(pr["params"])
                break
        else:
            raise KeyError(f"Predefinição '{preset}' não existe para o bloco '{tipo}'")
    return p


# --- Modelos de workflow -------------------------------------------------------


def _no(id_: str, tipo: str, preset: str | None, x: float, y: float, rotulo: str | None = None, **params) -> dict:
    p = parametros_padrao(tipo, preset)
    p.update(params)
    return {"id": id_, "tipo": tipo, "rotulo": rotulo or preset or BLOCOS_POR_TIPO[tipo]["nome"],
            "params": p, "posicao": {"x": x, "y": y}}


def _aresta(origem: str, destino: str, entrada: str) -> dict:
    return {"id": f"{origem}->{destino}:{entrada}", "origem": origem, "destino": destino, "entrada": entrada}


def _modelos() -> list[dict]:
    flex = {
        "id": "etanol-gasolina",
        "nome": "Etanol ou gasolina?",
        "descricao": "Hatch 1.0 flex no ensaio PBEV com os dois combustíveis e a paridade de preço.",
        "nos": [
            _no("gas", "combustivel", "Gasolina C (E30)", 0, 0),
            _no("eta", "combustivel", "Etanol hidratado", 0, 170),
            _no("mot", "motor_combustao", "1.0 aspirado flex", 290, 60),
            _no("cam", "transmissao", "Manual 5 marchas", 580, 60),
            _no("vei", "veiculo", "Hatch compacto", 870, 60, rotulo="Hatch 1.0 flex"),
            _no("pbev", "ensaio_pbev", "Etiqueta Inmetro (PBEV)", 1160, 60),
            _no("pai", "painel", "Painel de resultados", 1450, 60),
        ],
        "arestas": [
            _aresta("gas", "mot", "combustivel"), _aresta("eta", "mot", "combustivel"),
            _aresta("mot", "cam", "potencia"), _aresta("cam", "vei", "trem"),
            _aresta("vei", "pbev", "veiculo"), _aresta("pbev", "pai", "resultado"),
        ],
    }
    tecnologias = {
        "id": "flex-eletrico-hibrido",
        "nome": "Flex × híbrido × elétrico",
        "descricao": "Três arquiteturas no mesmo ensaio PBEV: consumo energético, custo por km e CO₂ do poço à roda.",
        "nos": [
            _no("eta", "combustivel", "Etanol hidratado", 0, 0),
            _no("mot", "motor_combustao", "1.0 turbo flex", 290, 0),
            _no("cam", "transmissao", "Automática 6 marchas", 580, 0),
            _no("vei", "veiculo", "Sedã compacto", 870, 0, rotulo="Sedã 1.0 turbo flex"),
            _no("eta2", "combustivel", "Etanol hidratado", 0, 230),
            _no("motH", "motor_combustao", "1.8 híbrido flex (Atkinson)", 290, 200),
            _no("batH", "bateria", "1,3 kWh (híbrido)", 0, 400),
            _no("emH", "motor_eletrico", "72 cv (híbrido)", 290, 400),
            _no("camH", "transmissao", "CVT", 580, 300),
            _no("veiH", "veiculo", "Sedã híbrido", 870, 300, rotulo="Sedã híbrido flex"),
            _no("bat", "bateria", "44,9 kWh (compacto)", 0, 600),
            _no("em", "motor_eletrico", "95 cv (compacto)", 290, 600),
            _no("red", "transmissao", "Redutor (elétrico)", 580, 600),
            _no("veiE", "veiculo", "Elétrico compacto", 870, 600),
            _no("pbev", "ensaio_pbev", "Etiqueta Inmetro (PBEV)", 1160, 300),
            _no("pai", "painel", "Painel de resultados", 1450, 300),
        ],
        "arestas": [
            _aresta("eta", "mot", "combustivel"), _aresta("mot", "cam", "potencia"), _aresta("cam", "vei", "trem"),
            _aresta("eta2", "motH", "combustivel"), _aresta("batH", "emH", "energia"),
            _aresta("motH", "camH", "potencia"), _aresta("emH", "camH", "potencia"), _aresta("camH", "veiH", "trem"),
            _aresta("bat", "em", "energia"), _aresta("em", "red", "potencia"), _aresta("red", "veiE", "trem"),
            _aresta("vei", "pbev", "veiculo"), _aresta("veiH", "pbev", "veiculo"), _aresta("veiE", "pbev", "veiculo"),
            _aresta("pbev", "pai", "resultado"),
        ],
    }
    desempenho = {
        "id": "desempenho",
        "nome": "Desempenho 0-100",
        "descricao": "SUV 1.3 turbo flex com gasolina e etanol: 0-100 km/h, retomada e velocidade máxima.",
        "nos": [
            _no("gas", "combustivel", "Gasolina C (E30)", 0, 0),
            _no("eta", "combustivel", "Etanol hidratado", 0, 170),
            _no("mot", "motor_combustao", "1.3 turbo flex", 290, 60),
            _no("cam", "transmissao", "Automática 6 marchas", 580, 60),
            _no("vei", "veiculo", "SUV compacto", 870, 60, rotulo="SUV 1.3 turbo flex"),
            _no("des", "desempenho", "Aceleração 0-100 km/h", 1160, 0),
            _no("pbev", "ensaio_pbev", "Etiqueta Inmetro (PBEV)", 1160, 180),
            _no("pai", "painel", "Painel de resultados", 1450, 60),
        ],
        "arestas": [
            _aresta("gas", "mot", "combustivel"), _aresta("eta", "mot", "combustivel"),
            _aresta("mot", "cam", "potencia"), _aresta("cam", "vei", "trem"),
            _aresta("vei", "des", "veiculo"), _aresta("vei", "pbev", "veiculo"),
            _aresta("des", "pai", "resultado"), _aresta("pbev", "pai", "resultado"),
        ],
    }
    ar = {
        "id": "ar-condicionado",
        "nome": "Calor e ar-condicionado",
        "descricao": "O mesmo hatch com e sem ar-condicionado no trânsito urbano a 35 °C.",
        "nos": [
            _no("gas", "combustivel", "Gasolina C (E30)", 0, 60),
            _no("mot", "motor_combustao", "1.0 aspirado flex", 290, 60),
            _no("cam", "transmissao", "Manual 5 marchas", 580, 60),
            _no("v1", "veiculo", "Hatch compacto", 870, 0, rotulo="Hatch sem ar"),
            _no("v2", "veiculo", "Hatch compacto", 870, 190, rotulo="Hatch com ar", ar_condicionado=True),
            _no("cic", "ciclo", "Urbano FTP-75", 1160, 60, temperatura=35),
            _no("pai", "painel", "Painel de resultados", 1450, 60),
        ],
        "arestas": [
            _aresta("gas", "mot", "combustivel"), _aresta("mot", "cam", "potencia"),
            _aresta("cam", "v1", "trem"), _aresta("cam", "v2", "trem"),
            _aresta("v1", "cic", "veiculo"), _aresta("v2", "cic", "veiculo"),
            _aresta("cic", "pai", "resultado"),
        ],
    }
    branco = {"id": "em-branco", "nome": "Em branco", "descricao": "Comece do zero arrastando blocos da paleta.",
              "nos": [], "arestas": []}
    return [flex, tecnologias, desempenho, ar, branco]


def catalogo() -> dict:
    return {
        "portas": PORTAS,
        "blocos": deepcopy(BLOCOS),
        "modelos": _modelos(),
        "ciclos": ciclos.catalogo(),
        "precos_referencia": PRECOS_REFERENCIA,
    }
