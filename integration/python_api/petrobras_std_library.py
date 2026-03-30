"""petrobras_std_library.py
==========================

Biblioteca de Componentes Padrão Petrobras
Peças pré-carregadas em memória com pesos e dimensões oficiais.

Categorias:
  • Flanges   — ASME B16.5 / Petrobras N-1882
  • Parafusos — ASTM A193-B7 (stud bolts) / A307 Gr.B (chumbadores)
  • Perfis W  — NBR 5884 / equivalente AISC

Uso rápido:
    from petrobras_std_library import PetrobrasStdLib

    lib = PetrobrasStdLib()
    flange  = lib.get_flange('4"', 'Class 300')
    perfil  = lib.get_perfil_w('W200x46')
    bolt    = lib.get_parafuso('M20', 'A193-B7')
    print(lib.summary())
"""
from __future__ import annotations

from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# FLANGES — ASME B16.5 / Petrobras N-1882
# Chave: "<DN_pol>_<Classe>"  (espaço removido da classe)
# OD: diâmetro externo do flange (mm) | E: espessura face (mm)
# L: comprimento face-a-face solda (mm) | massa_kg: por unidade
# ──────────────────────────────────────────────────────────────────────────────
_FLANGES: dict[str, dict[str, Any]] = {
    # ── Class 150 ─────────────────────────────────────────────────────────────
    '1"_Class150':    {"DN_pol": '1"',   "classe": "Class 150", "DN_mm":  25, "OD_mm": 124, "E_mm": 16, "L_mm": 108, "massa_kg":  1.8, "norma": "ASME B16.5"},
    '1.5"_Class150':  {"DN_pol": '1.5"', "classe": "Class 150", "DN_mm":  38, "OD_mm": 156, "E_mm": 17, "L_mm": 114, "massa_kg":  2.7, "norma": "ASME B16.5"},
    '2"_Class150':    {"DN_pol": '2"',   "classe": "Class 150", "DN_mm":  51, "OD_mm": 165, "E_mm": 19, "L_mm": 152, "massa_kg":  3.6, "norma": "ASME B16.5"},
    '3"_Class150':    {"DN_pol": '3"',   "classe": "Class 150", "DN_mm":  76, "OD_mm": 210, "E_mm": 24, "L_mm": 190, "massa_kg":  7.2, "norma": "ASME B16.5"},
    '4"_Class150':    {"DN_pol": '4"',   "classe": "Class 150", "DN_mm": 102, "OD_mm": 254, "E_mm": 24, "L_mm": 229, "massa_kg": 10.9, "norma": "ASME B16.5"},
    '6"_Class150':    {"DN_pol": '6"',   "classe": "Class 150", "DN_mm": 152, "OD_mm": 318, "E_mm": 25, "L_mm": 279, "massa_kg": 19.1, "norma": "ASME B16.5"},
    '8"_Class150':    {"DN_pol": '8"',   "classe": "Class 150", "DN_mm": 203, "OD_mm": 381, "E_mm": 29, "L_mm": 343, "massa_kg": 30.8, "norma": "ASME B16.5"},
    '10"_Class150':   {"DN_pol": '10"',  "classe": "Class 150", "DN_mm": 254, "OD_mm": 444, "E_mm": 30, "L_mm": 406, "massa_kg": 47.2, "norma": "ASME B16.5"},
    '12"_Class150':   {"DN_pol": '12"',  "classe": "Class 150", "DN_mm": 305, "OD_mm": 521, "E_mm": 32, "L_mm": 457, "massa_kg": 67.1, "norma": "ASME B16.5"},
    # ── Class 300 ─────────────────────────────────────────────────────────────
    '1"_Class300':    {"DN_pol": '1"',   "classe": "Class 300", "DN_mm":  25, "OD_mm": 124, "E_mm": 22, "L_mm": 117, "massa_kg":  2.5, "norma": "ASME B16.5"},
    '2"_Class300':    {"DN_pol": '2"',   "classe": "Class 300", "DN_mm":  51, "OD_mm": 165, "E_mm": 25, "L_mm": 159, "massa_kg":  5.4, "norma": "ASME B16.5"},
    '3"_Class300':    {"DN_pol": '3"',   "classe": "Class 300", "DN_mm":  76, "OD_mm": 210, "E_mm": 32, "L_mm": 210, "massa_kg": 10.4, "norma": "ASME B16.5"},
    '4"_Class300':    {"DN_pol": '4"',   "classe": "Class 300", "DN_mm": 102, "OD_mm": 254, "E_mm": 35, "L_mm": 248, "massa_kg": 16.8, "norma": "ASME B16.5"},
    '6"_Class300':    {"DN_pol": '6"',   "classe": "Class 300", "DN_mm": 152, "OD_mm": 318, "E_mm": 44, "L_mm": 318, "massa_kg": 34.5, "norma": "ASME B16.5"},
    '8"_Class300':    {"DN_pol": '8"',   "classe": "Class 300", "DN_mm": 203, "OD_mm": 406, "E_mm": 48, "L_mm": 381, "massa_kg": 59.4, "norma": "ASME B16.5"},
    '10"_Class300':   {"DN_pol": '10"',  "classe": "Class 300", "DN_mm": 254, "OD_mm": 483, "E_mm": 52, "L_mm": 419, "massa_kg": 89.0, "norma": "ASME B16.5"},
    '12"_Class300':   {"DN_pol": '12"',  "classe": "Class 300", "DN_mm": 305, "OD_mm": 559, "E_mm": 57, "L_mm": 470, "massa_kg":128.0, "norma": "ASME B16.5"},
    # ── Class 600 ─────────────────────────────────────────────────────────────
    '2"_Class600':    {"DN_pol": '2"',   "classe": "Class 600", "DN_mm":  51, "OD_mm": 165, "E_mm": 33, "L_mm": 165, "massa_kg":  7.2, "norma": "ASME B16.5"},
    '4"_Class600':    {"DN_pol": '4"',   "classe": "Class 600", "DN_mm": 102, "OD_mm": 273, "E_mm": 48, "L_mm": 267, "massa_kg": 22.7, "norma": "ASME B16.5"},
    '6"_Class600':    {"DN_pol": '6"',   "classe": "Class 600", "DN_mm": 152, "OD_mm": 365, "E_mm": 57, "L_mm": 343, "massa_kg": 52.6, "norma": "ASME B16.5"},
    '8"_Class600':    {"DN_pol": '8"',   "classe": "Class 600", "DN_mm": 203, "OD_mm": 445, "E_mm": 67, "L_mm": 419, "massa_kg": 98.2, "norma": "ASME B16.5"},
    # ── Class 900 ─────────────────────────────────────────────────────────────
    '4"_Class900':    {"DN_pol": '4"',   "classe": "Class 900", "DN_mm": 102, "OD_mm": 273, "E_mm": 57, "L_mm": 279, "massa_kg": 27.2, "norma": "ASME B16.5"},
    '6"_Class900':    {"DN_pol": '6"',   "classe": "Class 900", "DN_mm": 152, "OD_mm": 394, "E_mm": 67, "L_mm": 368, "massa_kg": 70.3, "norma": "ASME B16.5"},
    '8"_Class900':    {"DN_pol": '8"',   "classe": "Class 900", "DN_mm": 203, "OD_mm": 483, "E_mm": 83, "L_mm": 444, "massa_kg":127.0, "norma": "ASME B16.5"},
    # ── Class 1500 ────────────────────────────────────────────────────────────
    '4"_Class1500':   {"DN_pol": '4"',   "classe": "Class 1500","DN_mm": 102, "OD_mm": 311, "E_mm": 73, "L_mm": 330, "massa_kg": 44.5, "norma": "ASME B16.5"},
    '6"_Class1500':   {"DN_pol": '6"',   "classe": "Class 1500","DN_mm": 152, "OD_mm": 394, "E_mm": 95, "L_mm": 400, "massa_kg": 97.5, "norma": "ASME B16.5"},
    '8"_Class1500':   {"DN_pol": '8"',   "classe": "Class 1500","DN_mm": 203, "OD_mm": 483, "E_mm":111, "L_mm": 470, "massa_kg":162.0, "norma": "ASME B16.5"},
    # ── Class 2500 ────────────────────────────────────────────────────────────
    '4"_Class2500':   {"DN_pol": '4"',   "classe": "Class 2500","DN_mm": 102, "OD_mm": 368, "E_mm":102, "L_mm": 368, "massa_kg": 72.4, "norma": "ASME B16.5"},
    '6"_Class2500':   {"DN_pol": '6"',   "classe": "Class 2500","DN_mm": 152, "OD_mm": 495, "E_mm":130, "L_mm": 457, "massa_kg":161.0, "norma": "ASME B16.5"},
}

