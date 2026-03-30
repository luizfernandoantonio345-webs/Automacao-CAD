"""
n76_fluidos.py — Matriz de Fluidos Petrobras N-76
==================================================
Implementa a lógica de seleção automática de materiais conforme a norma
Petrobras N-76 (Especificações de Materiais para Tubulações Industriais),
aplicada à realidade da REGAP (Refinaria Gabriel Passos / Betim-MG).

Uso rápido:
    from engenharia_automacao.core.piping.n76_fluidos import obter_spec_fluido

    spec = obter_spec_fluido("Vapor de Baixa", temperatura_c=180.0)
    print(spec.material)          # ASTM A106 Gr.B
    print(spec.flange_classe)     # 150#
    print(spec.corrosao_allowance_mm)  # 1.6
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EspecificacaoFluido:
    """Especificação de tubulação derivada da N-76 para um fluido determinado."""
    fluido_normalizado: str          # nome canônico do fluido
    material: str                    # ex.: "ASTM A106 Gr.B"
    flange_classe: str               # ex.: "150#", "300#"
    face_flange: str                 # "RF" | "RTJ" | "FF"
    corrosao_allowance_mm: float     # sobre-espessura de corrosão [mm]
    isolamento_termico: bool         # requer isolamento por padrão?
    notas_n76: str                   # observações normativas aplicáveis


# ─────────────────────────────────────────────────────────────────────────────
# BASE DE DADOS DE FLUIDOS (N-76 / REGAP)
# Cada registro representa a especificação padrão para o fluido.
# CA = Corrosion Allowance.
# ─────────────────────────────────────────────────────────────────────────────
_FLUIDOS: dict[str, EspecificacaoFluido] = {

    # ── VAPOR ─────────────────────────────────────────────────────────────────
    "vapor de baixa": EspecificacaoFluido(
        fluido_normalizado="Vapor de Baixa (<= 10 bar / <= 200°C)",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=1.6,
        isolamento_termico=True,
        notas_n76=(
            "N-76 Tab.2 Linha VB: Aço carbono seamless para vapor de baixa pressão. "
            "Flange Class 150 RF com junta espiral metálica (SWG). "
            "Isolamento térmico obrigatório (lã de rocha 50mm + chapa alumínio)."
        ),
    ),

    "vapor de media pressao": EspecificacaoFluido(
        fluido_normalizado="Vapor de Média Pressão (11–42 bar / <=400°C)",
        material="ASTM A106 Gr.B",
        flange_classe="300#",
        face_flange="RF",
        corrosao_allowance_mm=1.6,
        isolamento_termico=True,
        notas_n76=(
            "N-76 Tab.2 Linha VM: Carbono ASTM A106-B; Flanges ASME Class 300 RF. "
            "Isolamento obrigatório (lã mineral 75mm). "
            "Suportar com guias anti-flambagem em trechos longos."
        ),
    ),

    "vapor de alta pressao": EspecificacaoFluido(
        fluido_normalizado="Vapor de Alta Pressão (> 42 bar / > 400°C)",
        material="ASTM A335 P11",
        flange_classe="600#",
        face_flange="RTJ",
        corrosao_allowance_mm=1.6,
        isolamento_termico=True,
        notas_n76=(
            "N-76 Tab.2 Linha VA: Liga Cr-Mo (P11) para alta temperatura. "
            "Flanges ASME Class 600 com anel RTJ. "
            "Pré-aquecimento para solda (PWHT obrigatório per N-133). "
            "Isolamento obrigatório 100mm + alumínio."
        ),
    ),

    # ── CONDENSADO / ÁGUA ────────────────────────────────────────────────────
    "condensado de vapor": EspecificacaoFluido(
        fluido_normalizado="Condensado de Vapor",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76: CA 3 mm padrão REGAP por condensação ácida. "
            "Purgadores tipo boia ou bimetálico conforme N-58."
        ),
    ),

    "agua de processo": EspecificacaoFluido(
        fluido_normalizado="Água de Processo",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76="N-76: CA 3 mm padrão. Inspecionar por ultrassom a cada 3 anos.",
    ),

    "agua acida": EspecificacaoFluido(
        fluido_normalizado="Água Ácida (Sour Water)",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=6.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76 Tab.3 Linha WS: Água ácida com H₂S. CA mínima 6 mm. "
            "Obrigatório controle de dureza (HRC ≤ 22, HB ≤ 237) per NACE MR-0175. "
            "Evitar material sensitizado para HIC (Hydrogen-Induced Cracking). "
            "Flanges 150# RF com junta espiral inox 316L."
        ),
    ),

    "agua cloretada": EspecificacaoFluido(
        fluido_normalizado="Água Cloretada / Salmoura",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=6.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76: CA 6 mm por ataque por cloretos. "
            "Avaliar revestimento interno por pintura epóxi (N-2630). "
            "Alternativa: duplex SS 2205 para serviço severo."
        ),
    ),

    # ── HIDROCARBONETOS ───────────────────────────────────────────────────────
    "gasolina": EspecificacaoFluido(
        fluido_normalizado="Gasolina / Nafta",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76 Tab.1 HC-Leve: Flanges 150# RF com junta espiral SWG SS316. "
            "Vedação conforme API 650 / N-68. "
            "ISBL: Linha de tancagem conforme N-2630."
        ),
    ),

    "oleo diesel": EspecificacaoFluido(
        fluido_normalizado="Óleo Diesel / Gasóleo",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76 Tab.1 HC-Médio: ASTM A106-B com CA 3mm. "
            "Flanges 150# RF. Para T > 200°C usar Class 300."
        ),
    ),

    "oleo combustivel": EspecificacaoFluido(
        fluido_normalizado="Óleo Combustível (OC / Resíduo Atmosférico)",
        material="ASTM A106 Gr.B",
        flange_classe="300#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=True,
        notas_n76=(
            "N-76 Tab.1 HC-Pesado: Isolamento obrigatório (tracing a vapor + lã mineral). "
            "Flanges 300# por viscosidade e temperatura elevada. "
            "Verificar naphtenic acid corrosion: se TAN > 0.5 mgKOH/g, TI = SS316."
        ),
    ),

    "petroleo cru": EspecificacaoFluido(
        fluido_normalizado="Petróleo Cru / Crude Oil",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76: CA 3 mm; fluido com H₂S avaliar NACE MR-0175. "
            "Pigging obrigatório em trechos longos conforme N-1630."
        ),
    ),

    "hidrocarboneto leve gasoso": EspecificacaoFluido(
        fluido_normalizado="Hidrocarboneto Leve Gasoso (GLP / GN)",
        material="ASTM A106 Gr.B",
        flange_classe="300#",
        face_flange="RTJ",
        corrosao_allowance_mm=1.6,
        isolamento_termico=False,
        notas_n76=(
            "N-76 / ASME B31.3: Flanges 300# RTJ (serviço flamável). "
            "Classe de fluido B (flamável); inspeção de solda 100% RT por N-113."
        ),
    ),

    "hidrocarboneto": EspecificacaoFluido(
        fluido_normalizado="Hidrocarboneto (Genérico)",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76="N-76: espeficação genérica. Refine o fluido para precisão.",
    ),

    # ── AMINAS / CORROSIVOS ───────────────────────────────────────────────────
    "amina mea dea mdea": EspecificacaoFluido(
        fluido_normalizado="Amina (MEA / DEA / MDEA)",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=3.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76: CA 3 mm; PWHT obrigatório (alivia tensões residuais que catalisam "
            "trincamento por aminas — SCC). Temperatura máxima de operação 130°C."
        ),
    ),

    "acido sulfurico": EspecificacaoFluido(
        fluido_normalizado="Ácido Sulfúrico (H₂SO₄)",
        material="ASTM A53 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=6.0,
        isolamento_termico=False,
        notas_n76=(
            "N-76 Tab.4: CA 6mm; aço carbono adequado apenas p/ conc. > 98%. "
            "Para concentrações intermediárias: liga liga C-276. "
            "Velocidade < 0.3 m/s (erosão-corrosão). Flanges 150# FF com junta PTFE."
        ),
    ),

    "gas combustivel": EspecificacaoFluido(
        fluido_normalizado="Gás Combustível (Fuel Gas)",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RTJ",
        corrosao_allowance_mm=1.6,
        isolamento_termico=False,
        notas_n76=(
            "N-76: serviço tipo 'flamável gasoso'. "
            "Classe B ASME B31.3; inspeção RT/UT em 100% das soldas de campo."
        ),
    ),

    "nitrogenio": EspecificacaoFluido(
        fluido_normalizado="Nitrogênio (N₂) / Instrumentação",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=0.0,
        isolamento_termico=False,
        notas_n76="N-76: fluido não corrosivo. CA 0 mm. Limpeza conforme N-2410.",
    ),

    "ar para instrumentos": EspecificacaoFluido(
        fluido_normalizado="Ar para Instrumentos / Ar de Serviço",
        material="ASTM A106 Gr.B",
        flange_classe="150#",
        face_flange="RF",
        corrosao_allowance_mm=0.0,
        isolamento_termico=False,
        notas_n76="N-76: fluido limpo, não corrosivo. CA 0 mm.",
    ),
}

# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

_ALIAS: dict[str, str] = {
    # Atalhos e variações de nomenclatura de campo
    "vb": "vapor de baixa",
    "vapor baixa": "vapor de baixa",
    "low pressure steam": "vapor de baixa",
    "vm": "vapor de media pressao",
    "vapor media": "vapor de media pressao",
    "va": "vapor de alta pressao",
    "vapor alta": "vapor de alta pressao",
    "high pressure steam": "vapor de alta pressao",
    "condensado": "condensado de vapor",
    "agua": "agua de processo",
    "water": "agua de processo",
    "agua acida": "agua acida",
    "sour water": "agua acida",
    "agua cloretada": "agua cloretada",
    "salmoura": "agua cloretada",
    "brine": "agua cloretada",
    "nafta": "gasolina",
    "naphtha": "gasolina",
    "diesel": "oleo diesel",
    "gasoleo": "oleo diesel",
    "oc": "oleo combustivel",
    "fuel oil": "oleo combustivel",
    "oleo combustivel": "oleo combustivel",
    "crude": "petroleo cru",
    "petroleo": "petroleo cru",
    "hidrocarboneto": "hidrocarboneto",
    "hc": "hidrocarboneto",
    "glp": "hidrocarboneto leve gasoso",
    "gas natural": "hidrocarboneto leve gasoso",
    "lpg": "hidrocarboneto leve gasoso",
    "mea": "amina mea dea mdea",
    "dea": "amina mea dea mdea",
    "mdea": "amina mea dea mdea",
    "amina": "amina mea dea mdea",
    "h2so4": "acido sulfurico",
    "acido sulfurico": "acido sulfurico",
    "fg": "gas combustivel",
    "fuel gas": "gas combustivel",
    "gas combustivel": "gas combustivel",
    "n2": "nitrogenio",
    "nitrogenio": "nitrogenio",
    "ar instrumento": "ar para instrumentos",
    "instrument air": "ar para instrumentos",
}


def obter_spec_fluido(fluido: str, temperatura_c: float = 25.0) -> EspecificacaoFluido:
    """Retorna a especificação N-76 para um fluido pelo nome.

    O argumento *fluido* é normalizado (lower-case, trim) e aceita tanto
    nomes canônicos quanto alias de campo (ex.: "VB", "OC", "sour water").

    Se a temperatura exceder o domínio do fluido, a corrosão allowance pode
    ser ajustada automaticamente (+50% acima de 200°C).

    Lança ValueError se o fluido não estiver catalogado.
    """
    chave = fluido.strip().lower()
    if chave in _ALIAS:
        chave = _ALIAS[chave]

    spec = _FLUIDOS.get(chave)
    if spec is None:
        opcoes = ", ".join(sorted(_FLUIDOS.keys()))
        raise ValueError(
            f"Fluido '{fluido}' não encontrado na matriz N-76. "
            f"Fluidos disponíveis: {opcoes}"
        )

    # Ajuste de CA por alta temperatura (acima de 200°C, corrosão acelera)
    ca_ajustada = spec.corrosao_allowance_mm
    if temperatura_c > 200.0 and ca_ajustada > 0.0:
        ca_ajustada = round(ca_ajustada * 1.5, 1)
        spec = EspecificacaoFluido(
            fluido_normalizado=spec.fluido_normalizado,
            material=spec.material,
            flange_classe=spec.flange_classe,
            face_flange=spec.face_flange,
            corrosao_allowance_mm=ca_ajustada,
            isolamento_termico=spec.isolamento_termico,
            notas_n76=spec.notas_n76 + f" [CA ajustada +50% por T={temperatura_c:.0f}°C > 200°C]",
        )

    return spec


def listar_fluidos() -> list[str]:
    """Retorna lista de todos os fluidos catalogados na matriz N-76."""
    return sorted(_FLUIDOS.keys())


def listar_aliases() -> dict[str, str]:
    """Retorna mapeamento alias → nome canônico."""
    return dict(_ALIAS)
