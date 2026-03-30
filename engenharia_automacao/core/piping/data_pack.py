"""
data_pack.py — Gerador de Data Pack Completo (Padrão REGAP/Petrobras)
=====================================================================
Gera o pacote completo de entrega de projeto de tubulação conforme
protocolo mandatório REGAP:

  1. Tag da Linha           — Padrão L-<AREA>-<SEQ>-<MAT>-<DN>
  2. Isométrico Descritivo  — Coordenadas (X,Y,Z) de nós, curvas e conexões
  3. BOM (Bill of Materials)— Tabela técnica completa com pesos
  4. Notas de Solda         — E7018 / SMAW / N-133
  5. Pintura                — N-13 (Primer Zinco + PU Alifático)
  6. Suportes Série L       — LP-1, LP-3, LP-10
  7. Juntas de Campo N-115  — Spools a cada 6 m
  8. Stress Check           — Verificação de lira de dilatação

Uso rápido:
    from engenharia_automacao.core.piping.data_pack import gerar_data_pack

    pack = gerar_data_pack(
        area="210",
        sequencial="001",
        fluido="Vapor de Baixa",
        diametro_nominal_pol='2"',
        comprimento_total_m=18.0,
        temperatura_operacao_c=180.0,
        pressao_operacao_bar=8.0,
        nos=[
            {"id": "N1", "x": 0,    "y": 0,   "z": 0},
            {"id": "N2", "x": 9000, "y": 0,   "z": 0},
            {"id": "N3", "x": 9000, "y": 3000,"z": 0},
        ],
    )
    print(pack.tag_linha)
    # → "L-210-001-AC-2\""
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .n76_fluidos import obter_spec_fluido, EspecificacaoFluido
from .n115_field_joints import (
    marcar_juntas_de_campo,
    gerar_notas_solda_e_pintura,
    ResultadoJuntasDeCampo,
)
from .serie_l_supports import (
    posicionar_suportes,
    ResultadoSuportes,
)
from .expansao_termica import verificar_expansao, ResultadoStressCheck
from .specs import select_piping_specification, PipingSpecification


# ─────────────────────────────────────────────────────────────────────────────
# MAPEAMENTO DE CÓDIGO DE MATERIAL PARA TAG
# ─────────────────────────────────────────────────────────────────────────────
_CODIGO_MATERIAL: dict[str, str] = {
    "ASTM A106 Gr.B": "AC",    # Aço Carbono
    "ASTM A335 P11":  "CM",    # Cromo-Molibdênio
    "ASTM A53 Gr.B":  "AC",
}


def _codigo_material(material: str) -> str:
    for chave, codigo in _CODIGO_MATERIAL.items():
        if chave.upper() in material.upper():
            return codigo
    return "AC"  # padrão


def _formatar_dn_pol(diametro_pol: str) -> str:
    """Remove espaços e normaliza o DN em polegadas para o tag."""
    return diametro_pol.strip().replace(" ", "").replace('"', '"')


# ─────────────────────────────────────────────────────────────────────────────
# ESTRUTURAS DE DADOS DO DATA PACK
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NoIsometrico:
    """Nó (ponto de coordenada) de um isométrico."""
    id: str
    x: float   # [mm]
    y: float   # [mm]
    z: float   # [mm]
    descricao: str = ""


@dataclass
class SegmentoIsometrico:
    """Segmento de tubo entre dois nós."""
    id: str
    no_inicio: str
    no_fim: str
    comprimento_mm: float
    direcao: str         # ex.: "+X", "-Z", "+Y"
    tipo_conexao_fim: str  # ex.: "CURVA 90°", "FLANGE", "SOLDA TOPO"


@dataclass
class ItemBOM:
    """Item da BOM (Bill of Materials) / Lista de Materiais."""
    item_num: int
    codigo: str               # ex.: "PIPE-01"
    descricao: str            # ex.: "Tubo sem-costura Ø 2\" SCH 40"
    norma_material: str       # ex.: "ASTM A106 Gr.B"
    quantidade: float
    unidade: str              # ex.: "m", "UN", "KG"
    peso_unitario_kg: float
    peso_total_kg: float
    observacao: str = ""


@dataclass
class DataPack:
    """Pacote completo de entrega de projeto de linha de tubulação."""
    # Identificação
    tag_linha: str
    area: str
    sequencial: str
    fluido: str
    diametro_nominal_pol: str
    diametro_nominal_mm: float
    material: str
    flange_classe: str
    face_flange: str
    corrosao_allowance_mm: float
    schedule: str
    pressao_operacao_bar: float
    temperatura_operacao_c: float
    comprimento_total_m: float
    timestamp_utc: str

    # Dados técnicos
    spec_n76: EspecificacaoFluido
    spec_piping: PipingSpecification

    # Isométrico
    nos: list[NoIsometrico] = field(default_factory=list)
    segmentos: list[SegmentoIsometrico] = field(default_factory=list)

    # BOM
    bom: list[ItemBOM] = field(default_factory=list)

    # Notas
    notas_solda_pintura: dict[str, Any] = field(default_factory=dict)

    # Suportes
    resultado_suportes: ResultadoSuportes | None = None

    # Juntas de Campo N-115
    resultado_jc: ResultadoJuntasDeCampo | None = None

    # Stress Check
    resultado_stress: ResultadoStressCheck | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serializa o Data Pack completo para dicionário (JSON-serializável)."""
        return {
            "data_pack_header": {
                "tag_linha": self.tag_linha,
                "area": self.area,
                "sequencial": self.sequencial,
                "fluido": self.fluido,
                "diametro_nominal": self.diametro_nominal_pol,
                "material": self.material,
                "flange_classe": self.flange_classe,
                "face_flange": self.face_flange,
                "corrosao_allowance_mm": self.corrosao_allowance_mm,
                "schedule": self.schedule,
                "pressao_operacao_bar": self.pressao_operacao_bar,
                "temperatura_operacao_c": self.temperatura_operacao_c,
                "comprimento_total_m": self.comprimento_total_m,
                "timestamp_utc": self.timestamp_utc,
                "unidade": "REGAP — Refinaria Gabriel Passos / Betim-MG",
                "normas_mandatorias": ["N-58", "N-76", "N-115", "N-133", "N-13", "ASME B31.3"],
            },
            "isometrico_descritivo": {
                "nos": [
                    {"id": n.id, "x_mm": n.x, "y_mm": n.y, "z_mm": n.z, "descricao": n.descricao}
                    for n in self.nos
                ],
                "segmentos": [
                    {
                        "id": s.id,
                        "de": s.no_inicio,
                        "ate": s.no_fim,
                        "comprimento_mm": s.comprimento_mm,
                        "direcao": s.direcao,
                        "conexao_fim": s.tipo_conexao_fim,
                    }
                    for s in self.segmentos
                ],
            },
            "bom": [
                {
                    "item": i.item_num,
                    "codigo": i.codigo,
                    "descricao": i.descricao,
                    "norma_material": i.norma_material,
                    "quantidade": i.quantidade,
                    "unidade": i.unidade,
                    "peso_unitario_kg": i.peso_unitario_kg,
                    "peso_total_kg": i.peso_total_kg,
                    "observacao": i.observacao,
                }
                for i in self.bom
            ],
            "notas_solda_pintura": self.notas_solda_pintura,
            "suportes_serie_l": (
                self.resultado_suportes.resumo() if self.resultado_suportes else {}
            ),
            "juntas_de_campo_n115": (
                {
                    "resumo": self.resultado_jc.resumo(),
                    "spools": self.resultado_jc.tabela_spools(),
                    "juntas": self.resultado_jc.tabela_juntas(),
                }
                if self.resultado_jc else {}
            ),
            "stress_check": (
                {
                    "expansao_mm": self.resultado_stress.expansao_termica_mm,
                    "delta_t": self.resultado_stress.delta_t,
                    "forca_bocal_N": self.resultado_stress.forca_bocal_estimada_N,
                    "tensao_MPa": self.resultado_stress.tensao_equivalente_MPa,
                    "status": self.resultado_stress.status.value,
                    "lira_recomendada": self.resultado_stress.tipo_lira_recomendada.value,
                    "recomendacao": self.resultado_stress.recomendacao,
                    "dimensoes_lira": self.resultado_stress.dimensoes_lira,
                }
                if self.resultado_stress else {}
            ),
            "notas_n76": self.spec_n76.notas_n76,
        }

    def to_markdown(self) -> str:
        """Gera relatório Markdown completo do Data Pack."""
        d = self.to_dict()
        h = d["data_pack_header"]
        stress = d["stress_check"]
        jc = d["juntas_de_campo_n115"]
        sup = d["suportes_serie_l"]

        lines = [
            f"# DATA PACK — {self.tag_linha}",
            f"**Unidade**: {h['unidade']}",
            f"**Emissão**: {self.timestamp_utc}",
            "",
            "---",
            "",
            "## 1. IDENTIFICAÇÃO DA LINHA",
            "",
            f"| Campo                   | Valor |",
            f"|-------------------------|-------|",
            f"| **Tag da Linha**        | `{self.tag_linha}` |",
            f"| Fluido                  | {self.fluido} |",
            f"| Diâmetro Nominal        | {self.diametro_nominal_pol} ({self.diametro_nominal_mm:.0f} mm) |",
            f"| Material                | {self.material} |",
            f"| Schedule                | {self.schedule} |",
            f"| Flange / Classe         | {self.face_flange} {self.flange_classe} |",
            f"| C.A. (Corrosão)         | {self.corrosao_allowance_mm:.1f} mm |",
            f"| Pressão de Operação     | {self.pressao_operacao_bar:.1f} bar |",
            f"| Temperatura de Operação | {self.temperatura_operacao_c:.0f} °C |",
            f"| Comprimento Total       | {self.comprimento_total_m:.1f} m |",
            f"| Normas Aplicadas        | {', '.join(h['normas_mandatorias'])} |",
            "",
            "---",
            "",
            "## 2. ISOMÉTRICO DESCRITIVO (Coordenadas dos Nós)",
            "",
            "| Nó  | X (mm) | Y (mm) | Z (mm) | Descrição |",
            "|-----|--------|--------|--------|-----------|",
        ]

        for n in d["isometrico_descritivo"]["nos"]:
            lines.append(
                f"| {n['id']} | {n['x_mm']:.0f} | {n['y_mm']:.0f} | {n['z_mm']:.0f} | {n['descricao']} |"
            )

        lines += [
            "",
            "### Segmentos",
            "",
            "| Seg | De → Até | Comprimento (mm) | Direção | Conexão |",
            "|-----|----------|------------------|---------|---------|",
        ]
        for s in d["isometrico_descritivo"]["segmentos"]:
            lines.append(
                f"| {s['id']} | {s['de']} → {s['ate']} | {s['comprimento_mm']:.0f} "
                f"| {s['direcao']} | {s['conexao_fim']} |"
            )

        lines += [
            "",
            "---",
            "",
            "## 3. BOM — LISTA DE MATERIAIS (Bill of Materials)",
            "",
            "| # | Código | Descrição | Norma Material | Qtd | Un | Peso unit. (kg) | Peso total (kg) |",
            "|---|--------|-----------|----------------|-----|----|-----------------|-----------------|",
        ]
        peso_total_geral = 0.0
        for i in d["bom"]:
            peso_total_geral += i["peso_total_kg"]
            lines.append(
                f"| {i['item']} | {i['codigo']} | {i['descricao']} | {i['norma_material']} "
                f"| {i['quantidade']:.1f} | {i['unidade']} | {i['peso_unitario_kg']:.2f} "
                f"| {i['peso_total_kg']:.2f} |"
            )
        lines.append(f"|   |        | **TOTAL** |                |     |    |                 | **{peso_total_geral:.2f}** |")

        # Solda e Pintura
        s_info = d["notas_solda_pintura"]
        solda = s_info.get("solda", {})
        pintura = s_info.get("pintura", {})

        lines += [
            "",
            "---",
            "",
            "## 4. NOTAS DE SOLDA",
            "",
            f"- **Processo**: {solda.get('processo', '')}",
            f"- **Eletrodo**: {solda.get('eletrodo', '')}",
            f"- **Norma**: {solda.get('norma_solda', '')}",
            f"- **Inspeção**: {solda.get('inspecao', '')}",
            f"- **PWHT**: {solda.get('pwht', '')}",
            f"- **Qualificação**: {solda.get('qualificacao', '')}",
            "",
            "---",
            "",
            "## 5. ESQUEMA DE PINTURA (N-13)",
            "",
            f"- **Sistema**: {pintura.get('sistema', '')}",
            f"- **Primer**: {pintura.get('primer', '')}",
            f"- **Acabamento**: {pintura.get('acabamento', '')}",
            f"- **Espessura Total Mínima**: {pintura.get('espessura_total_minima_um', '')} µm",
            f"- **Preparo de Superfície**: {pintura.get('preparo_superficie', '')}",
            f"- **Áreas Soldadas**: {pintura.get('areas_soldadas', '')}",
        ]

        # Suportes
        if sup:
            lines += [
                "",
                "---",
                "",
                "## 6. SUPORTES — SÉRIE L PETROBRAS",
                "",
                f"- **Vão máximo calculado**: {sup.get('vao_maximo_calculado_m', '')} m",
                f"- **Quantidade de suportes**: {sup.get('quantidade_suportes', '')}",
                f"- **Norma**: {sup.get('norma_serie_l', '')}",
                "",
                "| ID | Tipo | Posição (m) | Carga (kg) | Vão (m) |",
                "|----|------|-------------|------------|---------|",
            ]
            for s in sup.get("suportes", []):
                lines.append(
                    f"| {s['id']} | {s['tipo']} | {s['posicao_m']:.2f} | {s['carga_kg']:.1f} | {s['vao_m']:.2f} |"
                )

        # Juntas de Campo
        if jc:
            resumo_jc = jc.get("resumo", {})
            lines += [
                "",
                "---",
                "",
                "## 7. JUNTAS DE CAMPO — N-115",
                "",
                f"- **Comprimento máx. spool**: {resumo_jc.get('comprimento_maximo_spool_m_n115', 6)} m",
                f"- **Quantidade de spools**: {resumo_jc.get('quantidade_spools', '')}",
                f"- **Quantidade de JC**: {resumo_jc.get('quantidade_juntas_campo', '')}",
                f"- **Eletrodo**: {resumo_jc.get('eletrodo', '')}",
                "",
                "| Spool | Início (m) | Fim (m) | Comprimento (m) |",
                "|-------|------------|---------|-----------------|",
            ]
            for sp in jc.get("spools", []):
                lines.append(
                    f"| {sp['spool']} | {sp['inicio_m']:.2f} | {sp['fim_m']:.2f} | {sp['comprimento_m']:.2f} |"
                )

            if jc.get("juntas"):
                lines += [
                    "",
                    "| Junta | Posição (m) | Spool Ant. | Spool Próx. |",
                    "|-------|-------------|------------|-------------|",
                ]
                for junta in jc["juntas"]:
                    lines.append(
                        f"| {junta['junta']} | {junta['posicao_m']:.2f} | {junta['spool_anterior']} | {junta['spool_proximo']} |"
                    )

        # Stress Check
        if stress:
            lines += [
                "",
                "---",
                "",
                "## 8. STRESS CHECK — VERIFICAÇÃO DE EXPANSÃO TÉRMICA",
                "",
                f"| Parâmetro | Valor |",
                f"|-----------|-------|",
                f"| ΔT (operação − instalação) | {stress.get('delta_t', '')} °C |",
                f"| Expansão Térmica Linear | {stress.get('expansao_mm', '')} mm |",
                f"| Força estimada no bocal | {stress.get('forca_bocal_N', '')} N |",
                f"| Tensão equivalente | {stress.get('tensao_MPa', '')} MPa |",
                f"| **Status** | **{stress.get('status', '')}** |",
                f"| Lira recomendada | {stress.get('lira_recomendada', '')} |",
                "",
                f"> **{stress.get('recomendacao', '')}**",
            ]
            dim = stress.get("dimensoes_lira", {})
            if dim:
                lines += ["", "**Dimensões da lira sugerida:**"]
                for k, v in dim.items():
                    lines.append(f"- **{k}**: {v}")

        lines += [
            "",
            "---",
            "",
            "## 9. NOTAS N-76 (MATERIAIS)",
            "",
            f"> {d['notas_n76']}",
            "",
            "---",
            "_Documento gerado automaticamente pelo Sistema Especialista REGAP/Petrobras._",
            f"_Emissão: {self.timestamp_utc}_",
        ]

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DA BOM INTERNA
# ─────────────────────────────────────────────────────────────────────────────

