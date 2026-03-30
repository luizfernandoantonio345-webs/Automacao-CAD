"""
Exemplo de Uso — CHAT 2: O Mestre de Isométricos
================================================
Demonstra o fluxo completo:
  1. Criação de sistema de tubulação 3D
  2. Adição de válvulas e componentes
  3. Detecção automática de vãos e inserção de suportes
  4. Geração de BOM
  5. Exportação para DXF com cotação e simbologia
"""

from pathlib import Path
from engenharia_automacao.core.isometrica import (
    SistemaIsometrico,
    Ponto3D,
    Tubo,
    Valvula,
    TipoValvula,
    GeradorDXF,
)


def exemplo_isometrico_simples():
    """Exemplo 1: Tubulação simples com válvulas."""
    print("\n" + "=" * 70)
    print("CHAT 2: O MESTRE DE ISOMÉTRICOS")
    print("=" * 70)

    # Criar sistema
    sistema = SistemaIsometrico()

    # Definir arquitetura da tubulação
    # Linha horizontal principal: 3m de tubo Ø 50mm
    P1 = Ponto3D(x=0.0, y=0.0, z=0.0)
    P2 = Ponto3D(x=3.0, y=0.0, z=0.0)
    tubo1 = Tubo("T1", P1, P2, diametro=0.050, label="T1 (3m x Ø50)")
    sistema.adicionar_tubo(tubo1)

    # Válvula de gaveta na entrada
    valv_entrada = Valvula("V1", TipoValvula.GAVETA, P1, diametro=0.050, direcao=None, label="Válvula de Gaveta")
    sistema.adicionar_valvula(valv_entrada)

    # Cotovelo 90° a 2m
    P3 = Ponto3D(x=2.0, y=0.0, z=0.0)
    P4 = Ponto3D(x=2.0, y=0.0, z=-1.5)
    tubo2 = Tubo("T2", P3, P4, diametro=0.050, label="T2 (1.5m x Ø50)")
    sistema.adicionar_tubo(tubo2)

    # Válvula de globo na descida
    valv_desc = Valvula("V2", TipoValvula.GLOBO, P4, diametro=0.050, direcao=None, label="Válvula de Globo")
    sistema.adicionar_valvula(valv_desc)

    # Linha de descarga
    P5 = Ponto3D(x=2.0, y=-1.0, z=-1.5)
    tubo3 = Tubo("T3", P4, P5, diametro=0.040, label="T3 (1m x Ø40)")
    sistema.adicionar_tubo(tubo3)

    # Tee para purgador
    P6 = Ponto3D(x=1.0, y=0.0, z=0.0)
    tee = Valvula("V3", TipoValvula.TEE, P6, diametro=0.050, direcao=None, label="Tee")
    sistema.adicionar_valvula(tee)

    # Purgador
    P7 = Ponto3D(x=1.0, y=-0.5, z=0.0)
    purgador = Valvula("V4", TipoValvula.PURGADOR, P7, diametro=0.020, direcao=None, label="Purgador")
    sistema.adicionar_valvula(purgador)

    print("\n✓ Sistema 3D criado:")
    print(f"  - {len(sistema.tubos)} segmentos de tubo")
    print(f"  - {len(sistema.valvulas)} válvulas/componentes")

    # Detectar vãos livres e inserir suportes automaticamente
    print("\n✓ Analisando vãos livres...")
    recomendacoes = sistema.calcular_vaos_livres(vao_maximo=2.0)
    print(f"  - {len(recomendacoes)} suporte(s) inserido(s)")
    for rec in recomendacoes:
        print(f"    • {rec['tubo']}: {rec['motivo']} (vão = {rec['vao_livre']:.2f}m)")

    print(f"  - Total de suportes: {len(sistema.suportes)}")

    # Gerar BOM
    print("\n✓ Gerando Lista de Materiais (BOM)...")
    bom = sistema.gerar_bom()

    print("\n  TUBOS:")
    for tubo in bom['tubos']:
        print(f"    • Ø {tubo['diametro_mm']:.0f}mm: {tubo['quantidade']} un × {tubo['comprimento_unitario_medio']:.2f}m = {tubo['comprimento_total']:.2f}m")

    print("\n  VÁLVULAS:")
    for valv in bom['valvulas']:
        print(f"    • {valv['tipo'].upper()} Ø {valv['diametro_mm']:.0f}mm: {valv['quantidade']} un")

    print("\n  SUPORTES:")
    for sup in bom['suportes']:
        print(f"    • {sup['tipo'].upper()}: {sup['quantidade']} un")

    # Gerar desenho DXF
    print("\n✓ Gerando desenho isométrico em DXF...")
    gerador = GeradorDXF(sistema, titulo="Isométrico de Tubulação — Exemplo Industrial")
    caminho_dxf = Path(__file__).parent.parent.parent / "data" / "output" / "isometrico_exemplo.dxf"
    resultado_dxf = gerador.gerar(caminho_dxf)

    print(f"\n✓ Arquivo DXF gerado com sucesso!")
    print(f"  Caminho: {resultado_dxf}")
    print(f"  Contém: {len(sistema.tubos)} tubos, {len(sistema.valvulas)} válvulas, {len(sistema.suportes)} suportes")
    print(f"  Cotas automáticas: {len(gerador.cotas)}")

    print("\n" + "=" * 70)


