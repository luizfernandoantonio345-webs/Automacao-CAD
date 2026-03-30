"""
Simulador de Simbologia de Válvulas e Componentes
=================================================
Desenha símbolos padrão em isométrico para válvulas, tees, cotovelos, etc.
Cada símbolo é uma rotina que retorna pontos DXF para desenhar.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from .geometry import Ponto3D, Vetor3D, TipoValvula


@dataclass
class ElementoDXF:
    """Descritor de um elemento para desenho em DXF."""
    tipo: str           # "LINE", "POLYLINE", "CIRCLE", "TEXT", "ARC"
    pontos: list[tuple[float, float]]  # coordenadas 2D isométricas (mm)
    radius: float = 0.0
    texto: str = ""
    altura_texto: float = 3.0
    angulo: float = 0.0
    grupo: str = "0"   # camada/grupo
    cor: int = 256     # 256 = por camada (bylayer)


class SimbologiaValvulas:
    """Biblioteca de símbolos padrão para válvulas em isométrico."""

    ESCALA_SIMBOLO = 15.0  # mm (tamanho padrão do símbolo)

    @staticmethod
    def _linha_simbolo(P1: tuple[float, float], P2: tuple[float, float]) -> ElementoDXF:
        return ElementoDXF(tipo="LINE", pontos=[P1, P2], grupo="Valvulas")

    @staticmethod
    def _circulo_simbolo(centro: tuple[float, float], raio: float) -> ElementoDXF:
        return ElementoDXF(tipo="CIRCLE", pontos=[centro], radius=raio, grupo="Valvulas")

    @staticmethod
    def _polilinea_simbolo(pontos: list[tuple[float, float]]) -> ElementoDXF:
        return ElementoDXF(tipo="POLYLINE", pontos=pontos, grupo="Valvulas")

    @classmethod
    def gaveta(cls, px: float, py: float) -> list[ElementoDXF]:
        """Símbolo de válvula de gaveta — losango com linha cruzada.

        □ com / cruzando — representa a gaveta retraída.
        """
        centro = (px, py)
        r = cls.ESCALA_SIMBOLO

        # Losango
        pontos_losango = [
            (px - r, py),
            (px, py + r),
            (px + r, py),
            (px, py - r),
            (px - r, py),
        ]

        elementos = [
            ElementoDXF(tipo="POLYLINE", pontos=pontos_losango, grupo="Valvulas", cor=1),
            # Linha cruzando (representa trilho da gaveta)
            ElementoDXF(tipo="LINE", pontos=[(px - r*0.7, py - r*0.7), (px + r*0.7, py + r*0.7)], grupo="Valvulas", cor=1),
        ]
        return elementos

    @classmethod
    def globo(cls, px: float, py: float) -> list[ElementoDXF]:
        """Símbolo de válvula de globo — círculo com linha horizontal.

        ◎ — representa a restrição de orifício (globo).
        """
        centro = (px, py)
        r = cls.ESCALA_SIMBOLO

        elementos = [
            ElementoDXF(tipo="CIRCLE", pontos=[centro], radius=r, grupo="Valvulas", cor=3),
            ElementoDXF(tipo="LINE", pontos=[(px - r, py), (px + r, py)], grupo="Valvulas", cor=3),
        ]
        return elementos

    @classmethod
    def retencao(cls, px: float, py: float, angulo_saida: float = 0.0) -> list[ElementoDXF]:
        """Símbolo de válvula de retenção — triângulo com linha.

        ▷ — mola/pêndulo impede refluxo.
        """
        r = cls.ESCALA_SIMBOLO

        # Triângulo apontando para a direção de passagem
        cos_a = math.cos(math.radians(angulo_saida))
        sin_a = math.sin(math.radians(angulo_saida))

        # Pontos do triângulo em coordenadas locais
        p1_local = (r, 0)
        p2_local = (-r*0.5, r*0.7)
        p3_local = (-r*0.5, -r*0.7)

        # Rotaciona e translada
        def rotacionar(local_x, local_y):
            x = local_x * cos_a - local_y * sin_a + px
            y = local_x * sin_a + local_y * cos_a + py
            return (x, y)

        p1 = rotacionar(p1_local[0], p1_local[1])
        p2 = rotacionar(p2_local[0], p2_local[1])
        p3 = rotacionar(p3_local[0], p3_local[1])

        elementos = [
            ElementoDXF(tipo="POLYLINE", pontos=[p1, p2, p3, p1], grupo="Valvulas", cor=5),
        ]
        return elementos

    @classmethod
    def purgador(cls, px: float, py: float) -> list[ElementoDXF]:
        """Símbolo de purgador de ar — círculo com cruz.

        ⊕ — dreno de vapor/água.
        """
        centro = (px, py)
        r = cls.ESCALA_SIMBOLO

        elementos = [
            ElementoDXF(tipo="CIRCLE", pontos=[centro], radius=r, grupo="Valvulas", cor=2),
            ElementoDXF(tipo="LINE", pontos=[(px - r, py), (px + r, py)], grupo="Valvulas", cor=2),
            ElementoDXF(tipo="LINE", pontos=[(px, py - r), (px, py + r)], grupo="Valvulas", cor=2),
        ]
        return elementos

    @classmethod
    def tee(cls, px: float, py: float, angulo_lateral: float = 90.0) -> list[ElementoDXF]:
        """Símbolo de tee — três linhas em junção.

        T ou ⊥ — junção de três tubulações.
        """
        r = cls.ESCALA_SIMBOLO

        # Linha principal (horizontal)
        linha_h = ElementoDXF(tipo="LINE", pontos=[(px - r, py), (px + r, py)], grupo="Conexoes", cor=7)

        # Linha lateral (vertical)
        angulo_rad = math.radians(angulo_lateral)
        x_lat = r * math.cos(angulo_rad)
        y_lat = r * math.sin(angulo_rad)
        linha_v = ElementoDXF(tipo="LINE", pontos=[(px, py), (px + x_lat, py + y_lat)], grupo="Conexoes", cor=7)

        return [linha_h, linha_v]

    @classmethod
    def cotovelo(cls, px: float, py: float, angulo_entrada: float = 0.0, angulo_saida: float = 90.0) -> list[ElementoDXF]:
        """Símbolo de cotovelo 90° — duas linhas em ângulo reto.

        ⌐ ou ⌞ — mudança de direção de 90°.
        """
        r = cls.ESCALA_SIMBOLO

        # Linha 1 (entrada)
        cos_e = math.cos(math.radians(angulo_entrada))
        sin_e = math.sin(math.radians(angulo_entrada))
        p1 = (px - r * cos_e, py - r * sin_e)

        # Ponto de junção (cotovelo)
        pc = (px, py)

        # Linha 2 (saída)
        cos_s = math.cos(math.radians(angulo_saida))
        sin_s = math.sin(math.radians(angulo_saida))
        p2 = (px + r * cos_s, py + r * sin_s)

        elementos = [
            ElementoDXF(tipo="LINE", pontos=[p1, pc], grupo="Conexoes", cor=7),
            ElementoDXF(tipo="LINE", pontos=[pc, p2], grupo="Conexoes", cor=7),
        ]
        return elementos

    @classmethod
    def redutor(cls, px: float, py: float, diametro_entrada: float, diametro_saida: float, orientation: str = "H") -> list[ElementoDXF]:
        """Símbolo de redutor — duas linhas convergentes.

        ⧳ — redução de diâmetro.
        """
        r = cls.ESCALA_SIMBOLO
        r1 = r * diametro_entrada / (diametro_entrada + diametro_saida)
        r2 = r * diametro_saida / (diametro_entrada + diametro_saida)

        if orientation == "H":  # Horizontal
            p1_sup = (px - r, py + r1)
            p1_inf = (px - r, py - r1)
            p2_sup = (px + r, py + r2)
            p2_inf = (px + r, py - r2)
        else:  # Vertical
            p1_sup = (px - r1, py - r)
            p1_inf = (px + r1, py - r)
            p2_sup = (px - r2, py + r)
            p2_inf = (px + r2, py + r)

        elementos = [
            ElementoDXF(tipo="LINE", pontos=[p1_sup, p2_sup], grupo="Conexoes", cor=7),
            ElementoDXF(tipo="LINE", pontos=[p1_inf, p2_inf], grupo="Conexoes", cor=7),
        ]
        return elementos

    @classmethod
    def gerar_simbolo(cls, tipo: TipoValvula, px: float, py: float, **kwargs) -> list[ElementoDXF]:
        """Factory method — gera o símbolo apropriado para o tipo de válvula.

        Parâmetros opcionais (kwargs):
          - angulo_saida (para retenção)
          - angulo_lateral (para tee)
          - angulo_entrada, angulo_saida (para cotovelo)
          - diametro_entrada, diametro_saida (para redutor)
        """
        if tipo == TipoValvula.GAVETA:
            return cls.gaveta(px, py)
        elif tipo == TipoValvula.GLOBO:
            return cls.globo(px, py)
        elif tipo == TipoValvula.RETENCAO:
            angulo = kwargs.get("angulo_saida", 0.0)
            return cls.retencao(px, py, angulo)
        elif tipo == TipoValvula.PURGADOR:
            return cls.purgador(px, py)
        elif tipo == TipoValvula.TEE:
            angulo = kwargs.get("angulo_lateral", 90.0)
            return cls.tee(px, py, angulo)
        elif tipo == TipoValvula.COTOVELO:
            entrada = kwargs.get("angulo_entrada", 0.0)
            saida = kwargs.get("angulo_saida", 90.0)
            return cls.cotovelo(px, py, entrada, saida)
        elif tipo == TipoValvula.REDUTOR:
            de = kwargs.get("diametro_entrada", 0.05)
            ds = kwargs.get("diametro_saida", 0.025)
            orient = kwargs.get("orientation", "H")
            return cls.redutor(px, py, de, ds, orient)
        else:
            # Fallback: círculo simples
            return [ElementoDXF(tipo="CIRCLE", pontos=[(px, py)], radius=cls.ESCALA_SIMBOLO, grupo="Default")]


__all__ = [
    "ElementoDXF",
    "SimbologiaValvulas",
]