# ──────────────────────────────────────────────────────────────────────────────
# PARAFUSOS — ASTM A193-B7 (stud bolts flanges) / A307 Gr.B (chumbadores)
# Chave: "<Diâmetro_métrico>_<Especificação_sem_espaço>"
# massa_kg_m: massa linear por metro de comprimento útil
# ──────────────────────────────────────────────────────────────────────────────
_PARAFUSOS: dict[str, dict[str, Any]] = {
    # ── ASTM A193-B7 (stud bolts para flanges) ───────────────────────────────
    "M12_A193-B7":  {"diametro_mm": 12, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.089, "passo_mm": 1.75, "uso_tipico": "Flanges Class 150 (DN ≤ 1\")"},
    "M16_A193-B7":  {"diametro_mm": 16, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.158, "passo_mm": 2.00, "uso_tipico": "Flanges Class 150/300 (DN ≤ 3\")"},
    "M20_A193-B7":  {"diametro_mm": 20, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.247, "passo_mm": 2.50, "uso_tipico": "Flanges Class 150/300/600"},
    "M24_A193-B7":  {"diametro_mm": 24, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.355, "passo_mm": 3.00, "uso_tipico": "Flanges Class 600/900"},
    "M30_A193-B7":  {"diametro_mm": 30, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.555, "passo_mm": 3.50, "uso_tipico": "Flanges Class 900/1500"},
    "M36_A193-B7":  {"diametro_mm": 36, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 0.800, "passo_mm": 4.00, "uso_tipico": "Flanges Class 1500/2500"},
    "M42_A193-B7":  {"diametro_mm": 42, "especificacao": "ASTM A193-B7", "f_y_MPa": 724, "f_u_MPa": 862, "massa_kg_m": 1.090, "passo_mm": 4.50, "uso_tipico": "Flanges Class 2500 (DN ≥ 8\")"},
    # ── ASTM A307 Gr.B (chumbadores estruturais) ─────────────────────────────
    "M16_A307":     {"diametro_mm": 16, "especificacao": "ASTM A307 Gr.B", "f_y_MPa": 250, "f_u_MPa": 414, "massa_kg_m": 0.158, "passo_mm": 2.00, "uso_tipico": "Chumbador estrutural leve"},
    "M20_A307":     {"diametro_mm": 20, "especificacao": "ASTM A307 Gr.B", "f_y_MPa": 250, "f_u_MPa": 414, "massa_kg_m": 0.247, "passo_mm": 2.50, "uso_tipico": "Chumbador estrutural P ≤ 150 kN"},
    "M25_A307":     {"diametro_mm": 25, "especificacao": "ASTM A307 Gr.B", "f_y_MPa": 250, "f_u_MPa": 414, "massa_kg_m": 0.385, "passo_mm": 3.00, "uso_tipico": "Chumbador estrutural P ≤ 300 kN"},
    "M30_A307":     {"diametro_mm": 30, "especificacao": "ASTM A307 Gr.B", "f_y_MPa": 250, "f_u_MPa": 414, "massa_kg_m": 0.555, "passo_mm": 3.50, "uso_tipico": "Chumbador estrutural P ≤ 500 kN"},
    "M36_A307":     {"diametro_mm": 36, "especificacao": "ASTM A307 Gr.B", "f_y_MPa": 250, "f_u_MPa": 414, "massa_kg_m": 0.800, "passo_mm": 4.00, "uso_tipico": "Chumbador estrutural P > 500 kN"},
    # ── ASTM A325-N (parafusos estruturais de alta resistência) ───────────────
    "M20_A325":     {"diametro_mm": 20, "especificacao": "ASTM A325-N",   "f_y_MPa": 635, "f_u_MPa": 827, "massa_kg_m": 0.247, "passo_mm": 2.50, "uso_tipico": "Ligações estruturais — NBR 8800 item 6.3"},
    "M24_A325":     {"diametro_mm": 24, "especificacao": "ASTM A325-N",   "f_y_MPa": 635, "f_u_MPa": 827, "massa_kg_m": 0.355, "passo_mm": 3.00, "uso_tipico": "Ligações estruturais — NBR 8800 item 6.3"},
    "M30_A325":     {"diametro_mm": 30, "especificacao": "ASTM A325-N",   "f_y_MPa": 635, "f_u_MPa": 827, "massa_kg_m": 0.555, "passo_mm": 3.50, "uso_tipico": "Ligações estruturais — NBR 8800 item 6.3"},
}

