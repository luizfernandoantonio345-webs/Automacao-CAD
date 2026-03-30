"""
Módulo NBR 8800:2008 — Verificação de Perfis W em Aço ASTM A572 Gr.50
======================================================================
Implementa os Estados Limites Últimos (ELU) e Estados Limites de Serviço
(ELS) conforme a NBR 8800:2008 (Projeto de Estruturas de Aço e de Estruturas
Mistas de Aço e Concreto de Edifícios).

Método de cálculo: LRFD (Load and Resistance Factor Design).
"""

from .profiles import PerfilW, PERFIS_CATALOGADOS
from .calculista import (
    EntradaCalculo,
    ResultadoVerificacao,
    Calculista,
)
from .relatorio import gerar_relatorio_markdown, gerar_relatorio_html

__all__ = [
    "PerfilW",
    "PERFIS_CATALOGADOS",
    "EntradaCalculo",
    "ResultadoVerificacao",
    "Calculista",
    "gerar_relatorio_markdown",
    "gerar_relatorio_html",
]
