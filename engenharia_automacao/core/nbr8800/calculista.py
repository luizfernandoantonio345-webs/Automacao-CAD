"""
Calculista Estrutural — NBR 8800:2008 (LRFD)
============================================
Verificação analítica de perfis W em flexão simples (viga biapoiada,
carga distribuída uniforme) conforme os seguintes estados limites:

ELU — Estados Limites Últimos
  • EL-1 : Momento Fletor (Plastificação da Seção / FLT)
  • EL-2 : Cortante (verificação simplificada)

ELS — Estados Limites de Serviço
  • ES-1 : Flecha máxima ≤ L/250

Método: LRFD  →  φ_b = 0,90
Combinação de ações: Fd = γ_f · (g + q),  γ_f = 1,40

Referências normativas
----------------------
NBR 8800:2008  — Seção 5.4  (Resistência à Flexão de Vigas I)
NBR 6118:2014  — Seção 11.8 (Combinações de Ações)
AISC 360-16    — Capítulo F  (fórmulas de FLT equivalentes)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .profiles import PerfilW, PERFIS_CATALOGADOS

# ---------------------------------------------------------------------------
# Constantes de projeto
# ---------------------------------------------------------------------------
PHI_B: float = 0.90   # fator de resistência à flexão (LRFD, NBR 8800)
PHI_V: float = 1.00   # fator de resistência ao cortante (alma compacta)
GAMMA_F: float = 1.40  # coeficiente de ponderação das ações (PP + SC)
E_ACO: float = 200_000.0  # MPa
FY: float = 345.0         # MPa  (A572 Gr.50)
LIMITE_UTILIZACAO: float = 0.80  # taxa máxima antes do upsize automático


# ---------------------------------------------------------------------------
# Estruturas de entrada e resultado
# ---------------------------------------------------------------------------
@dataclass
class EntradaCalculo:
    """Parâmetros de entrada para o dimensionamento.

    Parâmetros
    ----------
    g   : kN/m — carga permanente (inclui PP estimado; iterativo se necessário)
    q   : kN/m — sobrecarga variável (utilização, vento, etc.)
    L   : m    — vão do elemento
    Lb  : m    — comprimento destravado lateralmente (padrão = L: sem travamento)
    Cb  : —    — fator de distribuição de momentos (1,0 = conservador; uniforme)
    """
    g: float           # kN/m — carga permanente característica
    q: float           # kN/m — sobrecarga variável característica
    L: float           # m    — vão
    Lb: Optional[float] = None   # m — comprimento destravado (None → = L)
    Cb: float = 1.0              # fator de momento uniforme equivalente


@dataclass
class VerificacaoSecao:
    """Resultado detalhado da verificação de seção compacta."""
    lambda_f: float
    lambda_pf: float
    lambda_rf: float
    lambda_w: float
    lambda_pw: float
    lambda_rw: float
    classe_mesa: str
    classe_alma: str
    is_compacta: bool


@dataclass
class VerificacaoFLT:
    """Resultado detalhado da verificação de Flambagem Lateral por Torção."""
    Lb: float          # m — comprimento destravado real
    Lp: float          # m — limite plástico
    Lr: float          # m — limite elástico
    regime: str        # "Sem FLT" | "FLT Inelástica" | "FLT Elástica"
    Cb: float
    Mp: float          # kN·m
    Mn: float          # kN·m — após FLT


@dataclass
class VerificacaoFlexao:
    """Resultado completo da verificação à flexão (ELU)."""
    M_sd: float        # kN·m — momento solicitante de cálculo
    Mrd: float         # kN·m — momento resistente de cálculo
    eta: float         # — taxa de utilização M_sd / Mrd
    aprovado: bool
    secao: VerificacaoSecao
    flt: VerificacaoFLT


@dataclass
class VerificacaoFlecha:
    """Resultado da verificação de flecha (ELS)."""
    delta_max: float   # mm — flecha máxima calculada
    delta_lim: float   # mm — flecha limite (L/250)
    relacao: float     # L / delta_max (quanto à margem)
    aprovado: bool


@dataclass
class VerificacaoCortante:
    """Resultado da verificação ao cortante (ELU)."""
    V_sd: float        # kN — cortante solicitante
    Vrd: float         # kN — cortante resistente
    eta: float
    aprovado: bool


@dataclass
class ResultadoVerificacao:
    """Resultado integral da verificação de um perfil sob as cargas fornecidas."""
    perfil: PerfilW
    entrada: EntradaCalculo
    # Combinação de ações
    w_d: float         # kN/m — carga de cálculo (ELU)
    w_ser: float       # kN/m — carga de serviço (ELS)
    # Sub-resultados
    flexao: VerificacaoFlexao
    flecha: VerificacaoFlecha
    cortante: VerificacaoCortante
    # Esbeltez L/r (eixo fraco, relativo ao vão)
    esbeltez_Lr: float
    # Índice geral
    aprovado: bool


@dataclass
class RelatorioCalculista:
    """Relatório final do dimensionamento, com perfil selecionado e histórico."""
    entrada: EntradaCalculo
    perfil_selecionado: ResultadoVerificacao
    historico_upsize: list[ResultadoVerificacao]
    lista_homologados: list[PerfilW]


# ---------------------------------------------------------------------------
# Funções auxiliares de cálculo
# ---------------------------------------------------------------------------
def _Mp_kNm(perfil: PerfilW) -> float:
    """Momento plástico Mp = fy · Zx  [kN·m].

    Unidades: fy [MPa = N/mm²],  Zx [cm³]
      Mp [N·mm] = fy [N/mm²] · Zx [cm³ = 1000 mm³]
      Mp [kN·m] = Mp [N·mm] / 1 000 000
    """
    return perfil.fy * perfil.Zx * 1_000.0 / 1_000_000.0


def _Mser_kNm(fy_MPa: float, Sx_cm3: float) -> float:
    """Momento de escoamento elástico: M_ser = fy · Sx  [kN·m]."""
    return fy_MPa * Sx_cm3 * 1_000.0 / 1_000_000.0


def _Lp_m(perfil: PerfilW) -> float:
    """Comprimento limite para plastificação total [m].

    NBR 8800:2008 / AISC 360-16 eq. F2-5:
      Lp = 1,76 · ry · √(E / fy)
    onde ry [cm], E [MPa], fy [MPa].
    Resultado em cm → converte para m.
    """
    return 1.76 * perfil.ry * math.sqrt(perfil.E / perfil.fy) / 100.0


def _Lr_m(perfil: PerfilW) -> float:
    """Comprimento limite para FLT elástica [m].

    NBR 8800:2008 / AISC 360-16 eq. F2-6:
      Lr = 1,95 · rts · (E / (0,7·fy)) ·
           √( J·c/(Sx·ho) + √((J·c/(Sx·ho))² + 6,76·(0,7·fy/E)²) )

    c = 1,0 para I duplo simétrico.
    Todas as propriedades em cm.
    """
    rts = perfil.rts          # cm
    J   = perfil.J            # cm⁴
    Sx  = perfil.Sx           # cm³
    ho  = perfil.ho           # cm
    E   = perfil.E            # MPa
    fy  = perfil.fy           # MPa
    c   = 1.0

    JcSxho = J * c / (Sx * ho)
    inner  = JcSxho**2 + 6.76 * (0.7 * fy / E)**2
    Lr_cm  = 1.95 * rts * (E / (0.7 * fy)) * math.sqrt(JcSxho + math.sqrt(inner))
    return Lr_cm / 100.0


def _Mn_kNm(perfil: PerfilW, Lb: float, Cb: float) -> tuple[float, str]:
    """Momento nominal Mn [kN·m] com classificação do regime de FLT.

    Parâmetros
    ----------
    Lb : comprimento destravado [m]
    Cb : fator de gradiente de momento (≥ 1,0)

    Retorna
    -------
    (Mn [kN·m], regime)
    """
    Mp  = _Mp_kNm(perfil)
    Lp  = _Lp_m(perfil)
    Lr  = _Lr_m(perfil)
    Sx  = perfil.Sx    # cm³
    fy  = perfil.fy    # MPa
    E   = perfil.E     # MPa

    # Convenção: Lb em metros, rts em cm → converter Lb para cm para Fcr
    Lb_cm  = Lb * 100.0
    rts_cm = perfil.rts

    if Lb <= Lp:
        return Mp, "Sem FLT"

    if Lb <= Lr:
        # FLT Inelástica — eq. F2-2
        M07fySx = 0.7 * fy * Sx * 1_000.0 / 1_000_000.0   # kN·m
        Mn = Cb * (Mp - (Mp - M07fySx) * (Lb - Lp) / (Lr - Lp))
        Mn = min(Mn, Mp)
        return Mn, "FLT Inelástica"

    # FLT Elástica — eq. F2-3 / F2-4
    J   = perfil.J    # cm⁴
    Sx  = perfil.Sx   # cm³
    ho  = perfil.ho   # cm
    c   = 1.0

    JcSxho = J * c / (Sx * ho)
    Fcr = (Cb * math.pi**2 * E / (Lb_cm / rts_cm)**2 *
           math.sqrt(1.0 + 0.078 * JcSxho * (Lb_cm / rts_cm)**2))  # MPa
    Mn  = Fcr * Sx * 1_000.0 / 1_000_000.0   # kN·m
    Mn  = min(Mn, Mp)
    return Mn, "FLT Elástica"


def _delta_mm(w_kNm: float, L_m: float, E_MPa: float, Ix_cm4: float) -> float:
    """Flecha máxima de viga biapoiada com carga distribuída uniforme [mm].

    δ_max = 5·w·L⁴ / (384·E·Ix)

    Unidades consistentes:
      w  [N/mm]  = w_kNm  (1 kN/m = 1 N/mm)
      L  [mm]    = L_m × 1000
      E  [N/mm²] = E_MPa
      Ix [mm⁴]   = Ix_cm4 × 10⁴
    """
    w_Nmm  = w_kNm                      # N/mm
    L_mm   = L_m * 1_000.0              # mm
    Ix_mm4 = Ix_cm4 * 10_000.0          # mm⁴
    return 5.0 * w_Nmm * L_mm**4 / (384.0 * E_MPa * Ix_mm4)


def _Vrd_kN(perfil: PerfilW) -> float:
    """Resistência nominal ao cortante [kN] (alma compacta, φ_v = 1,0).

    NBR 8800:2008 (eq. 5.10 simplificada):
      Vrd = φ_v · 0,6 · fy · Aw
    onde Aw = d · tw  (área bruta da alma) [mm²].
    """
    phi_v = 1.0
    Aw_mm2 = perfil.d * perfil.tw   # mm²
    Aw_cm2 = Aw_mm2 / 100.0
    fy_kN_cm2 = perfil.fy / 100.0   # kN/cm²
    return phi_v * 0.6 * fy_kN_cm2 * Aw_cm2   # kN


# ---------------------------------------------------------------------------
# Motor principal de verificação
# ---------------------------------------------------------------------------
class Calculista:
    """Calculista estrutural — NBR 8800:2008, perfis W em flexão simples.

    Uso rápido
    ----------
    >>> from engenharia_automacao.core.nbr8800 import Calculista, EntradaCalculo
    >>> calc = Calculista()
    >>> entrada = EntradaCalculo(g=15.0, q=10.0, L=8.0)
    >>> relatorio = calc.dimensionar(entrada)
    """

    def verificar_perfil(
        self,
        perfil: PerfilW,
        entrada: EntradaCalculo,
    ) -> ResultadoVerificacao:
        """Executa a verificação completa de um perfil para a entrada fornecida.

        Viga simplesmente apoiada, carga distribuída uniforme, LRFD.

        Combinação de ações (NBR 6118 / NBR 8800):
          w_d   = γ_f · (g + q)   [ELU — Estados Limites Últimos]
          w_ser = g + q            [ELS — Estados Limites de Serviço]
        """

        Lb = entrada.Lb if entrada.Lb is not None else entrada.L
        Cb = entrada.Cb
        L  = entrada.L

        # ── 1. Combinação de ações ──────────────────────────────────────────
        w_d   = GAMMA_F * (entrada.g + entrada.q)   # kN/m — ELU
        w_ser = entrada.g + entrada.q               # kN/m — ELS

        # ── 2. Esforços solicitantes ────────────────────────────────────────
        M_sd = w_d * L**2 / 8.0   # kN·m
        V_sd = w_d * L / 2.0      # kN

        # ── 3. Classificação da seção transversal ───────────────────────────
        sec = VerificacaoSecao(
            lambda_f   = perfil.lambda_f,
            lambda_pf  = perfil.lambda_pf,
            lambda_rf  = perfil.lambda_rf,
            lambda_w   = perfil.lambda_w,
            lambda_pw  = perfil.lambda_pw,
            lambda_rw  = perfil.lambda_rw,
            classe_mesa = perfil.classe_mesa,
            classe_alma = perfil.classe_alma,
            is_compacta = perfil.is_compacta,
        )

        # ── 4. FLT — Flambagem Lateral por Torção ──────────────────────────
        Mp               = _Mp_kNm(perfil)
        Mn, regime_flt   = _Mn_kNm(perfil, Lb, Cb)
        Lp               = _Lp_m(perfil)
        Lr               = _Lr_m(perfil)

        flt = VerificacaoFLT(
            Lb=Lb, Lp=Lp, Lr=Lr,
            regime=regime_flt,
            Cb=Cb,
            Mp=Mp,
            Mn=Mn,
        )

        # ── 5. Resistência à flexão de cálculo ─────────────────────────────
        Mrd = PHI_B * Mn       # kN·m
        eta = M_sd / Mrd
        flexao = VerificacaoFlexao(
            M_sd=M_sd, Mrd=Mrd, eta=eta,
            aprovado=(eta <= LIMITE_UTILIZACAO),
            secao=sec, flt=flt,
        )

        # ── 6. Flecha (ELS) ─────────────────────────────────────────────────
        delta_max = _delta_mm(w_ser, L, E_ACO, perfil.Ix)
        delta_lim = L * 1_000.0 / 250.0   # mm
        flecha = VerificacaoFlecha(
            delta_max=delta_max,
            delta_lim=delta_lim,
            relacao=(L * 1_000.0 / delta_max) if delta_max > 0 else float("inf"),
            aprovado=(delta_max <= delta_lim),
        )

        # ── 7. Cortante (ELU) ───────────────────────────────────────────────
        Vrd = _Vrd_kN(perfil)
        cortante = VerificacaoCortante(
            V_sd=V_sd, Vrd=Vrd,
            eta=(V_sd / Vrd),
            aprovado=(V_sd <= Vrd),
        )

        # ── 8. Esbeltez global L/r ──────────────────────────────────────────
        esbeltez_Lr = (L * 100.0) / perfil.ry   # L em cm, ry em cm

        aprovado = (
            flexao.aprovado and
            flecha.aprovado and
            cortante.aprovado
        )

        return ResultadoVerificacao(
            perfil=perfil,
            entrada=entrada,
            w_d=w_d,
            w_ser=w_ser,
            flexao=flexao,
            flecha=flecha,
            cortante=cortante,
            esbeltez_Lr=esbeltez_Lr,
            aprovado=aprovado,
        )

    def dimensionar(
        self,
        entrada: EntradaCalculo,
        catalogo: tuple[PerfilW, ...] = PERFIS_CATALOGADOS,
    ) -> RelatorioCalculista:
        """Seleciona o perfil mais econômico e gera o relatório de cálculo.

        Algoritmo de upsize automático
        --------------------------------
        1. Itera sobre o catálogo ordenado por Zx crescente.
        2. Verifica cada perfil.
        3. O primeiro perfil que passe **todos** os critérios AND cuja taxa de
           utilização à flexão seja ≤ 0,80 é selecionado.
        4. Perfis reprovados são registrados no histórico de upsize.

        A lista de perfis homologados inclui todos os perfis do catálogo que,
        para as mesmas ações, tenham eta ≤ 1,0 (verificação normativa mínima).
        """
        historico: list[ResultadoVerificacao] = []
        selecionado: Optional[ResultadoVerificacao] = None

        for perfil in catalogo:
            resultado = self.verificar_perfil(perfil, entrada)
            if selecionado is None:
                if resultado.aprovado:
                    selecionado = resultado
                else:
                    historico.append(resultado)

        if selecionado is None:
            # Nenhum perfil do catálogo atende — retorna o maior disponível
            # para que o relatório exponha as taxas (situação crítica)
            selecionado = self.verificar_perfil(catalogo[-1], entrada)

        # Lista homologada: todos os perfis com taxa flexão ≤ 1,0
        homologados: list[PerfilW] = []
        for perfil in catalogo:
            r = self.verificar_perfil(perfil, entrada)
            if r.flexao.eta <= 1.0 and r.flecha.aprovado and r.cortante.aprovado:
                homologados.append(perfil)

        return RelatorioCalculista(
            entrada=entrada,
            perfil_selecionado=selecionado,
            historico_upsize=historico,
            lista_homologados=homologados,
        )
