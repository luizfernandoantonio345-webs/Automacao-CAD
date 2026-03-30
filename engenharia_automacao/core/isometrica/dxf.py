"""
Gerador de Desenhos DXF — Isométricos de Tubulação
==================================================
Cria arquivos DXF compatíveis com AutoCAD, LibreCAD, etc.

Formato: DXF ASCII (formato legível, compatível com todas as versões).
Gera um arquivo com:
  • Tubos em isométrico
  • Símbolos de válvulas
  • Linhas de cota (ponta-a-ponta e centro-a-centro)
  • Suportes estruturais
  • Bloco de BOM no cabeçalho

Especificação: DXF versão 12 (R2000 é compatível também).
"""

from __future__ import annotations

import math
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO

from .geometry import (
    SistemaIsometrico,
    Tubo,
    Valvula,
    Suporte,
    Ponto3D,
)
from .simbologia import SimbologiaValvulas, ElementoDXF
from .cotacao import Cota, EstilosCota, GeradorCotas


class GeradorDXF:
    """Motor de geração de desenhos DXF (formato ASCII)."""

    ESCALA_SISTEMA = 1.0  # 1:1 no desenho (dimensões em mm)
    LARGURA_LINHA_TUBO = 0.5  # mm
    LARGURA_LINHA_COTA = 0.25  # mm
    ALTURA_TEXTO_PADRAO = 3.0  # mm

    def __init__(self, sistema: SistemaIsometrico, titulo: str = "Isométrico de Tubulação"):
        self.sistema = sistema
        self.titulo = titulo
        self.proxima_handle = 256  # Começa do 256 (maior que espaço reservado)
        self.cotas: list[Cota] = []
        self.elementos_dxf: list[ElementoDXF] = []

    def _proximo_handle(self) -> str:
        """Aloca um handle único para cada entidade DXF."""
        self.proxima_handle += 1
        return f"{self.proxima_handle:X}"  # Hexadecimal

    def _escrever_header(self, f: TextIO) -> None:
        """Escreve a seção HEADER do DXF."""
        f.write("0\n")
        f.write("SECTION\n")
        f.write("2\n")
        f.write("HEADER\n")

        # Parâmetros de header mínimos
        f.write("9\n$ACADVER\n1\nAC1015\n")  # DXF versão 2000
        f.write("9\n$EXTMIN\n10\n-1000.0\n20\n-1000.0\n30\n0.0\n")
        f.write("9\n$EXTMAX\n10\n5000.0\n20\n5000.0\n30\n0.0\n")

        f.write("0\n")
        f.write("ENDSEC\n")

    def _escrever_tables(self, f: TextIO) -> None:
        """Escreve tabelas de estilos (TABLES)."""
        f.write("0\n")
        f.write("SECTION\n")
        f.write("2\n")
        f.write("TABLES\n")

        # Tabela LTYPE (estilos de linha)
        f.write("0\nTABLE\n2\nLTYPE\n70\n1\n")
        f.write("0\nLTYPE\n2\nCONTINUOUS\n70\n0\n72\n0\n73\n0\n40\n0.0\n")
        f.write("0\nENDTAB\n")

        # Tabela LAYER (camadas)
        camadas = ["Tubos", "Valvulas", "Conexoes", "Suportes", "Cotas", "BOM", "0"]
        f.write("0\nTABLE\n2\nLAYER\n70\n" + str(len(camadas)) + "\n")
        for nome_camada in camadas:
            f.write(f"0\nLAYER\n2\n{nome_camada}\n70\n0\n62\n7\n6\nCONTINUOUS\n")
        f.write("0\nENDTAB\n")

        # Tabela STYLE (estilos de texto)
        f.write("0\nTABLE\n2\nSTYLE\n70\n1\n")
        f.write("0\nSTYLE\n2\nSTANDARD\n70\n0\n40\n0.0\n41\n1.0\n50\n0.0\n71\n0\n")
        f.write("0\nENDTAB\n")

        f.write("0\n")
        f.write("ENDSEC\n")

    def _escrever_tubos(self, f: TextIO) -> None:
        """Escreve os segmentos de tubo como linhas no ENTITIES."""
        for i, tubo in enumerate(self.sistema.tubos):
            p1_iso = tubo.P1.para_isometrico()
            p2_iso = tubo.P2.para_isometrico()

            # Retorna handle
            handle = self._proximo_handle()
            f.write(f"0\nLINE\n5\n{handle}\n")
            f.write("8\nTubos\n62\n1\n")  # Cor: vermelho
            f.write(f"10\n{p1_iso[0]:.2f}\n20\n{p1_iso[1]:.2f}\n30\n0.0\n")
            f.write(f"11\n{p2_iso[0]:.2f}\n21\n{p2_iso[1]:.2f}\n31\n0.0\n")
            f.write("39\n" + str(int(self.LARGURA_LINHA_TUBO * 100)) + "\n")  # Largura (em 1/100 mm)

            # Se há label, adiciona texto
            if tubo.label:
                centro = tubo.ponto_medio
                centro_iso = centro.para_isometrico()
                handle = self._proximo_handle()
                f.write(f"0\nTEXT\n5\n{handle}\n")
                f.write("8\nTubos\n")
                f.write(f"10\n{centro_iso[0]:.2f}\n20\n{centro_iso[1]:.2f}\n30\n0.0\n")
                f.write(f"40\n{self.ALTURA_TEXTO_PADRAO:.2f}\n")
                f.write(f"1\n{tubo.label}\n")
                f.write("50\n0.0\n7\nSTANDARD\n")

    def _escrever_valvulas(self, f: TextIO) -> None:
        """Escreve símbolos de válvulas."""
        for valv in self.sistema.valvulas:
            px, py = valv.posicao.para_isometrico()

            # Gera símbolo
            simbolo_elementos = SimbologiaValvulas.gerar_simbolo(
                valv.tipo, px, py,
                angulo_saida=0.0,  # padrão
            )

            for elem in simbolo_elementos:
                if elem.tipo == "LINE":
                    handle = self._proximo_handle()
                    f.write(f"0\nLINE\n5\n{handle}\n")
                    f.write(f"8\n{elem.grupo}\n62\n{elem.cor}\n")
                    p1, p2 = elem.pontos
                    f.write(f"10\n{p1[0]:.2f}\n20\n{p1[1]:.2f}\n30\n0.0\n")
                    f.write(f"11\n{p2[0]:.2f}\n21\n{p2[1]:.2f}\n31\n0.0\n")

                elif elem.tipo == "CIRCLE":
                    handle = self._proximo_handle()
                    f.write(f"0\nCIRCLE\n5\n{handle}\n")
                    f.write(f"8\n{elem.grupo}\n62\n{elem.cor}\n")
                    f.write(f"10\n{elem.pontos[0][0]:.2f}\n20\n{elem.pontos[0][1]:.2f}\n30\n0.0\n")
                    f.write(f"40\n{elem.radius:.2f}\n")

                elif elem.tipo == "POLYLINE":
                    handle = self._proximo_handle()
                    f.write(f"0\nLWPOLYLINE\n5\n{handle}\n")
                    f.write(f"8\n{elem.grupo}\n62\n{elem.cor}\n")
                    f.write(f"90\n{len(elem.pontos)}\n")  # Número de vértices
                    for px_v, py_v in elem.pontos:
                        f.write(f"10\n{px_v:.2f}\n20\n{py_v:.2f}\n30\n0.0\n")

            # Adiciona label se houver
            if valv.label:
                handle = self._proximo_handle()
                f.write(f"0\nTEXT\n5\n{handle}\n")
                f.write("8\nValvulas\n")
                f.write(f"10\n{px:.2f}\n20\n{py + 15:.2f}\n30\n0.0\n")
                f.write(f"40\n{self.ALTURA_TEXTO_PADRAO:.2f}\n")
                f.write(f"1\n{valv.label}\n")
                f.write("50\n0.0\n7\nSTANDARD\n")

    def _escrever_suportes(self, f: TextIO) -> None:
        """Escreve os suportes estruturais."""
        for sup in self.sistema.suportes:
            px, py = sup.posicao.para_isometrico()

            # Símbolo simples: X para pé-de-amigo
            tamanho = 8.0
            handle = self._proximo_handle()
            f.write(f"0\nLINE\n5\n{handle}\n")
            f.write("8\nSuportes\n62\n3\n")  # Cor: verde
            f.write(f"10\n{px - tamanho:.2f}\n20\n{py - tamanho:.2f}\n30\n0.0\n")
            f.write(f"11\n{px + tamanho:.2f}\n21\n{py + tamanho:.2f}\n31\n0.0\n")

            handle = self._proximo_handle()
            f.write(f"0\nLINE\n5\n{handle}\n")
            f.write("8\nSuportes\n62\n3\n")
            f.write(f"10\n{px - tamanho:.2f}\n20\n{py + tamanho:.2f}\n30\n0.0\n")
            f.write(f"11\n{px + tamanho:.2f}\n21\n{py - tamanho:.2f}\n31\n0.0\n")

            # Label do suporte
            handle = self._proximo_handle()
            f.write(f"0\nTEXT\n5\n{handle}\n")
            f.write("8\nSuportes\n")
            f.write(f"10\n{px:.2f}\n20\n{py - 15:.2f}\n30\n0.0\n")
            f.write(f"40\n{self.ALTURA_TEXTO_PADRAO - 0.5:.2f}\n")
            f.write(f"1\n{sup.nome}\n")
            f.write("50\n0.0\n7\nSTANDARD\n")

    def _escrever_cotas(self, f: TextIO) -> None:
        """Escreve as cotas (dimensões)."""
        for cota in self.cotas:
            x1, y1, x2, y2 = cota.propriedades_cota_iso()

            # Linha de cota
            handle = self._proximo_handle()
            f.write(f"0\nLINE\n5\n{handle}\n")
            f.write("8\nCotas\n62\n2\n")  # Cor: azul
            f.write(f"10\n{x1:.2f}\n20\n{y1:.2f}\n30\n0.0\n")
            f.write(f"11\n{x2:.2f}\n21\n{y2:.2f}\n31\n0.0\n")
            f.write("39\n10\n")  # Espessura = 0.1 mm

            # Setas de cota
            angulo_linha = math.degrees(math.atan2(y2 - y1, x2 - x1))
            seta1 = EstilosCota.desenhar_seta((x1, y1), angulo_linha)
            seta2 = EstilosCota.desenhar_seta((x2, y2), angulo_linha + 180)

            for seta_pts in [seta1, seta2]:
                handle = self._proximo_handle()
                f.write(f"0\nLWPOLYLINE\n5\n{handle}\n")
                f.write("8\nCotas\n62\n2\n")
                f.write(f"90\n{len(seta_pts)}\n")
                for px_s, py_s in seta_pts:
                    f.write(f"10\n{px_s:.2f}\n20\n{py_s:.2f}\n30\n0.0\n")

            # Texto da cota
            txt_x, txt_y = cota.posicao_texto_cota()
            texto = cota.texto_dimensao()

            handle = self._proximo_handle()
            f.write(f"0\nTEXT\n5\n{handle}\n")
            f.write("8\nCotas\n62\n2\n")
            f.write(f"10\n{txt_x:.2f}\n20\n{txt_y:.2f}\n30\n0.0\n")
            f.write(f"40\n{cota.altura_texto:.2f}\n")
            f.write(f"1\n{texto}\n")
            f.write("50\n0.0\n7\nSTANDARD\n")

    def _escrever_bom_bloco(self, f: TextIO) -> None:
        """Escreve o BOM (lista de materiais) como bloco de texto no rodapé."""
        bom = self.sistema.gerar_bom()

        # Criar seção de texto para BOM (no rodapé do desenho)
        y_inicio = -500.0

        linhas_bom = ["LISTA DE MATERIAIS (BOM)", "=" * 40]

        linhas_bom.append("\nTUBOS:")
        for tubo in bom['tubos']:
            linhas_bom.append(
                f"  Ø {tubo['diametro_mm']:.0f}mm x {tubo['comprimento_total']:.2f}m "
                f"({tubo['quantidade']} un) — {tubo['material']}"
            )

        linhas_bom.append("\nVÁLVULAS:")
        for valv in bom['valvulas']:
            linhas_bom.append(
                f"  {valv['tipo'].upper()} Ø {valv['diametro_mm']:.0f}mm ({valv['quantidade']} un)"
            )

        linhas_bom.append("\nSUPORTES:")
        for sup in bom['suportes']:
            linhas_bom.append(
                f"  {sup['tipo'].upper()} ({sup['quantidade']} un)"
            )

        # Moldura do quadro BOM
        x0 = -1020.0
        y0 = y_inicio + 8.0
        largura = 860.0
        altura = (len(linhas_bom) + 1) * 12.0
        quadro = [
            (x0, y0),
            (x0 + largura, y0),
            (x0 + largura, y0 - altura),
            (x0, y0 - altura),
            (x0, y0),
        ]

        handle = self._proximo_handle()
        f.write(f"0\nLWPOLYLINE\n5\n{handle}\n")
        f.write("8\nBOM\n62\n7\n")
        f.write(f"90\n{len(quadro)}\n")
        for px_q, py_q in quadro:
            f.write(f"10\n{px_q:.2f}\n20\n{py_q:.2f}\n30\n0.0\n")

        # Escreve como várias linhas de texto
        for i, linha in enumerate(linhas_bom):
            handle = self._proximo_handle()
            f.write(f"0\nTEXT\n5\n{handle}\n")
            f.write("8\nBOM\n62\n7\n")
            f.write(f"10\n-1000.0\n20\n{y_inicio - i * 12:.1f}\n30\n0.0\n")
            f.write(f"40\n2.5\n")
            f.write(f"1\n{linha}\n")
            f.write("50\n0.0\n7\nSTANDARD\n")

    def gerar(self, caminho_saida: Path) -> Path:
        """Gera o arquivo DXF e retorna o caminho."""

        # Gera cotas auxiliares
        for tubo in self.sistema.tubos:
            self.cotas.append(GeradorCotas.cotacao_tubo_pp(f"Tubo-{tubo.nome}", tubo.P1, tubo.P2))
            self.cotas.append(GeradorCotas.cotacao_tubo_cc(f"Tubo-{tubo.nome}", tubo.P1, tubo.P2))

        # Abre arquivo para escrita
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)

        with open(caminho_saida, "w", encoding="utf-8") as f:
            # Seção HEADER
            self._escrever_header(f)

            # Seção TABLES
            self._escrever_tables(f)

            # Seção ENTITIES (o conteúdo principal)
            f.write("0\n")
            f.write("SECTION\n")
            f.write("2\n")
            f.write("ENTITIES\n")

            # Título do desenho
            handle = self._proximo_handle()
            f.write(f"0\nTEXT\n5\n{handle}\n")
            f.write("8\n0\n62\n1\n")
            f.write(f"10\n-1000.0\n20\n500.0\n30\n0.0\n")
            f.write(f"40\n5.0\n")
            f.write(f"1\n{self.titulo}\n")
            f.write("50\n0.0\n7\nSTANDARD\n")

            # Data e hora
            dt_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            handle = self._proximo_handle()
            f.write(f"0\nTEXT\n5\n{handle}\n")
            f.write("8\n0\n62\n7\n")
            f.write(f"10\n-1000.0\n20\n485.0\n30\n0.0\n")
            f.write(f"40\n2.0\n")
            f.write(f"1\nData: {dt_str}\n")
            f.write("50\n0.0\n7\nSTANDARD\n")

            # Conteúdo
            self._escrever_tubos(f)
            self._escrever_valvulas(f)
            self._escrever_suportes(f)
            self._escrever_cotas(f)
            self._escrever_bom_bloco(f)

            f.write("0\n")
            f.write("ENDSEC\n")

            # Fim do arquivo
            f.write("0\n")
            f.write("EOF\n")

        return caminho_saida


__all__ = [
    "GeradorDXF",
]
