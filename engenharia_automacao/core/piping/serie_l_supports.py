"""
serie_l_supports.py — Série L de Suportes Petrobras (LP-1 / LP-3 / LP-10)
==========================================================================
Implementa a lógica de seleção e posicionamento de suportes tubulares
conforme a Série L (Suportes Padrão) da Petrobras, usada na REGAP e demais
refinarias.

Tipos principais implementados:
  • LP-1  — Guia (permite deslocamento axial, restringe lateral)
  • LP-3  — Ancoragem (fixa totalmente, absorve reações de expansão)
  • LP-10 — Apoio Simples (sapata de escorregamento, carrega peso)

Cálculo de vão máximo:
  A distância máxima entre suportes é calculada pela deflexão admissível
  de um tubo cheio de fluido + isolamento (se aplicável), considerando
  viga bi-apoiada com carga distribuída uniforme.

Uso rápido:
    from engenharia_automacao.core.piping.serie_l_supports import (
        calcular_vao_maximo,
        posicionar_suportes,
    )

    resultado = posicionar_suportes(
        comprimento_total_m=24.0,
        diametro_mm=100.0,
        fluido="agua de processo",
        com_isolamento=False,
    )
    for s in resultado.suportes:
        print(f"{s.tipo.value} {s.id} @ {s.posicao_m:.2f} m")
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# PARÂMETROS FISICOS DE REFERÊNCIA
# ─────────────────────────────────────────────────────────────────────────────

E_ACO_MPA: float = 200_000.0          # Módulo de elasticidade Aço Carbono [MPa]
DELTA_LIM_RATIO: float = 1.0 / 500.0  # Deflexão admissível = L/500 (prática Petrobras)

# Peso unitário de água de processo (kg/L = kg/dm³)
DENSIDADE_AGUA_KG_L: float = 1.0
# Peso de isolamento típico por metro (lã mineral 50mm, chapisco Al) em kg/m para DN 100
# Tabela simplificada: peso adicional de isolamento [kg/m] por DN [mm]
_PESO_ISOLAMENTO_KG_M: dict[int, float] = {
    25:  2.0,
    50:  3.5,
    80:  5.0,
    100: 6.5,
    150: 9.0,
    200: 12.0,
    250: 15.0,
    300: 18.0,
}

# Peso linear do tubo vazio [kg/m] por DN [mm] (SCH 40, referência)
_PESO_TUBO_KG_M: dict[int, float] = {
    25:  1.70,
    50:  3.60,
    80:  6.00,
    100: 8.60,
    150: 15.00,
    200: 23.70,
    250: 34.00,
    300: 46.00,
}

# Inércia tubular [mm⁴] — tubo silíd. SCH 40 por DN nominal [mm]
# I = π/64 × (Do⁴ - Di⁴) — valores pre-calculados para DOs e espessuras SCH 40
_INERCIA_TUBO_MM4: dict[int, float] = {
    25:  8.49e4,
    50:  4.93e5,
    80:  1.52e6,
    100: 3.59e6,
    150: 1.16e7,
    200: 3.11e7,
    250: 7.00e7,
    300: 1.38e8,
}


class TipoSuporteSL(str, Enum):
    """Tipos de suporte da Série L Petrobras."""
    LP1_GUIA          = "LP-1 (Guia)"
    LP3_ANCORA        = "LP-3 (Ancoragem)"
    LP10_APOIO_SIMPLES = "LP-10 (Apoio Simples)"


@dataclass(frozen=True)
class SuporteSL:
    """Representação de um suporte da Série L posicionado em uma linha."""
    id: str                     # ex.: "S-01"
    tipo: TipoSuporteSL
    posicao_m: float            # posição ao longo da linha [m]
    carga_kg: float             # carga vertical estimada [kg]
    vao_m: float                # vão coberto por este suporte [m]
    norma_referencia: str       # ex.: "LP-10 Série L Petrobras"
    observacao: str = ""


@dataclass
class ResultadoSuportes:
    """Resultado completo do posicionamento de suportes em uma linha."""
    tag_linha: str
    comprimento_total_m: float
    vao_maximo_calculado_m: float
    suportes: list[SuporteSL] = field(default_factory=list)

    @property
    def quantidade_suportes(self) -> int:
        return len(self.suportes)

    def resumo(self) -> dict:
        return {
            "tag_linha": self.tag_linha,
            "comprimento_total_m": self.comprimento_total_m,
            "vao_maximo_calculado_m": round(self.vao_maximo_calculado_m, 2),
            "quantidade_suportes": self.quantidade_suportes,
            "norma_serie_l": "Série L Petrobras — LP-1, LP-3, LP-10",
            "suportes": [
                {
                    "id": s.id,
                    "tipo": s.tipo.value,
                    "posicao_m": round(s.posicao_m, 2),
                    "carga_kg": round(s.carga_kg, 1),
                    "vao_m": round(s.vao_m, 2),
                }
                for s in self.suportes
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _nominal_mais_proximo(diametro_mm: float, tabela: dict) -> int:
    return min(tabela.keys(), key=lambda dn: abs(dn - diametro_mm))


def _peso_fluido_kg_m(diametro_mm: float, densidade_kg_l: float = DENSIDADE_AGUA_KG_L) -> float:
    """Peso do fluido por metro de tubo [kg/m] — área interna × densidade."""
    dn = _nominal_mais_proximo(diametro_mm, _PESO_TUBO_KG_M)
    # Di aproximado: Do - 2*espessura (estimativa para SCH 40)
    _do_mm = {25: 33.4, 50: 60.3, 80: 88.9, 100: 114.3, 150: 168.3, 200: 219.1, 250: 273.1, 300: 323.9}
    _t_mm  = {25: 3.38, 50: 3.91, 80: 5.49, 100: 6.02, 150: 7.11, 200: 8.18, 250: 9.27, 300: 10.31}
    do = _do_mm.get(dn, diametro_mm)
    t  = _t_mm.get(dn, 5.0)
    di = do - 2.0 * t
    area_interna_mm2 = math.pi / 4.0 * di ** 2
    volume_m3_por_m = area_interna_mm2 * 1e-6  # mm² → m²
    return round(volume_m3_por_m * densidade_kg_l * 1000.0, 3)  # kg/m


def _peso_isolamento_kg_m(diametro_mm: float) -> float:
    dn = _nominal_mais_proximo(diametro_mm, _PESO_ISOLAMENTO_KG_M)
    return _PESO_ISOLAMENTO_KG_M.get(dn, 6.5)


def _inercia_mm4(diametro_mm: float) -> float:
    dn = _nominal_mais_proximo(diametro_mm, _INERCIA_TUBO_MM4)
    return _INERCIA_TUBO_MM4[dn]


# ─────────────────────────────────────────────────────────────────────────────
# API PÚBLICA
# ─────────────────────────────────────────────────────────────────────────────

def calcular_vao_maximo(
    diametro_mm: float,
    com_isolamento: bool = False,
    densidade_fluido_kg_l: float = DENSIDADE_AGUA_KG_L,
    delta_lim_ratio: float = DELTA_LIM_RATIO,
) -> float:
    """Calcula o vão máximo admissível entre suportes [m].

    Usa a equação da deflexão máxima para viga bi-apoiada com carga uniform:
        δ_max = (5 · w · L⁴) / (384 · E · I)  ≤  δ_lim = L / 500

    Isolando L:
        L³ ≤ (384 · E · I · δ_ratio) / (5 · w)
        L  = ( (384 · E · I) / (5 · w / δ_ratio) )^(1/3)

    Onde w inclui: tubo + fluido + isolamento (se aplicável).

    Parâmetros
    ----------
    diametro_mm         : diâmetro nominal externo [mm]
    com_isolamento      : se True, soma peso de isolamento ao peso linear
    densidade_fluido_kg_l: densidade do fluido [kg/L] (padrão água = 1.0)
    delta_lim_ratio     : razão δ_lim/L (padrão 1/500 = 0.002)

    Retorna
    -------
    vão máximo [m]
    """
    dn = _nominal_mais_proximo(diametro_mm, _PESO_TUBO_KG_M)

    w_tubo = _PESO_TUBO_KG_M.get(dn, 8.6)           # kg/m
    w_fluido = _peso_fluido_kg_m(diametro_mm, densidade_fluido_kg_l)
    w_iso = _peso_isolamento_kg_m(diametro_mm) if com_isolamento else 0.0
    w_total_kg_m = w_tubo + w_fluido + w_iso

    # Carga linear em N/mm
    g = 9.81  # m/s²
    w_N_mm = (w_total_kg_m * g) / 1000.0  # N/mm

    I_mm4 = _inercia_mm4(diametro_mm)

    # L³ = (384 · E · I · δ_ratio) / (5 · w)
    numerator = 384.0 * E_ACO_MPA * I_mm4 * delta_lim_ratio
    denominator = 5.0 * w_N_mm
    L_mm = (numerator / denominator) ** (1.0 / 3.0)
    L_m = L_mm / 1000.0

    # Teto prático: 12 m (N-115 não permite vãos > 12m sem estudo especial)
    return round(min(L_m, 12.0), 2)


def posicionar_suportes(
    comprimento_total_m: float,
    diametro_mm: float,
    tag_linha: str = "LINHA",
    fluido: str = "agua de processo",
    com_isolamento: bool = False,
    densidade_fluido_kg_l: float = DENSIDADE_AGUA_KG_L,
    forcar_ancora_extremidades: bool = True,
) -> ResultadoSuportes:
    """Posiciona suportes Série L ao longo de uma linha.

    Lógica de posicionamento:
      • Ponto inicial → LP-3 (Ancoragem)
      • Trechos intermediários → LP-10 (Apoio Simples)
      • A cada mudança de direção prevista → LP-1 (Guia)
      • Ponto final → LP-3 (Ancoragem)

    Parâmetros
    ----------
    comprimento_total_m    : comprimento total da linha [m]
    diametro_mm            : diâmetro nominal externo [mm]
    tag_linha              : tag da linha
    fluido                 : fluido transportado (apenas para documentação)
    com_isolamento         : se True, inclui peso do isolamento no cálculo
    densidade_fluido_kg_l  : densidade do fluido [kg/L]
    forcar_ancora_extremi  : força LP-3 nas extremidades da linha

    Retorna
    -------
    ResultadoSuportes com suportes posicionados.
    """
    if comprimento_total_m <= 0:
        raise ValueError("comprimento_total_m deve ser > 0.")

    vao_max = calcular_vao_maximo(diametro_mm, com_isolamento, densidade_fluido_kg_l)

    # Carga por suporte = w_total × vão / 2 (metade do vão de cada lado)
    dn = _nominal_mais_proximo(diametro_mm, _PESO_TUBO_KG_M)
    w_kg_m = (
        _PESO_TUBO_KG_M.get(dn, 8.6)
        + _peso_fluido_kg_m(diametro_mm, densidade_fluido_kg_l)
        + (_peso_isolamento_kg_m(diametro_mm) if com_isolamento else 0.0)
    )
    carga_por_suporte_kg = round(w_kg_m * vao_max / 2.0, 1)  # carga aproximada

    n_vãos = math.ceil(comprimento_total_m / vao_max)
    passo = comprimento_total_m / n_vãos  # passo uniforme

    resultado = ResultadoSuportes(
        tag_linha=tag_linha,
        comprimento_total_m=comprimento_total_m,
        vao_maximo_calculado_m=vao_max,
    )

    posicoes: list[float] = [round(i * passo, 3) for i in range(n_vãos + 1)]
    # Garante que o último ponto é exatamente o fim da linha
    posicoes[-1] = comprimento_total_m

    for idx, pos in enumerate(posicoes):
        is_first = idx == 0
        is_last = idx == len(posicoes) - 1
        is_guia = (idx % 3 == 2) and not is_first and not is_last  # a cada 3°: guia

        if (is_first or is_last) and forcar_ancora_extremidades:
            tipo = TipoSuporteSL.LP3_ANCORA
            obs = "Ancoragem de extremidade — absorve reações de expansão térmica."
        elif is_guia:
            tipo = TipoSuporteSL.LP1_GUIA
            obs = "Guia lateral — permite dilatação axial, restringe deslocamento transversal."
        else:
            tipo = TipoSuporteSL.LP10_APOIO_SIMPLES
            obs = "Apoio simples / sapata de escorregamento — suporta peso, permite dilatação livre."

        vao = round(passo if not is_last else passo, 2)

        resultado.suportes.append(
            SuporteSL(
                id=f"S-{idx+1:02d}",
                tipo=tipo,
                posicao_m=pos,
                carga_kg=carga_por_suporte_kg,
                vao_m=vao,
                norma_referencia=f"{tipo.value} — Série L Petrobras",
                observacao=obs,
            )
        )

    return resultado
