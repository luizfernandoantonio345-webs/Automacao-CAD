"""
Sistema de Cotação Automática para Isométricos
==============================================
Implementa:
  • Cotação ponta-a-ponta (P-P) — fabricação
  • Cotação centro-a-centro (C-C) — montagem
  • Posicionamento automático de linhas de cota
  • Simbologias de seta de cota (norma ISO)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from .geometry import Ponto3D


@dataclass
class Cota:
    """Especificação de uma dimensão (cota) no desenho."""
    id: str
    p1_iso: tuple[float, float]   # ponto inicial isométrico [mm]
    p2_iso: tuple[float, float]   # ponto final isométrico [mm]
    valor: float                   # valor da cota [m] ou [mm]
    tipo: Literal["P-P", "C-C"]   # ponta-a-ponta ou centro-a-centro
    unidade: str = "mm"           # "mm" ou "m"
    offset_distancia: float = 25.0 # distância da linha de cota ao objeto [mm]
    offset_texto: float = 5.0     # distância do texto ao ponto da cota [mm]
    altura_texto: float = 3.0
    prefixo: str = ""
    sufixo: str = ""

    def propriedades_cota_iso(self) -> tuple[float, float, float, float]:
        """Calcula a linha de cota paralela deslocada.

        Retorna (x1, y1, x2, y2) — linha deslocada no iso.
        """
        x1, y1 = self.p1_iso
        x2, y2 = self.p2_iso

        # Vetor do objeto
        dx = x2 - x1
        dy = y2 - y1
        dist_obj = math.sqrt(dx**2 + dy**2)

        if dist_obj < 1e-6:
            # Pontos coincidentes
            return (x1, y1, x2, y2)

        # Vetor perpendicular (rotação 90° CCW)
        px = -dy / dist_obj
        py = dx / dist_obj

        # Desloca pela distância offset
        offset = self.offset_distancia
        x1_cota = x1 + px * offset
        y1_cota = y1 + py * offset
        x2_cota = x2 + px * offset
        y2_cota = y2 + py * offset

        return (x1_cota, y1_cota, x2_cota, y2_cota)

    def posicao_texto_cota(self) -> tuple[float, float]:
        """Calcula a posição do texto da cota.

        Texto é posicionado no ponto médio da linha de cota, um pouco acima.
        """
        x1, y1, x2, y2 = self.propriedades_cota_iso()

        # Ponto médio
        xm = (x1 + x2) / 2.0
        ym = (y1 + y2) / 2.0

        # Pequeno deslocamento vertical para legibilidade
        return (xm, ym + self.offset_texto)

    def texto_dimensao(self) -> str:
        """Gera a string de dimensão com prefixo e sufixo."""
        if self.unidade == "mm":
            if self.valor < 1.0:
                texto = f"{self.valor * 1000:.0f}"
            else:
                texto = f"{self.valor:.2f}"
        else:  # metros
            texto = f"{self.valor:.3f}" if self.valor < 1 else f"{self.valor:.2f}"

        return f"{self.prefixo}{texto}{self.sufixo}"


class GeradorCotas:
    """Utilitário para gerar cotas automaticamente a partir de tubulação."""

    @staticmethod
    def cotacao_tubo_pp(nome: str, p1_3d: Ponto3D, p2_3d: Ponto3D) -> Cota:
        """Gera cota ponta-a-ponta para um tubo.

        Apenas a distância efetiva entre as extremidades é cotada.
        """
        p1_iso = p1_3d.para_isometrico()
        p2_iso = p2_3d.para_isometrico()
        comprimento = p1_3d.distancia_para(p2_3d)  # [m]

        return Cota(
            id=f"{nome}_PP",
            p1_iso=p1_iso,
            p2_iso=p2_iso,
            valor=comprimento,
            tipo="P-P",
            unidade="mm",
            prefixo="",
            sufixo=" mm",
        )

    @staticmethod
    def cotacao_tubo_cc(nome: str, p1_3d: Ponto3D, p2_3d: Ponto3D) -> Cota:
        """Gera cota centro-a-centro para um tubo (para montagem).

        Usa os mesmos pontos, mas acrescenta "C-C" no sufixo e ajusta offset.
        """
        p1_iso = p1_3d.para_isometrico()
        p2_iso = p2_3d.para_isometrico()
        comprimento = p1_3d.distancia_para(p2_3d)  # [m]

        return Cota(
            id=f"{nome}_CC",
            p1_iso=p1_iso,
            p2_iso=p2_iso,
            valor=comprimento,
            tipo="C-C",
            unidade="mm",
            prefixo="",
            sufixo=" (C-C)",
            offset_distancia=40.0,  # Mais distante para não sobrepor P-P
        )

    @staticmethod
    def cotacao_diametro(nome: str, centro_3d: Ponto3D, diametro_mm: float, orientacao: str = "H") -> Optional[Cota]:
        """Gera cota de diâmetro para um tubo.

        orientacao: "H" (horizontal) ou "V" (vertical) na isometria.
        """
        centro_iso = centro_3d.para_isometrico()
        cx, cy = centro_iso

        if orientacao == "H":
            p1_iso = (cx - diametro_mm/2, cy)
            p2_iso = (cx + diametro_mm/2, cy)
        else:
            p1_iso = (cx, cy - diametro_mm/2)
            p2_iso = (cx, cy + diametro_mm/2)

        return Cota(
            id=f"{nome}_DIAM",
            p1_iso=p1_iso,
            p2_iso=p2_iso,
            valor=diametro_mm,
            tipo="P-P",
            unidade="mm",
            prefixo="Ø ",
            sufixo=" mm",
            offset_distancia=15.0,
            altura_texto=2.5,
        )


class EstilosCota:
    """Estilos e padrões para desenhos de cotas."""

    # Seta padrão ISO (triângulo preenchido)
    SETA_TAMANHO = 2.0  # mm

    @staticmethod
    def desenhar_seta(ponto_iso: tuple[float, float], angulo: float) -> list[tuple[float, float]]:
        """Gera pontos do triângulo de seta para o DXF.

        ponto_iso: ponto de inserção da seta
        angulo: ângulo de rotação [graus]
        """
        px, py = ponto_iso
        ang_rad = math.radians(angulo)
        cos_a = math.cos(ang_rad)
        sin_a = math.sin(ang_rad)

        # Triângulo (local)
        p1_local = (EstilosCota.SETA_TAMANHO, 0)
        p2_local = (-EstilosCota.SETA_TAMANHO * 0.5, EstilosCota.SETA_TAMANHO * 0.5)
        p3_local = (-EstilosCota.SETA_TAMANHO * 0.5, -EstilosCota.SETA_TAMANHO * 0.5)

        # Rotaciona
        def rot(local_x, local_y):
            x = local_x * cos_a - local_y * sin_a + px
            y = local_x * sin_a + local_y * cos_a + py
            return (x, y)

        return [rot(p1_local[0], p1_local[1]), rot(p2_local[0], p2_local[1]), rot(p3_local[0], p3_local[1])]


__all__ = [
    "Cota",
    "GeradorCotas",
    "EstilosCota",
]
