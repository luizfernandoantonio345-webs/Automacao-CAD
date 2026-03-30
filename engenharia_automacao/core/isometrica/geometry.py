"""
Motor de Isométricos de Tubulação — Geometria 3D Base
=====================================================
Estruturas de dados para representação de tubulação 3D:
  • Pontos, Vetores, Linhas 3D
  • Tubos (cilindros) com diâmetro e comprimento
  • Válvulas e componentes simbólicos
  • Suportes e fixações

Transformação isométrica para projeção em 2D (para DXF).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


@dataclass(frozen=True)
class Ponto3D:
    """Ponto no espaço 3D [m]."""
    x: float
    y: float
    z: float

    def __add__(self, outro: Ponto3D) -> Ponto3D:
        return Ponto3D(self.x + outro.x, self.y + outro.y, self.z + outro.z)

    def __sub__(self, outro: Ponto3D) -> Ponto3D:
        return Ponto3D(self.x - outro.x, self.y - outro.y, self.z - outro.z)

    def __mul__(self, escalar: float) -> Ponto3D:
        return Ponto3D(self.x * escalar, self.y * escalar, self.z * escalar)

    def distancia_para(self, outro: Ponto3D) -> float:
        """Distância euclidiana [m]."""
        dx, dy, dz = self.x - outro.x, self.y - outro.y, self.z - outro.z
        return math.sqrt(dx**2 + dy**2 + dz**2)

    def para_isometrico(self) -> tuple[float, float]:
        """Transforma para coordenadas isométricas [mm] no plano 2D.

        Projeção isométrica padrão (eixos a 120°):
          x_iso = x - z
          y_iso = (x + z) / 2 + y
        com escala 1:1.
        """
        # Conversão de metros para mm
        x_mm = self.x * 1000.0
        y_mm = self.y * 1000.0
        z_mm = self.z * 1000.0

        # Transformação isométrica
        x_iso = x_mm - z_mm
        y_iso = (x_mm + z_mm) / 2.0 + y_mm

        return (x_iso, y_iso)


@dataclass(frozen=True)
class Vetor3D:
    """Vetor no espaço 3D (sem posição)."""
    dx: float
    dy: float
    dz: float

    def magnitude(self) -> float:
        return math.sqrt(self.dx**2 + self.dy**2 + self.dz**2)

    def normalizar(self) -> Vetor3D:
        mag = self.magnitude()
        if mag < 1e-9:
            return Vetor3D(0, 0, 0)
        return Vetor3D(self.dx / mag, self.dy / mag, self.dz / mag)

    def dot(self, outro: Vetor3D) -> float:
        return self.dx * outro.dx + self.dy * outro.dy + self.dz * outro.dz

    def cross(self, outro: Vetor3D) -> Vetor3D:
        return Vetor3D(
            self.dy * outro.dz - self.dz * outro.dy,
            self.dz * outro.dx - self.dx * outro.dz,
            self.dx * outro.dy - self.dy * outro.dx,
        )


class TipoValvula(Enum):
    """Tipos de válvulas e componentes."""
    GAVETA = "gaveta"          # Gate valve
    GLOBO = "globo"            # Globe valve
    RETENCAO = "retenção"      # Check valve
    PURGADOR = "purgador"      # Steam trap
    BUTTERFLY = "borboleta"    # Butterfly valve
    BOLA = "bola"              # Ball valve
    TEE = "tee"                # Tee fitting
    COTOVELO = "cotovelo"      # Elbow fitting (90°)
    REDUTOR = "redutor"        # Reducer


@dataclass
class Tubo:
    """Segmento de tubo de P1 a P2."""
    nome: str
    P1: Ponto3D
    P2: Ponto3D
    diametro: float          # m
    material: str = "Aço Carbono"
    label: Optional[str] = None

    @property
    def comprimento(self) -> float:
        """Comprimento [m]."""
        return self.P1.distancia_para(self.P2)

    @property
    def vetor(self) -> Vetor3D:
        """Vetor direção do tubo."""
        dx = self.P2.x - self.P1.x
        dy = self.P2.y - self.P1.y
        dz = self.P2.z - self.P1.z
        return Vetor3D(dx, dy, dz)

    @property
    def ponto_medio(self) -> Ponto3D:
        return Ponto3D(
            (self.P1.x + self.P2.x) / 2,
            (self.P1.y + self.P2.y) / 2,
            (self.P1.z + self.P2.z) / 2,
        )


@dataclass
class Valvula:
    """Componente de válvula em posição 3D."""
    nome: str
    tipo: TipoValvula
    posicao: Ponto3D
    diametro: float          # m
    direcao: Optional[Vetor3D] = None  # direção de passagem
    label: Optional[str] = None


@dataclass
class Suporte:
    """Suporte estrutural (pé-de-amigo, guia, etc.)."""
    nome: str
    posicao: Ponto3D
    tipo_suporte: str = "pé-de-amigo"
    diametro_tuberia: float = 0.025  # padrão 25 mm


class SistemaIsometrico:
    """Base de dados e gerenciador de tubulação 3D.

    Responsabilidades:
      • Armazenar tubos, válvulas, suportes
      • Calcular vãos livres
      • Identificar pontos de suportação necessários
      • Gerar BOM
    """

    def __init__(self):
        self.tubos: list[Tubo] = []
        self.valvulas: list[Valvula] = []
        self.suportes: list[Suporte] = []
        self.acessorios: dict = field(default_factory=dict)

    def adicionar_tubo(self, tubo: Tubo) -> None:
        """Adiciona um segmento de tubo."""
        self.tubos.append(tubo)

    def adicionar_valvula(self, valvula: Valvula) -> None:
        self.valvulas.append(valvula)

    def adicionar_suporte(self, suporte: Suporte) -> None:
        self.suportes.append(suporte)

    def calcular_vaos_livres(self, vao_maximo: float = 2.0) -> list[dict]:
        """Identifica vãos livres > vao_maximo [m] e recomenda suportes.

        Algoritmo:
          1. Percorre sequência de tubos
          2. Para cada tubo horizontal sem suporte, calcula comprimento
          3. Se L > vao_maximo, insere suporte no meio

        Retorna lista de recomendações.
        """
        recomendacoes = []

        for i, tubo in enumerate(self.tubos):
            # Vetor do tubo
            v = tubo.vetor
            mag = tubo.comprimento

            # Verifica se é horizontal (dz ~ 0)
            if abs(v.dz) < 0.1 and mag > vao_maximo:
                # Vão livre significativo — recomenda suporte
                ponto_suporte = tubo.ponto_medio
                suporte_recomendado = Suporte(
                    nome=f"Suporte-{len(self.suportes) + 1}",
                    posicao=ponto_suporte,
                    tipo_suporte="pé-de-amigo",
                    diametro_tuberia=tubo.diametro,
                )
                recomendacoes.append({
                    "tubo": tubo.nome,
                    "vao_livre": mag,
                    "suporte": suporte_recomendado,
                    "motivo": f"Vão livre > {vao_maximo}m",
                })

                self.adicionar_suporte(suporte_recomendado)

        return recomendacoes

    def gerar_bom(self) -> dict:
        """Gera a lista de materiais (BOM) para toda a tubulação.

        Retorna:
          {
            'tubos': [{'diametro': ..., 'material': ..., 'comprimento_total': ...}, ...],
            'valvulas': [{'tipo': ..., 'diametro': ..., 'quantidade': ...}, ...],
            'suportes': [{'tipo': ..., 'quantidade': ...}, ...],
          }
        """
        # Agrupamento de tubos por diâmetro
        tubos_por_diametro = {}
        for tubo in self.tubos:
            chave = (tubo.diametro, tubo.material)
            if chave not in tubos_por_diametro:
                tubos_por_diametro[chave] = []
            tubos_por_diametro[chave].append(tubo.comprimento)

        bom_tubos = []
        for (diametro, material), comprimentos in tubos_por_diametro.items():
            bom_tubos.append({
                'diametro_m': diametro,
                'diametro_mm': diametro * 1000,
                'material': material,
                'quantidade': len(comprimentos),
                'comprimento_total': sum(comprimentos),
                'comprimento_unitario_medio': sum(comprimentos) / len(comprimentos),
            })

        # Agrupamento de válvulas por tipo e diâmetro
        valvulas_por_tipo = {}
        for valv in self.valvulas:
            chave = (valv.tipo.value, valv.diametro)
            valvulas_por_tipo[chave] = valvulas_por_tipo.get(chave, 0) + 1

        bom_valvulas = []
        for (tipo, diametro), qtd in valvulas_por_tipo.items():
            bom_valvulas.append({
                'tipo': tipo,
                'diametro_m': diametro,
                'diametro_mm': diametro * 1000,
                'quantidade': qtd,
            })

        # Agrupamento de suportes
        suportes_por_tipo = {}
        for sup in self.suportes:
            chave = sup.tipo_suporte
            suportes_por_tipo[chave] = suportes_por_tipo.get(chave, 0) + 1

        bom_suportes = []
        for tipo, qtd in suportes_por_tipo.items():
            bom_suportes.append({
                'tipo': tipo,
                'quantidade': qtd,
            })

        return {
            'tubos': bom_tubos,
            'valvulas': bom_valvulas,
            'suportes': bom_suportes,
        }

    def extents(self) -> tuple[float, float, float, float, float, float]:
        """Retorna limites da tubulação [min_x, min_y, min_z, max_x, max_y, max_z] [m]."""
        todos_pontos = [t.P1 for t in self.tubos] + [t.P2 for t in self.tubos]
        todos_pontos += [v.posicao for v in self.valvulas]
        todos_pontos += [s.posicao for s in self.suportes]

        if not todos_pontos:
            return (0, 0, 0, 0, 0, 0)

        xs = [p.x for p in todos_pontos]
        ys = [p.y for p in todos_pontos]
        zs = [p.z for p in todos_pontos]

        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


__all__ = [
    "Ponto3D",
    "Vetor3D",
    "TipoValvula",
    "Tubo",
    "Valvula",
    "Suporte",
    "SistemaIsometrico",
]