def exemplo_isometrico_complexo():
    """Exemplo 2: Sistema mais complexo com múltiplas linhas."""
    print("\n" + "=" * 70)
    print("EXEMPLO 2: Sistema de Vapor e Retorno (Mais Complexo)")
    print("=" * 70)

    sistema = SistemaIsometrico()

    # Linha de alimentação (3m)
    P0 = Ponto3D(x=0.0, y=0.0, z=2.0)
    P1 = Ponto3D(x=3.0, y=0.0, z=2.0)
    tubo_alim = Tubo("T-Alim", P0, P1, diametro=0.075, label="Alimentação (3m x Ø75)")
    sistema.adicionar_tubo(tubo_alim)

    # Válvula de gaveta na entrada
    valv_entrada = Valvula("V-Entrada", TipoValvula.GAVETA, P0, 0.075, None, "V. de Gaveta (Entrada)")
    sistema.adicionar_valvula(valv_entrada)

    # Ramal 1: Para consumidor
    P2 = Ponto3D(x=1.5, y=0.0, z=2.0)
    P3 = Ponto3D(x=1.5, y=0.0, z=0.5)
    P4 = Ponto3D(x=1.5, y=2.0, z=0.5)

    tee1 = Valvula("V-Tee1", TipoValvula.TEE, P2, 0.075, None, "Tee #1")
    sistema.adicionar_valvula(tee1)

    tubo_desc1 = Tubo("T-Desc1", P2, P3, diametro=0.050, label="Descida (1.5m x Ø50)")
    sistema.adicionar_tubo(tubo_desc1)

    tubo_lateral1 = Tubo("T-Lateral1", P3, P4, diametro=0.050, label="Lateral (2m x Ø50)")
    sistema.adicionar_tubo(tubo_lateral1)

    # Ramal 2: Para outro consumidor
    P5 = Ponto3D(x=2.5, y=0.0, z=2.0)
    P6 = Ponto3D(x=2.5, y=-1.5, z=0.0)

    tee2 = Valvula("V-Tee2", TipoValvula.TEE, P5, 0.075, None, "Tee #2")
    sistema.adicionar_valvula(tee2)

    tubo_lateral2 = Tubo("T-Lateral2", P5, P6, diametro=0.050, label="Descida (2m x Ø50)")
    sistema.adicionar_tubo(tubo_lateral2)

    # Linha de retorno
    P7 = Ponto3D(x=0.0, y=0.0, z=0.0)
    P8 = Ponto3D(x=3.0, y=0.0, z=0.0)
    tubo_retorno = Tubo("T-Retorno", P7, P8, diametro=0.100, label="Retorno (3m x Ø100)")
    sistema.adicionar_tubo(tubo_retorno)

    # Válvula de retenção
    P9 = Ponto3D(x=1.5, y=0.0, z=0.0)
    valv_retencao = Valvula("V-Ret", TipoValvula.RETENCAO, P9, 0.100, None, "V. de Retenção")
    sistema.adicionar_valvula(valv_retencao)

    print(f"✓ Sistema criado: {len(sistema.tubos)} tubos, {len(sistema.valvulas)} componentes")

    # Vãos e suportes
    recomendacoes = sistema.calcular_vaos_livres(vao_maximo=2.5)
    print(f"✓ Suportes identificados: {len(recomendacoes)}")

    # BOM
    bom = sistema.gerar_bom()
    print(f"✓ BOM gerado:\n")
    comprimento_total = sum(t['comprimento_total'] for t in bom['tubos'])
    print(f"   Comprimento total de tubo: {comprimento_total:.2f}m")
    print(f"   Total de válvulas: {sum(v['quantidade'] for v in bom['valvulas'])}")

    # DXF
    gerador = GeradorDXF(sistema, titulo="Sistema Vapor/Retorno — Isométrico Completo")
    caminho_dxf = Path(__file__).parent.parent.parent / "data" / "output" / "isometrico_vapor_retorno.dxf"
    resultado = gerador.gerar(caminho_dxf)
    print(f"\n✓ DXF salvo em: {resultado}")


if __name__ == "__main__":
    exemplo_isometrico_simples()
    exemplo_isometrico_complexo()

    print("\n✓ TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO!")
    print("  Verifique os arquivos DXF em: engenharia_automacao/data/output/")
