"""
Base de Dados de Perfis W Laminados — ASTM A572 Grau 50
========================================================
Propriedades geométricas e mecânicas conforme:
  - AISC Steel Construction Manual, 16ª Edição (tabelas de perfis)
  - ABNT NBR 6355 / CBCA — Catálogo de Perfis Estruturais

Unidades do banco de dados:
  Dimensões lineares : mm
  Áreas              : cm²
  Momentos de inércia: cm⁴
  Módulos de seção   : cm³
  Raios de giração   : cm
  Massa linear       : kg/m

Perfis ordenados por Zx crescente → usados diretamente no algoritmo
de upsize automático (menor perfil suficiente primeiro).
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constantes do material ASTM A572 Gr. 50
# ---------------------------------------------------------------------------
FY: float = 345.0        # MPa  — tensão de escoamento
FU: float = 450.0        # MPa  — tensão de ruptura
E_ACO: float = 200_000.0 # MPa  — módulo de elasticidade


@dataclass(frozen=True)
class PerfilW:
    """Seção transversal de perfil W laminado.

    Parâmetros armazenados
    ----------------------
    nome  : designação (ex. "W200x36")
    d     : altura total da seção [mm]
    bf    : largura da mesa [mm]
    tf    : espessura da mesa [mm]
    tw    : espessura da alma [mm]
    A     : área da seção transversal [cm²]
    Ix    : momento de inércia — eixo forte [cm⁴]
    Sx    : módulo de resistência elástico — eixo forte [cm³]
    Zx    : módulo de resistência plástico — eixo forte [cm³]
    Iy    : momento de inércia — eixo fraco [cm⁴]
    ry    : raio de giração — eixo fraco [cm]
    peso  : massa linear [kg/m]

    Propriedades derivadas (calculadas via @property)
    -------------------------------------------------
    rx, h, J, Cw, rts — usadas nas verificações de flambagem.
    """

    nome: str
    d: float    # mm
    bf: float   # mm
    tf: float   # mm
    tw: float   # mm
    A: float    # cm²
    Ix: float   # cm⁴
    Sx: float   # cm³
    Zx: float   # cm³
    Iy: float   # cm⁴
    ry: float   # cm
    peso: float # kg/m

    # ------------------------------------------------------------------
    # Material (constantes de classe — ASTM A572 Gr.50)
    # ------------------------------------------------------------------
    @property
    def fy(self) -> float:
        return FY

    @property
    def fu(self) -> float:
        return FU

    @property
    def E(self) -> float:
        return E_ACO

    # ------------------------------------------------------------------
    # Derivadas geométricas
    # ------------------------------------------------------------------
    @property
    def rx(self) -> float:
        """Raio de giração eixo forte [cm]."""
        return math.sqrt(self.Ix / self.A)

    @property
    def h(self) -> float:
        """Altura livre da alma (d - 2·tf) [mm]."""
        return self.d - 2.0 * self.tf

    @property
    def J(self) -> float:
        """Constante de torção de St. Venant [cm⁴].

        Fórmula simplificada para perfil I duplo simétrico
        (despreza raios de concordância):
          J ≈ (2/3)·bf·tf³ + (1/3)·hw·tw³
        """
        bf_cm = self.bf / 10.0
        tf_cm = self.tf / 10.0
        tw_cm = self.tw / 10.0
        hw_cm = self.h  / 10.0
        return (2.0 / 3.0) * bf_cm * tf_cm**3 + (1.0 / 3.0) * hw_cm * tw_cm**3

    @property
    def Cw(self) -> float:
        """Constante de empenamento (warping) [cm⁶].

        Para I duplo simétrico:
          Cw = Iy · ho² / 4
        onde ho = d - tf (distância entre centróides das mesas).
        """
        ho_cm = (self.d - self.tf) / 10.0  # mm → cm
        return self.Iy * ho_cm**2 / 4.0

    @property
    def rts(self) -> float:
        """Raio efetivo para FLT [cm].

        rts² = √(Iy · Cw) / Sx
        """
        return math.sqrt(math.sqrt(self.Iy * self.Cw) / self.Sx)

    @property
    def ho(self) -> float:
        """Distância entre centróides das mesas [cm]."""
        return (self.d - self.tf) / 10.0

    # ------------------------------------------------------------------
    # Limites de esbeltez (NBR 8800:2008 / AISC 360-16, Seção B4)
    # ------------------------------------------------------------------
    @property
    def lambda_pf(self) -> float:
        """Esbeltez máxima da mesa — seção compacta: 0,38·√(E/fy)."""
        return 0.38 * math.sqrt(self.E / self.fy)

    @property
    def lambda_rf(self) -> float:
        """Esbeltez máxima da mesa — seção semicompacta: 1,0·√(E/fy)."""
        return 1.0 * math.sqrt(self.E / self.fy)

    @property
    def lambda_pw(self) -> float:
        """Esbeltez máxima da alma — seção compacta: 3,76·√(E/fy)."""
        return 3.76 * math.sqrt(self.E / self.fy)

    @property
    def lambda_rw(self) -> float:
        """Esbeltez máxima da alma — seção semicompacta: 5,70·√(E/fy)."""
        return 5.70 * math.sqrt(self.E / self.fy)

    @property
    def lambda_f(self) -> float:
        """Esbeltez real da mesa: bf / (2·tf)."""
        return self.bf / (2.0 * self.tf)

    @property
    def lambda_w(self) -> float:
        """Esbeltez real da alma: h / tw."""
        return self.h / self.tw

    @property
    def classe_mesa(self) -> str:
        lf = self.lambda_f
        if lf <= self.lambda_pf:
            return "Compacta"
        if lf <= self.lambda_rf:
            return "Semicompacta"
        return "Esbelta"

    @property
    def classe_alma(self) -> str:
        lw = self.lambda_w
        if lw <= self.lambda_pw:
            return "Compacta"
        if lw <= self.lambda_rw:
            return "Semicompacta"
        return "Esbelta"

    @property
    def is_compacta(self) -> bool:
        return (self.lambda_f <= self.lambda_pf and
                self.lambda_w <= self.lambda_pw)

    def __str__(self) -> str:
        return (
            f"{self.nome}  |  A={self.A:.1f}cm²  Ix={self.Ix:.0f}cm⁴  "
            f"Zx={self.Zx:.0f}cm³  ry={self.ry:.2f}cm  "
            f"peso={self.peso:.1f}kg/m"
        )


# ---------------------------------------------------------------------------
# Catálogo de Perfis — ASTM A572 Gr.50  (W séries, ordenados por Zx ↑)
# ---------------------------------------------------------------------------
# Fonte: AISC Steel Construction Manual, 16ª Edição
#        Perfis com designação métrica usada no Brasil (CBCA)
# ---------------------------------------------------------------------------
PERFIS_CATALOGADOS: tuple[PerfilW, ...] = (
    # ── W150 ────────────────────────────────────────────────────────────────
    PerfilW("W150x13",  d=148, bf=100, tf=7.1,  tw=4.3,  A=16.8,  Ix=688,    Sx=93.0,  Zx=105,   Iy=65.3,  ry=1.97, peso=13.0),
    PerfilW("W150x18",  d=153, bf=102, tf=9.3,  tw=5.8,  A=23.2,  Ix=1010,   Sx=132,   Zx=150,   Iy=88.5,  ry=1.95, peso=18.0),
    PerfilW("W150x24",  d=160, bf=102, tf=10.3, tw=6.6,  A=30.5,  Ix=1280,   Sx=159,   Zx=183,   Iy=109,   ry=1.89, peso=24.0),
    # ── W200 ────────────────────────────────────────────────────────────────
    PerfilW("W200x15",  d=200, bf=100, tf=7.2,  tw=4.3,  A=19.2,  Ix=1280,   Sx=128,   Zx=146,   Iy=61.2,  ry=1.79, peso=15.0),
    PerfilW("W200x22",  d=206, bf=102, tf=8.0,  tw=6.2,  A=28.6,  Ix=1940,   Sx=188,   Zx=215,   Iy=84.8,  ry=1.72, peso=22.0),
    PerfilW("W200x36",  d=201, bf=165, tf=10.2, tw=6.2,  A=45.7,  Ix=3440,   Sx=342,   Zx=378,   Iy=758,   ry=4.07, peso=36.0),
    PerfilW("W200x52",  d=206, bf=204, tf=12.6, tw=7.9,  A=66.1,  Ix=5260,   Sx=511,   Zx=570,   Iy=1770,  ry=5.17, peso=52.0),
    PerfilW("W200x71",  d=216, bf=206, tf=17.4, tw=10.2, A=90.7,  Ix=7650,   Sx=707,   Zx=800,   Iy=2620,  ry=5.36, peso=71.0),
    PerfilW("W200x100", d=229, bf=210, tf=23.7, tw=14.5, A=127,   Ix=11300,  Sx=987,   Zx=1120,  Iy=3880,  ry=5.53, peso=100.0),
    # ── W250 ────────────────────────────────────────────────────────────────
    PerfilW("W250x18",  d=251, bf=101, tf=7.3,  tw=4.8,  A=23.7,  Ix=2280,   Sx=181,   Zx=204,   Iy=62.4,  ry=1.62, peso=18.0),
    PerfilW("W250x25",  d=257, bf=102, tf=8.4,  tw=6.1,  A=32.1,  Ix=3060,   Sx=238,   Zx=274,   Iy=87.1,  ry=1.65, peso=25.0),
    PerfilW("W250x33",  d=258, bf=146, tf=9.1,  tw=6.1,  A=41.8,  Ix=3990,   Sx=309,   Zx=346,   Iy=328,   ry=2.80, peso=33.0),
    PerfilW("W250x49",  d=247, bf=202, tf=11.0, tw=7.4,  A=63.2,  Ix=7080,   Sx=573,   Zx=638,   Iy=1480,  ry=4.83, peso=49.0),
    PerfilW("W250x73",  d=253, bf=254, tf=14.2, tw=8.6,  A=93.0,  Ix=11400,  Sx=900,   Zx=1010,  Iy=3850,  ry=6.43, peso=73.0),
    PerfilW("W250x89",  d=260, bf=256, tf=17.3, tw=10.7, A=114,   Ix=14200,  Sx=1090,  Zx=1230,  Iy=4820,  ry=6.49, peso=89.0),
    # ── W310 ────────────────────────────────────────────────────────────────
    PerfilW("W310x21",  d=302, bf=101, tf=7.1,  tw=5.1,  A=26.9,  Ix=4090,   Sx=271,   Zx=304,   Iy=59.3,  ry=1.48, peso=21.0),
    PerfilW("W310x28",  d=309, bf=102, tf=8.9,  tw=6.0,  A=36.0,  Ix=5490,   Sx=355,   Zx=404,   Iy=80.1,  ry=1.49, peso=28.0),
    PerfilW("W310x39",  d=310, bf=165, tf=9.7,  tw=5.8,  A=50.1,  Ix=8440,   Sx=545,   Zx=607,   Iy=441,   ry=2.97, peso=39.0),
    PerfilW("W310x52",  d=317, bf=167, tf=13.2, tw=7.6,  A=66.6,  Ix=11900,  Sx=751,   Zx=848,   Iy=617,   ry=3.05, peso=52.0),
    PerfilW("W310x74",  d=310, bf=206, tf=16.3, tw=9.4,  A=94.2,  Ix=16600,  Sx=1070,  Zx=1200,  Iy=1540,  ry=4.04, peso=74.0),
    PerfilW("W310x97",  d=308, bf=305, tf=15.4, tw=9.9,  A=123,   Ix=22300,  Sx=1440,  Zx=1600,  Iy=7280,  ry=7.70, peso=97.0),
    # ── W360 ────────────────────────────────────────────────────────────────
    PerfilW("W360x33",  d=349, bf=127, tf=8.5,  tw=5.8,  A=41.9,  Ix=8260,   Sx=473,   Zx=531,   Iy=193,   ry=2.15, peso=33.0),
    PerfilW("W360x44",  d=352, bf=171, tf=9.8,  tw=6.9,  A=56.2,  Ix=12100,  Sx=688,   Zx=773,   Iy=490,   ry=2.95, peso=44.0),
    PerfilW("W360x57",  d=358, bf=172, tf=13.1, tw=7.9,  A=72.5,  Ix=16100,  Sx=900,   Zx=1020,  Iy=659,   ry=3.01, peso=57.0),
    PerfilW("W360x79",  d=354, bf=205, tf=16.8, tw=9.4,  A=101,   Ix=22800,  Sx=1290,  Zx=1440,  Iy=1540,  ry=3.90, peso=79.0),
    PerfilW("W360x110", d=360, bf=256, tf=19.9, tw=11.4, A=141,   Ix=33100,  Sx=1840,  Zx=2050,  Iy=3500,  ry=4.98, peso=110.0),
    PerfilW("W360x134", d=369, bf=257, tf=23.8, tw=13.1, A=171,   Ix=41600,  Sx=2250,  Zx=2530,  Iy=4360,  ry=5.05, peso=134.0),
    # ── W410 ────────────────────────────────────────────────────────────────
    PerfilW("W410x39",  d=399, bf=140, tf=8.8,  tw=6.4,  A=50.0,  Ix=16600,  Sx=831,   Zx=931,   Iy=304,   ry=2.47, peso=39.0),
    PerfilW("W410x54",  d=403, bf=177, tf=10.9, tw=7.5,  A=68.6,  Ix=23000,  Sx=1140,  Zx=1280,  Iy=628,   ry=3.03, peso=54.0),
    PerfilW("W410x75",  d=410, bf=179, tf=16.0, tw=9.7,  A=96.0,  Ix=33800,  Sx=1650,  Zx=1850,  Iy=938,   ry=3.13, peso=75.0),
    PerfilW("W410x100", d=415, bf=180, tf=21.1, tw=10.0, A=127,   Ix=45100,  Sx=2180,  Zx=2450,  Iy=1250,  ry=3.14, peso=100.0),
    # ── W460 ────────────────────────────────────────────────────────────────
    PerfilW("W460x52",  d=450, bf=152, tf=10.8, tw=7.6,  A=66.4,  Ix=35400,  Sx=1570,  Zx=1760,  Iy=345,   ry=2.28, peso=52.0),
    PerfilW("W460x74",  d=457, bf=190, tf=14.5, tw=9.0,  A=94.6,  Ix=55500,  Sx=2430,  Zx=2720,  Iy=1080,  ry=3.38, peso=74.0),
    PerfilW("W460x97",  d=466, bf=193, tf=19.0, tw=11.4, A=124,   Ix=74600,  Sx=3200,  Zx=3600,  Iy=1450,  ry=3.42, peso=97.0),
    # ── W530 ────────────────────────────────────────────────────────────────
    PerfilW("W530x66",  d=525, bf=165, tf=11.4, tw=8.9,  A=84.5,  Ix=61200,  Sx=2330,  Zx=2600,  Iy=407,   ry=2.19, peso=66.0),
    PerfilW("W530x82",  d=528, bf=209, tf=13.3, tw=9.5,  A=104,   Ix=86700,  Sx=3290,  Zx=3680,  Iy=2390,  ry=4.80, peso=82.0),
    PerfilW("W530x109", d=539, bf=213, tf=18.3, tw=11.6, A=139,   Ix=117000, Sx=4340,  Zx=4920,  Iy=3290,  ry=4.87, peso=109.0),
    # ── W610 ────────────────────────────────────────────────────────────────
    PerfilW("W610x82",  d=599, bf=178, tf=12.8, tw=10.0, A=104,   Ix=99200,  Sx=3310,  Zx=3710,  Iy=602,   ry=2.40, peso=82.0),
    PerfilW("W610x101", d=603, bf=228, tf=14.9, tw=10.5, A=129,   Ix=131000, Sx=4340,  Zx=4870,  Iy=3520,  ry=5.22, peso=101.0),
    PerfilW("W610x125", d=612, bf=229, tf=19.6, tw=11.9, A=159,   Ix=168000, Sx=5490,  Zx=6160,  Iy=4710,  ry=5.44, peso=125.0),
)

# Ordena por Zx crescente (garante upsize no sentido capacidade crescente)
PERFIS_CATALOGADOS = tuple(sorted(PERFIS_CATALOGADOS, key=lambda p: p.Zx))