# ──────────────────────────────────────────────────────────────────────────────
# PERFIS W — NBR 5884:2005 / equivalente AISC
# h: altura total | bf: largura da mesa | tw: espessura da alma | tf: espessura da mesa
# A_mm2: área da seção; Ix / Iy em mm⁴; W_kg_m: massa linear
# ──────────────────────────────────────────────────────────────────────────────
_PERFIS_W: dict[str, dict[str, Any]] = {
    "W100x19":  {"h_mm": 106, "bf_mm": 103, "tw_mm":  7.1, "tf_mm":  8.8, "A_mm2":  2_480, "Ix_mm4":  4.77e6, "Iy_mm4":  1.60e6, "W_kg_m":  19.3, "norma": "NBR 5884"},
    "W150x22":  {"h_mm": 152, "bf_mm": 152, "tw_mm":  5.8, "tf_mm":  6.6, "A_mm2":  2_860, "Ix_mm4": 12.10e6, "Iy_mm4":  3.87e6, "W_kg_m":  22.5, "norma": "NBR 5884"},
    "W150x37":  {"h_mm": 162, "bf_mm": 154, "tw_mm":  8.1, "tf_mm": 11.6, "A_mm2":  4_740, "Ix_mm4": 22.20e6, "Iy_mm4":  7.07e6, "W_kg_m":  37.1, "norma": "NBR 5884"},
    "W200x36":  {"h_mm": 201, "bf_mm": 165, "tw_mm":  6.2, "tf_mm": 10.2, "A_mm2":  4_570, "Ix_mm4": 34.40e6, "Iy_mm4":  7.64e6, "W_kg_m":  35.9, "norma": "NBR 5884"},
    "W200x46":  {"h_mm": 203, "bf_mm": 203, "tw_mm":  7.2, "tf_mm": 11.0, "A_mm2":  5_900, "Ix_mm4": 45.60e6, "Iy_mm4": 15.30e6, "W_kg_m":  46.1, "norma": "NBR 5884"},
    "W200x71":  {"h_mm": 216, "bf_mm": 206, "tw_mm": 10.2, "tf_mm": 17.4, "A_mm2":  9_100, "Ix_mm4": 76.60e6, "Iy_mm4": 25.40e6, "W_kg_m":  71.5, "norma": "NBR 5884"},
    "W250x58":  {"h_mm": 252, "bf_mm": 203, "tw_mm":  8.0, "tf_mm": 13.5, "A_mm2":  7_400, "Ix_mm4": 87.00e6, "Iy_mm4": 18.80e6, "W_kg_m":  58.1, "norma": "NBR 5884"},
    "W250x89":  {"h_mm": 260, "bf_mm": 256, "tw_mm": 10.7, "tf_mm": 17.3, "A_mm2": 11_400, "Ix_mm4":142.00e6, "Iy_mm4": 48.40e6, "W_kg_m":  88.9, "norma": "NBR 5884"},
    "W250x149": {"h_mm": 282, "bf_mm": 263, "tw_mm": 17.3, "tf_mm": 28.4, "A_mm2": 19_000, "Ix_mm4":259.00e6, "Iy_mm4": 86.40e6, "W_kg_m": 149.0, "norma": "NBR 5884"},
    "W310x39":  {"h_mm": 310, "bf_mm": 165, "tw_mm":  5.8, "tf_mm":  9.7, "A_mm2":  4_970, "Ix_mm4": 84.90e6, "Iy_mm4":  7.21e6, "W_kg_m":  38.7, "norma": "NBR 5884"},
    "W310x86":  {"h_mm": 310, "bf_mm": 254, "tw_mm":  9.1, "tf_mm": 16.3, "A_mm2": 11_000, "Ix_mm4":199.00e6, "Iy_mm4": 44.50e6, "W_kg_m":  86.3, "norma": "NBR 5884"},
    "W310x129": {"h_mm": 318, "bf_mm": 308, "tw_mm": 13.1, "tf_mm": 20.6, "A_mm2": 16_500, "Ix_mm4":308.00e6, "Iy_mm4":100.00e6, "W_kg_m": 129.0, "norma": "NBR 5884"},
    "W310x202": {"h_mm": 341, "bf_mm": 315, "tw_mm": 20.1, "tf_mm": 31.8, "A_mm2": 25_800, "Ix_mm4":498.00e6, "Iy_mm4":158.00e6, "W_kg_m": 202.0, "norma": "NBR 5884"},
    "W360x51":  {"h_mm": 355, "bf_mm": 171, "tw_mm":  7.2, "tf_mm": 11.6, "A_mm2":  6_450, "Ix_mm4":141.00e6, "Iy_mm4":  9.69e6, "W_kg_m":  50.7, "norma": "NBR 5884"},
    "W360x91":  {"h_mm": 363, "bf_mm": 257, "tw_mm":  9.5, "tf_mm": 15.9, "A_mm2": 11_600, "Ix_mm4":266.00e6, "Iy_mm4": 44.80e6, "W_kg_m":  91.4, "norma": "NBR 5884"},
    "W360x147": {"h_mm": 360, "bf_mm": 370, "tw_mm": 12.3, "tf_mm": 19.8, "A_mm2": 18_800, "Ix_mm4":389.00e6, "Iy_mm4":169.00e6, "W_kg_m": 147.0, "norma": "NBR 5884"},
    "W460x74":  {"h_mm": 457, "bf_mm": 190, "tw_mm":  9.0, "tf_mm": 14.5, "A_mm2":  9_480, "Ix_mm4":333.00e6, "Iy_mm4": 16.60e6, "W_kg_m":  74.3, "norma": "NBR 5884"},
    "W460x97":  {"h_mm": 465, "bf_mm": 193, "tw_mm": 11.4, "tf_mm": 19.0, "A_mm2": 12_300, "Ix_mm4":445.00e6, "Iy_mm4": 22.80e6, "W_kg_m":  97.0, "norma": "NBR 5884"},
    "W460x177": {"h_mm": 483, "bf_mm": 286, "tw_mm": 16.6, "tf_mm": 26.9, "A_mm2": 22_500, "Ix_mm4":910.00e6, "Iy_mm4":104.00e6, "W_kg_m": 177.0, "norma": "NBR 5884"},
    "W530x85":  {"h_mm": 529, "bf_mm": 166, "tw_mm": 10.2, "tf_mm": 13.2, "A_mm2": 10_800, "Ix_mm4":477.00e6, "Iy_mm4": 13.50e6, "W_kg_m":  85.0, "norma": "NBR 5884"},
    "W610x101": {"h_mm": 603, "bf_mm": 228, "tw_mm": 10.5, "tf_mm": 14.9, "A_mm2": 12_900, "Ix_mm4":764.00e6, "Iy_mm4": 39.30e6, "W_kg_m": 101.0, "norma": "NBR 5884"},
}


