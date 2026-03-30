"""
n115_field_joints.py — Juntas de Campo (N-115 / REGAP)
=======================================================
Implementa a lógica de "Juntas de Campo" (Field Joints) conforme a norma
Petrobras N-115: Critérios de Montagem de Tubulações Industriais.

Regra mandatória N-115 §4.2:
  Toda linha de tubulação projetada deve prever juntas de campo (JC) a
  cada segmento máximo de 6 m, de modo a viabilizar o transporte (spools)
  e a montagem dentro da refinaria sem uso de guindastes de grande porte.

Uso rápido:
    from engenharia_automacao.core.piping.n115_field_joints import marcar_juntas_de_campo

    resultado = marcar_juntas_de_campo(comprimento_total_m=22.5, tag_linha="L-210-001-AC-1")
    for jc in resultado.juntas:
        print(f"  JC {jc.id}: posição {jc.posicao_m:.2f} m — tipo {jc.tipo_solda}")
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES N-115
# ─────────────────────────────────────────────────────────────────────────────

COMPRIMENTO_MAXIMO_SPOOL_M: float = 6.0      # N-115 §4.2 — comprimento máximo de spool
TIPO_SOLDA_CAMPO: str = "BW (Butt Weld) — SMAW E7018 conforme N-133"
TIPO_SOLDA_FABRICA: str = "BW (Butt Weld) — SMAW E7018 / SAW conforme N-133"
ESPECIFICACAO_ELETRODO: str = "Eletrodo E7018 (SMAW) — AWS A5.1 / ASME SFA-5.1"
ESQUEMA_PINTURA: str = "N-13 — Primer Epóxi Rico em Zinco (60µm) + Acabamento PU Alifático (60µm)"


@dataclass(frozen=True)
class JuntaDeCampo:
    """Representa uma junta de campo (solda de montagem) em um spool."""
    id: str                    # ex.: "JC-01"
    tag_linha: str             # ex.: "L-210-001-AC-1"
    posicao_m: float           # posição ao longo da linha [m]
    spool_anterior: str        # spool que termina aqui
    spool_proximo: str         # spool que inicia aqui
    tipo_solda: str            # especificação da solda
    eletrodo: str              # especificação do eletrodo
    pintura: str               # esquema de pintura aplicado após solda


@dataclass
class Spool:
    """Segmento de tubulação pré-fabricado (spool)."""
    id: str                    # ex.: "SP-01"
    tag_linha: str
    inicio_m: float            # início do spool na linha [m]
    fim_m: float               # fim do spool na linha [m]

    @property
    def comprimento_m(self) -> float:
        return round(self.fim_m - self.inicio_m, 3)


@dataclass
class ResultadoJuntasDeCampo:
    """Resultado completo da segmentação de uma linha em spools + JCs."""
    tag_linha: str
    comprimento_total_m: float
    comprimento_maximo_spool_m: float           # N-115 §4.2
    spools: list[Spool] = field(default_factory=list)
    juntas: list[JuntaDeCampo] = field(default_factory=list)

    @property
    def quantidade_spools(self) -> int:
        return len(self.spools)

    @property
    def quantidade_juntas_campo(self) -> int:
        return len(self.juntas)

    def resumo(self) -> dict:
        return {
            "tag_linha": self.tag_linha,
            "comprimento_total_m": self.comprimento_total_m,
            "comprimento_maximo_spool_m_n115": self.comprimento_maximo_spool_m,
            "quantidade_spools": self.quantidade_spools,
            "quantidade_juntas_campo": self.quantidade_juntas_campo,
            "norma_aplicada": "N-115 §4.2 — Juntas de Campo REGAP",
            "eletrodo": ESPECIFICACAO_ELETRODO,
            "pintura": ESQUEMA_PINTURA,
        }

    def tabela_spools(self) -> list[dict]:
        return [
            {
                "spool": s.id,
                "inicio_m": s.inicio_m,
                "fim_m": s.fim_m,
                "comprimento_m": s.comprimento_m,
            }
            for s in self.spools
        ]

    def tabela_juntas(self) -> list[dict]:
        return [
            {
                "junta": jc.id,
                "posicao_m": jc.posicao_m,
                "spool_anterior": jc.spool_anterior,
                "spool_proximo": jc.spool_proximo,
                "tipo_solda": jc.tipo_solda,
            }
            for jc in self.juntas
        ]


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def marcar_juntas_de_campo(
    comprimento_total_m: float,
    tag_linha: str,
    comprimento_max_spool_m: float = COMPRIMENTO_MAXIMO_SPOOL_M,
) -> ResultadoJuntasDeCampo:
    """Segmenta uma linha em spools com juntas de campo a cada N metros.

    Parâmetros
    ----------
    comprimento_total_m   : comprimento total da linha [m]
    tag_linha              : tag da linha (ex.: "L-210-001-AC-1")
    comprimento_max_spool_m: comprimento máximo de spool (padrão N-115 = 6 m)

    Retorna
    -------
    ResultadoJuntasDeCampo com spools e juntas de campo definidos.
    """
    if comprimento_total_m <= 0:
        raise ValueError("comprimento_total_m deve ser maior que zero.")
    if comprimento_max_spool_m <= 0:
        raise ValueError("comprimento_max_spool_m deve ser maior que zero.")

    n_spools = math.ceil(comprimento_total_m / comprimento_max_spool_m)
    comprimento_spool = comprimento_total_m / n_spools  # divisão uniforme

    resultado = ResultadoJuntasDeCampo(
        tag_linha=tag_linha,
        comprimento_total_m=comprimento_total_m,
        comprimento_maximo_spool_m=comprimento_max_spool_m,
    )

    for i in range(n_spools):
        inicio = round(i * comprimento_spool, 3)
        fim = round((i + 1) * comprimento_spool, 3)
        # Garante que o último spool vai exatamente até o final
        if i == n_spools - 1:
            fim = comprimento_total_m

        spool_id = f"SP-{i+1:02d}"
        resultado.spools.append(
            Spool(
                id=spool_id,
                tag_linha=tag_linha,
                inicio_m=inicio,
                fim_m=fim,
            )
        )

        # Junta de campo entre spool atual e próximo (exceto no último)
        if i < n_spools - 1:
            jc_id = f"JC-{i+1:02d}"
            resultado.juntas.append(
                JuntaDeCampo(
                    id=jc_id,
                    tag_linha=tag_linha,
                    posicao_m=fim,
                    spool_anterior=spool_id,
                    spool_proximo=f"SP-{i+2:02d}",
                    tipo_solda=TIPO_SOLDA_CAMPO,
                    eletrodo=ESPECIFICACAO_ELETRODO,
                    pintura=ESQUEMA_PINTURA,
                )
            )

    return resultado


def gerar_notas_solda_e_pintura() -> dict:
    """Retorna as notas padrão de solda e pintura conforme normas Petrobras."""
    return {
        "solda": {
            "processo": "SMAW — Shielded Metal Arc Welding",
            "eletrodo": ESPECIFICACAO_ELETRODO,
            "norma_solda": "N-133 — Execução de Soldas em Tubulações",
            "inspecao": "100% RT (Radiografía Industrial) para serviços Classe B",
            "pwht": "Obrigatório para P-5A / P-5B (A335 P11) — conforme N-133 §8",
            "qualificacao": "WPS / PQR aprovados pela Petrobras (N-1338)",
        },
        "pintura": {
            "sistema": ESQUEMA_PINTURA,
            "primer": "Primer Epóxi Rico em Zinco — 60 µm mínimo",
            "acabamento": "Poliuretano Alifático 2K — 60 µm mínimo",
            "espessura_total_minima_um": 120,
            "norma": "N-13 — Sistema de Pintura para Dutos e Tubulações",
            "preparo_superficie": "Jateamento Sa 2½ (ISO 8501-1) antes da aplicação",
            "areas_soldadas": (
                "Reparar pintura nas faixas de 150 mm adjacentes a cada "
                "junta de campo após inspeção de solda aprovada."
            ),
        },
    }
