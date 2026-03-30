"""
expansao_termica.py — Stress Check e Liras de Dilatação (REGAP/Petrobras)
=========================================================================
Implementa:
  1. Cálculo de expansão térmica de linhas de tubulação (ASME B31.3 / N-76)
  2. "Stress Check" simplificado — detecta se os esforços nos bocais são
     excessivos para a linha projetada como reta.
  3. Recomendação automática de Lira de Dilatação (Loop 'L' ou 'U') quando
     a linha é muito rígida.

Uso rápido:
    from engenharia_automacao.core.piping.expansao_termica import verificar_expansao

    resultado = verificar_expansao(
        comprimento_reto_m=30.0,
        diametro_mm=100.0,
        temperatura_operacao_c=250.0,
        temperatura_instalacao_c=20.0,
    )
    print(resultado.recomendacao)
    # → 'LIRA-U: instalar lira de expansão tipo U...'
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES FÍSICAS (ASME B31.3 / Petrobras)
# ─────────────────────────────────────────────────────────────────────────────

# Coeficiente de dilatação linear do aço carbono [mm/mm/°C]
# Referência: ASME B31.3 Appendix C / ASTM A106 Gr.B
ALFA_ACO_CARBONO: float = 12.0e-6  # mm/mm·°C   ≈ 12 µm/m·°C

# Módulo de elasticidade do aço carbono [MPa]
E_ACO_MPA: float = 200_000.0

# Tensão admissível de flexão (Petrobras / ASME B31.3 — 1/3 do fy)
# Para ASTM A106 Gr.B: Sy = 240 MPa → Sa = 80 MPa (simplificativo)
TENSAO_ADMISSIVEL_MPa: float = 80.0

# Força máxima admissível no bocal de bomba/vaso [N]
# (valor conservativo; projeto detalhado usa cargas permitidas do fabricante)
CARGA_BOCAL_MAXIMA_N: float = 500.0


class StatusStress(str, Enum):
    OK        = "OK — Linha flexível, sem necessidade de lira."
    ATENCAO   = "ATENÇÃO — Expansão moderada; adicionar guias ou pré-frio."
    CRITICO   = "CRÍTICO — Linha rígida; lira de dilatação obrigatória."


class TipoLira(str, Enum):
    NENHUMA = "Nenhuma"
    LIRA_L  = "Lira-L (expansão lateral em 'L' — desvia e absorve)"
    LIRA_U  = "Lira-U (loop em 'U' — absorção direta no trecho)"
    LIRA_Z  = "Lira-Z (compensador em 'Z' — para linhas em nível diferente)"


@dataclass
class ResultadoStressCheck:
    """Resultado do stress check simplificado de uma linha reta."""
    comprimento_m: float
    diametro_mm: float
    delta_t: float                     # variação de temperatura [°C]
    expansao_termica_mm: float         # dilatação linear total [mm]
    forca_bocal_estimada_N: float      # força axial estimada nos bocais [N]
    tensao_equivalente_MPa: float      # tensão de flexão equivalente [MPa]
    status: StatusStress
    tipo_lira_recomendada: TipoLira
    recomendacao: str                  # texto descritivo
    dimensoes_lira: dict               # braco_m e altura_m da lira sugerida


def verificar_expansao(
    comprimento_reto_m: float,
    diametro_mm: float,
    temperatura_operacao_c: float,
    temperatura_instalacao_c: float = 20.0,
    material: str = "ASTM A106 Gr.B",
) -> ResultadoStressCheck:
    """Verifica a expansão térmica de uma linha reta e recomenda lira se necessário.

    Parâmetros
    ----------
    comprimento_reto_m       : comprimento do trecho reto analisado [m]
    diametro_mm              : diâmetro nominal externo [mm]
    temperatura_operacao_c   : temperatura máxima de operação [°C]
    temperatura_instalacao_c : temperatura de instalação/montagem [°C]
    material                 : especificação do material (informativa)

    Retorna
    -------
    ResultadoStressCheck com status, força no bocal, tensão e recomendação.

    Método Simplificado
    -------------------
    1. ΔL = α × L × ΔT                     (expansão linear)
    2. F_bocal = E × A × (ΔL/L)            (força axial se linha travada)
       Para estimativa conservativa usa-se área da parede do tubo.
    3. σ_eq = M_flexão / W_resistente       (tensão de flexão se F gerar momento)
       Estimativa: M ≈ F × D/4 (momento de alavancagem no bocal).
    """
    if comprimento_reto_m <= 0:
        raise ValueError("comprimento_reto_m deve ser > 0.")

    delta_t = temperatura_operacao_c - temperatura_instalacao_c
    L_mm = comprimento_reto_m * 1000.0

    # 1. Expansão linear
    expansao_mm = ALFA_ACO_CARBONO * L_mm * delta_t

    # 2. Área da parede do tubo (estimativa SCH 40)
    _do_est = {25: 33.4, 50: 60.3, 80: 88.9, 100: 114.3,
               150: 168.3, 200: 219.1, 250: 273.1, 300: 323.9}
    _t_est  = {25: 3.38, 50: 3.91, 80: 5.49, 100: 6.02,
               150: 7.11, 200: 8.18, 250: 9.27, 300: 10.31}
    dn_keys = list(_do_est.keys())
    dn = min(dn_keys, key=lambda k: abs(k - diametro_mm))
    do = _do_est[dn]
    t  = _t_est[dn]
    di = do - 2.0 * t
    A_mm2 = math.pi / 4.0 * (do ** 2 - di ** 2)

    # Deformação axial se linha completamente engastada
    deformacao_axial = expansao_mm / L_mm
    forca_axial_N = E_ACO_MPA * A_mm2 * deformacao_axial  # em N (MPa × mm²)

    # 3. Tensão equivalente (momento estimado no bocal)
    # Momento = Força × D/4 (alavancagem mínima)
    W_resistente_mm3 = math.pi / 32.0 * (do ** 4 - di ** 4) / do  # modulo resistente
    M_bocal_Nmm = forca_axial_N * (do / 4.0)
    tensao_MPa = M_bocal_Nmm / max(W_resistente_mm3, 1.0)

    # 4. Classificação
    if forca_axial_N <= CARGA_BOCAL_MAXIMA_N and tensao_MPa <= TENSAO_ADMISSIVEL_MPa * 0.5:
        status = StatusStress.OK
        tipo_lira = TipoLira.NENHUMA
        recomendacao = (
            f"Linha OK. Expansão de {expansao_mm:.1f} mm não gera esforço "
            f"excessivo nos bocais (F_bocal={forca_axial_N:.0f} N < {CARGA_BOCAL_MAXIMA_N:.0f} N). "
            "Verificar suportes guia nas extremidades."
        )
        dimensoes_lira: dict = {}

    elif forca_axial_N <= CARGA_BOCAL_MAXIMA_N * 3.0 or tensao_MPa <= TENSAO_ADMISSIVEL_MPa:
        status = StatusStress.ATENCAO
        # Lira-L: mais simples e econômica para desvios curtos
        braco_l = _calcular_braco_lira_l(expansao_mm, diametro_mm)
        tipo_lira = TipoLira.LIRA_L
        recomendacao = (
            f"ATENÇÃO: Expansão {expansao_mm:.1f} mm — considere projetar a linha "
            f"com trecho em 'L' (desvio natural) de braço ≥ {braco_l:.2f} m. "
            f"F_bocal estimada = {forca_axial_N:.0f} N. "
            "Alternativamente, adicionar suportes-guia a cada 1,5 m nas extremidades."
        )
        dimensoes_lira = {
            "tipo": "L",
            "braco_disponivel_m": round(braco_l, 2),
            "nota": "Desvio ortogonal natural na planta ou elevação.",
        }

    else:
        status = StatusStress.CRITICO
        # Lira-U: absorção direta no trecho
        braco_u, altura_u = _calcular_lira_u(expansao_mm, diametro_mm)
        tipo_lira = TipoLira.LIRA_U
        recomendacao = (
            f"CRÍTICO: Instalar LIRA DE DILATAÇÃO tipo 'U' no trecho. "
            f"Parâmetros calculados: braço = {braco_u:.2f} m, altura = {altura_u:.2f} m. "
            f"F_bocal={forca_axial_N:.0f} N excede limite de {CARGA_BOCAL_MAXIMA_N:.0f} N. "
            f"Tensão equivalente = {tensao_MPa:.1f} MPa "
            f"(limite {TENSAO_ADMISSIVEL_MPa:.0f} MPa). "
            "Consultar Calculista de Flexibilidade (CAESAR II recomendado)."
        )
        dimensoes_lira = {
            "tipo": "U",
            "braco_m": round(braco_u, 2),
            "altura_m": round(altura_u, 2),
            "nota": (
                "Lira tipo U: dois cotovelos 90° + trecho reto vertical. "
                "Dimensionar por ASME B31.3 / N-143 com análise de flexibilidade completa."
            ),
        }

    return ResultadoStressCheck(
        comprimento_m=comprimento_reto_m,
        diametro_mm=diametro_mm,
        delta_t=delta_t,
        expansao_termica_mm=round(expansao_mm, 2),
        forca_bocal_estimada_N=round(forca_axial_N, 1),
        tensao_equivalente_MPa=round(tensao_MPa, 2),
        status=status,
        tipo_lira_recomendada=tipo_lira,
        recomendacao=recomendacao,
        dimensoes_lira=dimensoes_lira,
    )


# ─────────────────────────────────────────────────────────────────────────────
# CÁLCULO DAS DIMENSÕES DAS LIRAS
# ─────────────────────────────────────────────────────────────────────────────

def _calcular_braco_lira_l(expansao_mm: float, diametro_mm: float) -> float:
    """Calcula o comprimento mínimo do braço de uma lira 'L'.

    Fórmula Grinnell / Caesar II simplificada:
        L_braco = C × sqrt(Do × ΔL)
    onde C = 0.5 (coeficiente para aço carbono, SA_lim = 80 MPa).
    """
    C_flexao = 0.5  # coeficiente para ASTM A106 Gr.B
    braco_mm = C_flexao * math.sqrt(diametro_mm * expansao_mm)
    braco_m = braco_mm / 1000.0
    return max(braco_m, 0.5)  # mínimo prático de 0.5 m


def _calcular_lira_u(expansao_mm: float, diametro_mm: float) -> tuple[float, float]:
    """Calcula as dimensões de uma lira 'U' (loop de expansão).

    Retorna (braço_m, altura_m).

    Referência: ASME B31.3 Appendix D / prática Petrobras.
    Razão altura/braço ≈ 2:1 (loop clássico).
    """
    C_flexao = 0.7  # coeficiente mais conservativo para lira U
    braco_mm = C_flexao * math.sqrt(diametro_mm * expansao_mm)
    braco_m = max(braco_mm / 1000.0, 1.0)   # mínimo 1 m de braço
    altura_m = round(braco_m * 2.0, 2)       # altura = 2× braço
    return braco_m, altura_m