# ──────────────────────────────────────────────────────────────────────────────
# Classe pública de acesso
# ──────────────────────────────────────────────────────────────────────────────

class PetrobrasStdLib:
    """
    Biblioteca de peças padrão Petrobras, pré-carregada em memória.

    Consultas são O(1) — sem acesso a disco ou banco de dados.
    Ideal para chamadas repetidas em loops de cálculo estrutural.
    """

    def __init__(self) -> None:
        self._flanges:    dict[str, dict[str, Any]] = _FLANGES
        self._parafusos:  dict[str, dict[str, Any]] = _PARAFUSOS
        self._perfis_w:   dict[str, dict[str, Any]] = _PERFIS_W

    # ── FLANGES ───────────────────────────────────────────────────────────────

    def get_flange(self, dn_pol: str, classe: str) -> dict[str, Any] | None:
        """
        Retorna dados do flange pelo DN (polegadas) e classe de pressão ASME.

        Exemplo:
            lib.get_flange('4"', 'Class 300')

        Retorna None se a combinação não existir na biblioteca.
        """
        chave = f"{dn_pol}_{classe.replace(' ', '')}"
        return self._flanges.get(chave)

    def listar_flanges(self, classe: str | None = None) -> list[dict[str, Any]]:
        """Lista todos os flanges; filtra por classe de pressão se fornecida."""
        itens = list(self._flanges.values())
        if classe:
            itens = [f for f in itens if f["classe"] == classe]
        return sorted(itens, key=lambda f: (f["classe"], f["DN_mm"]))

    def flanges_por_dn(self, dn_pol: str) -> list[dict[str, Any]]:
        """Retorna todas as classes disponíveis para um DN específico."""
        return [f for f in self._flanges.values() if f["DN_pol"] == dn_pol]

    # ── PARAFUSOS ─────────────────────────────────────────────────────────────

    def get_parafuso(self, diametro: str, especificacao: str) -> dict[str, Any] | None:
        """
        Retorna dados do parafuso/chumbador.

        Exemplos:
            lib.get_parafuso('M20', 'A193-B7')
            lib.get_parafuso('M30', 'A307')
        """
        chave = f"{diametro}_{especificacao}"
        return self._parafusos.get(chave)

    def listar_parafusos(self, especificacao: str | None = None) -> list[dict[str, Any]]:
        """Lista todos os parafusos; filtra por especificação parcial se fornecida."""
        itens = list(self._parafusos.values())
        if especificacao:
            itens = [p for p in itens if especificacao.upper() in p["especificacao"].upper()]
        return sorted(itens, key=lambda p: (p["especificacao"], p["diametro_mm"]))

    # ── PERFIS W ──────────────────────────────────────────────────────────────

    def get_perfil_w(self, nome: str) -> dict[str, Any] | None:
        """
        Retorna dados de um perfil W pelo nome normalizado.

        Exemplo:
            lib.get_perfil_w('W200x46')
        """
        return self._perfis_w.get(nome)

    def listar_perfis_w(
        self,
        W_min_kg_m: float | None = None,
        W_max_kg_m: float | None = None,
    ) -> list[dict[str, Any]]:
        """Lista perfis W ordenados por massa linear; filtra por faixa opcional."""
        itens = list(self._perfis_w.values())
        if W_min_kg_m is not None:
            itens = [p for p in itens if p["W_kg_m"] >= W_min_kg_m]
        if W_max_kg_m is not None:
            itens = [p for p in itens if p["W_kg_m"] <= W_max_kg_m]
        return sorted(itens, key=lambda p: p["W_kg_m"])

    def selecionar_perfil_por_deflexao(
        self,
        w_N_mm: float,
        L_mm: float,
        delta_lim_mm: float,
        E_MPa: float = 200_000.0,
    ) -> dict[str, Any] | None:
        """
        Seleciona o perfil W de menor massa que atende ao limite de deflexão
        em viga bi-apoiada com carga distribuída uniforme.

            I_min = (5 · w · L⁴) / (384 · E · δ_lim)

        Ref.: NBR 8800:2008 Anexo B, eq. B.2.

        Parâmetros
        ----------
        w_N_mm      : carga distribuída em N/mm
        L_mm        : comprimento entre apoios em mm
        delta_lim_mm: deflexão máxima admissível em mm
        E_MPa       : módulo de elasticidade em MPa (padrão 200 000 MPa)

        Retorna None se nenhum perfil do catálogo atender.
        """
        I_min = (5.0 * w_N_mm * L_mm ** 4) / (384.0 * E_MPa * delta_lim_mm)
        candidatos = [p for p in self._perfis_w.values() if p["Ix_mm4"] >= I_min]
        return min(candidatos, key=lambda p: p["W_kg_m"]) if candidatos else None

    # ── UTILITÁRIOS ───────────────────────────────────────────────────────────

    def summary(self) -> dict[str, int]:
        """Retorna contagem de itens em cada categoria da biblioteca."""
        return {
            "flanges":   len(self._flanges),
            "parafusos": len(self._parafusos),
            "perfis_w":  len(self._perfis_w),
        }

    def __repr__(self) -> str:  # pragma: no cover
        s = self.summary()
        return (
            f"PetrobrasStdLib("
            f"flanges={s['flanges']}, "
            f"parafusos={s['parafusos']}, "
            f"perfis_w={s['perfis_w']})"
        )