_PESO_TUBO_KG_M_BOM: dict[int, float] = {
    25: 1.70, 50: 3.60, 80: 6.00, 100: 8.60,
    150: 15.00, 200: 23.70, 250: 34.00, 300: 46.00,
}
_PESO_CURVA_KG: dict[int, float] = {
    25: 0.4, 50: 1.1, 80: 2.5, 100: 4.5,
    150: 10.0, 200: 18.0, 250: 30.0, 300: 48.0,
}
_PESO_FLANGE_KG: dict[int, float] = {
    25: 1.8, 50: 3.6, 80: 7.2, 100: 10.9,
    150: 19.1, 200: 30.8, 250: 47.2, 300: 67.1,
}


def _dn_mais_proximo(diametro_mm: float, tabela: dict) -> int:
    return min(tabela.keys(), key=lambda k: abs(k - diametro_mm))


def _pol_to_mm(dn_pol: str) -> float:
    """Converte DN em polegadas ('2"', '4"', etc.) para mm aproximado."""
    _map = {
        '0.5"': 15, '3/4"': 20, '1"': 25, '1.5"': 38,
        '2"': 51, '3"': 76, '4"': 102, '6"': 152,
        '8"': 203, '10"': 254, '12"': 305,
    }
    return float(_map.get(dn_pol.strip(), 100.0))


