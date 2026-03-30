"""
CLI de Teste — Calculista NBR 8800:2008
========================================
Interface para receber dados de carga/vão e gerar relatório técnico.
"""

from pathlib import Path
from engenharia_automacao.core.nbr8800 import Calculista, EntradaCalculo


def main() -> None:
    """Interface interativa para dimensionamento."""
    print("=" * 70)
    print("CALCULISTA ESTRUTURAL — NBR 8800:2008 (LRFD)")
    print("=" * 70)
    print()

    try:
        g = float(input("Carga Permanente (g) [kN/m]: ").strip() or "15.0")
        q = float(input("Sobrecarga Variável (q) [kN/m]: ").strip() or "10.0")
        L = float(input("Vão Livre (L) [m]: ").strip() or "8.0")

        entrada = EntradaCalculo(g=g, q=q, L=L)
        calc = Calculista()

        print("\n" + "=" * 70)
        print("EXECUTANDO DIMENSIONAMENTO...")
        print("=" * 70 + "\n")

        relatorio = calc.dimensionar(entrada)
        resultado = relatorio.perfil_selecionado

        # Resumo rápido
        print(f"✓ Perfil selecionado: {resultado.perfil.nome}")
        print(f"  - Carga de cálculo (ELU): {resultado.w_d:.2f} kN/m")
        print(f"  - Momento solicitante: {resultado.flexao.M_sd:.2f} kN·m")
        print(f"  - Momento resistente: {resultado.flexao.Mrd:.2f} kN·m")
        print(f"  - Taxa de utilização (flexão): {resultado.flexao.eta:.1%}")
        print(f"  - Flecha máxima: {resultado.flecha.delta_max:.2f} mm (limite: {resultado.flecha.delta_lim:.2f} mm)")
        print(f"\n  Status Final: {'🟢 APROVADO' if resultado.aprovado else '🔴 REPROVADO'}")

        # Gerar relatório Markdown
        from engenharia_automacao.core.nbr8800.relatorio import gerar_relatorio_markdown
        md = gerar_relatorio_markdown(relatorio)

        # Salvar em arquivo
        output_file = Path(__file__).parent.parent.parent / "data" / "output" / "relatorio_nbr8800.md"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(md, encoding="utf-8")
        print(f"\n✓ Relatório salvo em: {output_file}")

        # Listar perfis homologados
        print(f"\n✓ Perfis homologados: {len(relatorio.lista_homologados)}")
        for i, perf in enumerate(relatorio.lista_homologados[:5], 1):
            print(f"   {i}. {perf.nome} — Zx={perf.Zx:.0f}cm³, peso={perf.peso:.1f}kg/m")
        if len(relatorio.lista_homologados) > 5:
            print(f"   ... e mais {len(relatorio.lista_homologados) - 5}")

    except ValueError as e:
        print(f"\n✗ Erro de entrada: {e}")
    except Exception as e:
        print(f"\n✗ Erro irrecuperável: {e}")


if __name__ == "__main__":
    main()