def _gerar_bom(
    comprimento_m: float,
    diametro_mm: float,
    material: str,
    schedule: str,
    flange_classe: str,
    face_flange: str,
    n_curvas: int = 2,
    n_flanges: int = 2,
) -> list[ItemBOM]:
    """Gera a BOM básica de uma linha reta com curvas e flanges."""
    dn = _dn_mais_proximo(diametro_mm, _PESO_TUBO_KG_M_BOM)
    peso_tubo_m = _PESO_TUBO_KG_M_BOM.get(dn, 8.6)
    peso_curva = _PESO_CURVA_KG.get(dn, 4.5)
    peso_flange = _PESO_FLANGE_KG.get(dn, 10.9)

    dn_pol_str = _mm_to_pol_str(diametro_mm)

    bom: list[ItemBOM] = [
        ItemBOM(
            item_num=1,
            codigo="PIPE-01",
            descricao=f"Tubo sem-costura Ø {dn_pol_str} {schedule} — {material}",
            norma_material=f"{material} / ASME B36.10M",
            quantidade=comprimento_m,
            unidade="m",
            peso_unitario_kg=peso_tubo_m,
            peso_total_kg=round(comprimento_m * peso_tubo_m, 2),
        ),
    ]

    if n_curvas > 0:
        bom.append(ItemBOM(
            item_num=2,
            codigo="ELL-01",
            descricao=f"Curva 90° raio longo Ø {dn_pol_str} — {material}",
            norma_material=f"{material} / ASME B16.9",
            quantidade=float(n_curvas),
            unidade="UN",
            peso_unitario_kg=peso_curva,
            peso_total_kg=round(n_curvas * peso_curva, 2),
        ))

    if n_flanges > 0:
        bom.append(ItemBOM(
            item_num=3,
            codigo="FLG-01",
            descricao=f"Flange WN Ø {dn_pol_str} Cl. {flange_classe} {face_flange} — {material}",
            norma_material=f"{material} / ASME B16.5",
            quantidade=float(n_flanges),
            unidade="UN",
            peso_unitario_kg=peso_flange,
            peso_total_kg=round(n_flanges * peso_flange, 2),
        ))

    bom.append(ItemBOM(
        item_num=len(bom) + 1,
        codigo="JNT-01",
        descricao=f"Junta espiral metálica Ø {dn_pol_str} Cl. {flange_classe} SS304+GF",
        norma_material="ASME B16.20 / API 601",
        quantidade=float(n_flanges),
        unidade="UN",
        peso_unitario_kg=0.3,
        peso_total_kg=round(n_flanges * 0.3, 2),
    ))

    bom.append(ItemBOM(
        item_num=len(bom) + 1,
        codigo="BOLT-01",
        descricao=f"Parafuso prisioneiro stud-bolt ASTM A193-B7 / Porca A194-2H",
        norma_material="ASTM A193-B7 / ASME B18.2.1",
        quantidade=float(n_flanges * 8),
        unidade="UN",
        peso_unitario_kg=0.25,
        peso_total_kg=round(n_flanges * 8 * 0.25, 2),
        observacao="8 parafusos por flange (estimativa Cl. 150)",
    ))

    return bom


def _mm_to_pol_str(diametro_mm: float) -> str:
    _map = {15: '1/2"', 20: '3/4"', 25: '1"', 38: '1.5"', 51: '2"',
            76: '3"', 102: '4"', 152: '6"', 203: '8"', 254: '10"', 305: '12"'}
    dn = min(_map.keys(), key=lambda k: abs(k - diametro_mm))
    return _map[dn]


def _gerar_nos(nos_input: list[dict]) -> list[NoIsometrico]:
    """Converte lista de dicts em NoIsometrico."""
    return [
        NoIsometrico(
            id=n["id"],
            x=float(n.get("x", 0)),
            y=float(n.get("y", 0)),
            z=float(n.get("z", 0)),
            descricao=n.get("descricao", ""),
        )
        for n in nos_input
    ]


def _gerar_segmentos(nos: list[NoIsometrico]) -> list[SegmentoIsometrico]:
    """Gera segmentos automáticos conectando nós sequencialmente."""
    segmentos = []
    for i in range(len(nos) - 1):
        n1, n2 = nos[i], nos[i + 1]
        dx = n2.x - n1.x
        dy = n2.y - n1.y
        dz = n2.z - n1.z
        comprimento = math.sqrt(dx**2 + dy**2 + dz**2)

        # Determina direção dominante
        abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)
        if abs_dx >= abs_dy and abs_dx >= abs_dz:
            direcao = "+X" if dx >= 0 else "-X"
        elif abs_dy >= abs_dx and abs_dy >= abs_dz:
            direcao = "+Y" if dy >= 0 else "-Y"
        else:
            direcao = "+Z" if dz >= 0 else "-Z"

        # Tipo de conexão no fim do segmento
        if i < len(nos) - 2:
            prox = nos[i + 2]
            ddx = prox.x - n2.x
            ddy = prox.y - n2.y
            ddz = prox.z - n2.z
            # Se há mudança de direção → curva
            mudou = (
                (abs_dx > 0 and abs(ddy) > 0)
                or (abs_dy > 0 and abs(ddz) > 0)
                or (abs_dz > 0 and abs(ddx) > 0)
            )
            conexao = "CURVA 90° R.L." if mudou else "SOLDA TOPO"
        else:
            conexao = "FLANGE WN"

        segmentos.append(SegmentoIsometrico(
            id=f"SEG-{i+1:02d}",
            no_inicio=n1.id,
            no_fim=n2.id,
            comprimento_mm=round(comprimento, 1),
            direcao=direcao,
            tipo_conexao_fim=conexao,
        ))

    return segmentos


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def gerar_data_pack(
    area: str,
    sequencial: str,
    fluido: str,
    diametro_nominal_pol: str,
    comprimento_total_m: float,
    temperatura_operacao_c: float,
    pressao_operacao_bar: float,
    nos: list[dict] | None = None,
    temperatura_instalacao_c: float = 20.0,
    n_curvas: int = 2,
    n_flanges: int = 2,
    com_isolamento: bool | None = None,
) -> DataPack:
    """Gera o Data Pack completo de uma linha de tubulação.

    Parâmetros
    ----------
    area                    : código da área de processo (ex.: "210")
    sequencial              : número sequencial da linha (ex.: "001")
    fluido                  : nome do fluido (aceita alias N-76)
    diametro_nominal_pol    : DN em polegadas (ex.: '2"', '4"')
    comprimento_total_m     : comprimento total da linha [m]
    temperatura_operacao_c  : temperatura máxima de operação [°C]
    pressao_operacao_bar    : pressão de operação [bar]
    nos                     : lista de nós [{id, x, y, z}] em mm (opcional)
    temperatura_instalacao_c: temperatura de montagem [°C] (padrão 20°C)
    n_curvas                : número de curvas na linha (BOM)
    n_flanges               : número de flanges (BOM)
    com_isolamento          : força/suprime isolamento (None = usa N-76)

    Retorna
    -------
    DataPack completo com todos os documentos.
    """
    # 1. Especificação N-76
    spec_n76 = obter_spec_fluido(fluido, temperatura_c=temperatura_operacao_c)

    # 2. Tag da linha
    diametro_mm = _pol_to_mm(diametro_nominal_pol)
    cod_mat = _codigo_material(spec_n76.material)
    tag = f"L-{area}-{sequencial}-{cod_mat}-{diametro_nominal_pol}"

    # 3. Especificação de piping (espessura, schedule, hidrotest)
    spec_piping = select_piping_specification(
        fluid=fluido,
        temperature_c=temperatura_operacao_c,
        operating_pressure_bar=pressao_operacao_bar,
        diameter_mm=diametro_mm,
    )

    # 4. Nós e segmentos do isométrico
    if nos:
        nos_obj = _gerar_nos(nos)
    else:
        # Gera linha reta padrão (se não fornecido)
        comp_mm = comprimento_total_m * 1000.0
        nos_obj = _gerar_nos([
            {"id": "N1", "x": 0, "y": 0, "z": 0, "descricao": "Origem"},
            {"id": "N2", "x": comp_mm, "y": 0, "z": 0, "descricao": "Destino"},
        ])

    segmentos_obj = _gerar_segmentos(nos_obj)

    # 5. BOM
    bom = _gerar_bom(
        comprimento_m=comprimento_total_m,
        diametro_mm=diametro_mm,
        material=spec_n76.material,
        schedule=spec_piping.selected_schedule,
        flange_classe=spec_n76.flange_classe,
        face_flange=spec_n76.face_flange,
        n_curvas=n_curvas,
        n_flanges=n_flanges,
    )

    # 6. Notas de solda e pintura
    notas = gerar_notas_solda_e_pintura()

    # 7. Suportes Série L
    isolamento = com_isolamento if com_isolamento is not None else spec_n76.isolamento_termico
    suportes = posicionar_suportes(
        comprimento_total_m=comprimento_total_m,
        diametro_mm=diametro_mm,
        tag_linha=tag,
        fluido=fluido,
        com_isolamento=isolamento,
    )

    # 8. Juntas de Campo N-115
    jc = marcar_juntas_de_campo(
        comprimento_total_m=comprimento_total_m,
        tag_linha=tag,
    )

    # 9. Stress Check
    stress = verificar_expansao(
        comprimento_reto_m=comprimento_total_m,
        diametro_mm=diametro_mm,
        temperatura_operacao_c=temperatura_operacao_c,
        temperatura_instalacao_c=temperatura_instalacao_c,
    )

    return DataPack(
        tag_linha=tag,
        area=area,
        sequencial=sequencial,
        fluido=fluido,
        diametro_nominal_pol=diametro_nominal_pol,
        diametro_nominal_mm=diametro_mm,
        material=spec_n76.material,
        flange_classe=spec_n76.flange_classe,
        face_flange=spec_n76.face_flange,
        corrosao_allowance_mm=spec_n76.corrosao_allowance_mm,
        schedule=spec_piping.selected_schedule,
        pressao_operacao_bar=pressao_operacao_bar,
        temperatura_operacao_c=temperatura_operacao_c,
        comprimento_total_m=comprimento_total_m,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        spec_n76=spec_n76,
        spec_piping=spec_piping,
        nos=nos_obj,
        segmentos=segmentos_obj,
        bom=bom,
        notas_solda_pintura=notas,
        resultado_suportes=suportes,
        resultado_jc=jc,
        resultado_stress=stress,
    )


def formatar_tag_linha(
    area: str,
    sequencial: str,
    material: str,
    diametro_pol: str,
) -> str:
    """Monta a tag de linha conforme padrão REGAP.

    Formato: L-<AREA>-<SEQ>-<COD_MAT>-<DN>
    Exemplo: L-210-001-AC-2"
    """
    cod = _codigo_material(material)
    return f"L-{area}-{sequencial}-{cod}-{diametro_pol}"
