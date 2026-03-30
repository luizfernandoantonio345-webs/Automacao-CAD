"""stress_test_gallery.py
=======================

BLOCO DE MATURAÇÃO — Galeria de 20 Casos (Mecânica / Civil)

Casos  1-10  (Mecânica): Torres 3 m–15 m  |  variação de largura de escada
                          e tipo de fixação (soldada vs parafusada).
                          Validação de deflexão conforme NBR 8800:2008 item 7.7.

Casos 11-20  (Civil):    Pórticos 10 t–100 t  |  redimensionamento de sapatas
                          de concreto e profundidade de chumbadores por carga.
                          Base normativa: NBR 6118:2014 e N-1710 Rev. C.

Saída: data/output/stress_test_report.txt
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Constantes físicas e limites normativos
# ──────────────────────────────────────────────────────────────────────────────
E_ACO_MPA: float = 200_000.0   # Módulo de elasticidade do aço  [NBR 6355 / AISC]
Q_ADM_KPA: float = 200.0       # Capacidade admissível do solo (kPa) – conservador
VENTO_N_MM: float = 0.30       # Carga de vento distribuída (N/mm) = 0,6 kPa × 0,5 m

# Razão L/δ para deflexão admissível (NBR 8800:2008 Tabela 7.1)
DEFLEXAO_LIMITE: dict[str, float] = {
    "soldada":    250.0,   # Ligação rígida  → L/250
    "parafusada": 200.0,   # Ligação semirrígida → L/200
}

# Catálogo de perfis W – NBR 5884 / equivalente AISC  (I_x em mm⁴)
PERFIS_W: list[dict[str, Any]] = [
    {"nome": "W150x22",  "Ix": 12.1e6,  "A_mm2": 2_860,  "W_kg_m": 22.5},
    {"nome": "W150x37",  "Ix": 22.2e6,  "A_mm2": 4_740,  "W_kg_m": 37.1},
    {"nome": "W200x46",  "Ix": 45.6e6,  "A_mm2": 5_900,  "W_kg_m": 46.1},
    {"nome": "W200x71",  "Ix": 76.6e6,  "A_mm2": 9_100,  "W_kg_m": 71.5},
    {"nome": "W250x89",  "Ix": 142.0e6, "A_mm2": 11_400, "W_kg_m": 88.9},
    {"nome": "W250x149", "Ix": 259.0e6, "A_mm2": 19_000, "W_kg_m": 149.0},
    {"nome": "W310x129", "Ix": 308.0e6, "A_mm2": 16_500, "W_kg_m": 129.0},
    {"nome": "W310x202", "Ix": 498.0e6, "A_mm2": 25_800, "W_kg_m": 202.0},
]


# ──────────────────────────────────────────────────────────────────────────────
# Módulo MECÂNICA — Deflexão e auto-correção de perfil
# ──────────────────────────────────────────────────────────────────────────────

def _deflexao_mm(w_N_mm: float, L_mm: float, I_mm4: float) -> float:
    """
    Deflexão máxima — viga bi-apoiada, carga uniformemente distribuída.

        δ = (5 · w · L⁴) / (384 · E · I)

    Ref.: NBR 8800:2008 Anexo B, eq. B.2
    """
    return (5.0 * w_N_mm * L_mm ** 4) / (384.0 * E_ACO_MPA * I_mm4)


def _perfil_inicial(altura_m: float) -> dict[str, Any]:
    """Perfil de partida por faixa de altura (heurística conservadora)."""
    if altura_m <= 6.0:
        return PERFIS_W[0]   # W150x22
    elif altura_m <= 9.0:
        return PERFIS_W[1]   # W150x37
    elif altura_m <= 12.0:
        return PERFIS_W[2]   # W200x46
    else:
        return PERFIS_W[3]   # W200x71


def processar_caso_mecanica(
    num_caso: int,
    altura_m: float,
    largura_mm: int,
    fixacao: str,
) -> dict[str, Any]:
    """
    Processa um caso mecânico: calcula deflexão e aplica upgrade automático
    de perfil até atender ao limite normativo.

    Normas: NBR 8800:2008 item 7.7 / N-1710 Rev. C §6.4.
    """
    L_mm = altura_m * 1000.0
    limite_ratio = DEFLEXAO_LIMITE[fixacao]
    delta_lim_mm = L_mm / limite_ratio

    perfil = _perfil_inicial(altura_m)
    upgrades: list[str] = []
    erros: list[str] = []

    idx = next(i for i, p in enumerate(PERFIS_W) if p["nome"] == perfil["nome"])

    # Loop de auto-correção ─────────────────────────────────────────────────
    while True:
        delta_calc = _deflexao_mm(VENTO_N_MM, L_mm, perfil["Ix"])
        if delta_calc <= delta_lim_mm:
            break  # Perfil aprovado

        erros.append(
            f"Perfil {perfil['nome']}: δ={delta_calc:.2f} mm > δ_lim={delta_lim_mm:.2f} mm "
            f"(L/{limite_ratio:.0f}) — upgrade aplicado automaticamente"
        )
        idx += 1
        if idx >= len(PERFIS_W):
            erros.append(
                "ERRO CRÍTICO: catálogo esgotado — avaliar solução especial (treliça / tubo estrutural)."
            )
            break
        upgrades.append(f"{perfil['nome']} → {PERFIS_W[idx]['nome']}")
        perfil = PERFIS_W[idx]

    delta_final = _deflexao_mm(VENTO_N_MM, L_mm, perfil["Ix"])
    status = "APROVADO" if delta_final <= delta_lim_mm else "REPROVADO"

    return {
        "caso": num_caso,
        "tipo": "MECANICA",
        "altura_m": altura_m,
        "largura_escada_mm": largura_mm,
        "fixacao": fixacao,
        "perfil_final": perfil["nome"],
        "Ix_mm4": perfil["Ix"],
        "delta_lim_mm": round(delta_lim_mm, 2),
        "delta_calc_mm": round(delta_final, 2),
        "status": status,
        "upgrades_realizados": upgrades,
        "erros": erros,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Módulo CIVIL — Sapata de concreto + chumbadores
# ──────────────────────────────────────────────────────────────────────────────

def _dimensionar_sapata(carga_kN: float) -> dict[str, Any]:
    """
    Dimensiona sapata isolada quadrada.

        A_req = P / q_adm    (m²)
        l_sap = √(A_req)     (m)
        h_sap ≥ max(0,30; 0,40 · l_sap)

    Ref.: NBR 6118:2014 item 22.5.1 / N-1710 Rev. C §8.3.
    """
    A_req = carga_kN / Q_ADM_KPA          # q_adm em kN/m² → A em m²
    lado = math.sqrt(A_req)
    h = max(0.30, round(lado * 0.40, 2))
    alerta_estaca = lado > 2.50           # Sapata impraticável — recomendar estacas

    resultado: dict[str, Any] = {
        "A_req_m2": round(A_req, 3),
        "lado_m": round(lado, 3),
        "h_sapata_m": round(h, 3),
        "alerta_estaca": alerta_estaca,
    }

    if alerta_estaca:
        # Auto-correção: dividir em 2 sapatas menores
        lado_corr = round(math.sqrt(A_req / 2), 3)
        resultado["solucao_corrigida"] = {
            "tipo": "2 sapatas isoladas (NBR 6118 cap. 23)",
            "lado_m": lado_corr,
            "A_req_m2": round(A_req / 2, 3),
        }

    return resultado


def _dimensionar_chumbador(carga_kN: float) -> dict[str, Any]:
    """
    Dimensiona chumbadores de ancoragem.

    Tabela de seleção por faixa de carga:
        P ≤ 150 kN → M20  |  P ≤ 300 kN → M25  |  P ≤ 500 kN → M30  |  P > 500 kN → M36

    L_anc = max(L_tabela; 20·d_bolt)   — N-1710 Rev. C §9.2.4 / NBR 6118:2014 item 9.4.2.3

    Material padrão: ASTM A307 Grau B (f_y = 250 MPa, f_u = 414 MPa).
    """
    if carga_kN <= 150.0:
        d_mm, qtd, L_tab = 20, 4, 400
    elif carga_kN <= 300.0:
        d_mm, qtd, L_tab = 25, 4, 500
    elif carga_kN <= 500.0:
        d_mm, qtd, L_tab = 30, 6, 600
    elif carga_kN <= 700.0:
        d_mm, qtd, L_tab = 36, 6, 720
    else:
        d_mm, qtd, L_tab = 36, 8, 800

    L_anc = max(L_tab, 20 * d_mm)     # §9.2.4 — comprimento mínimo de ancoragem

    return {
        "diametro_mm": d_mm,
        "quantidade": qtd,
        "comprimento_ancoragem_mm": L_anc,
        "especificacao": f"M{d_mm} ASTM A307 Gr.B — {qtd} und.",
        "norma_ref": "N-1710 §9.2.4 / NBR 6118:2014 item 9.4.2.3",
    }


def processar_caso_civil(
    num_caso: int,
    carga_t: float,
) -> dict[str, Any]:
    """Processa um caso civil: sapata de concreto + chumbadores + auto-correção."""
    carga_kN = carga_t * 9.81
    erros: list[str] = []
    correcoes: list[str] = []

    sapata = _dimensionar_sapata(carga_kN)
    chumbador = _dimensionar_chumbador(carga_kN)

    if sapata["alerta_estaca"]:
        erros.append(
            f"Sapata com lado={sapata['lado_m']:.2f} m > 2,50 m: dimensões excessivas para fundação direta. "
            "Interferência estrutural detectada  — NBR 6118:2014 cap. 23 recomenda fundação profunda."
        )
        sc = sapata["solucao_corrigida"]
        correcoes.append(
            f"Auto-correção aplicada: {sc['tipo']}  "
            f"lado={sc['lado_m']:.2f} m × {sc['lado_m']:.2f} m  (A={sc['A_req_m2']:.2f} m² cada)"
        )

    status = "APROVADO" if not erros else "CORRIGIDO"

    return {
        "caso": num_caso,
        "tipo": "CIVIL",
        "carga_t": carga_t,
        "carga_kN": round(carga_kN, 2),
        "sapata": sapata,
        "chumbador": chumbador,
        "status": status,
        "erros": erros,
        "correcoes": correcoes,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Renderização do relatório TXT
# ──────────────────────────────────────────────────────────────────────────────

def _formatar_relatorio(resultados: list[dict[str, Any]], ts: str) -> str:
    linhas: list[str] = [
        "=" * 80,
        "  STRESS TEST REPORT  —  BLOCO DE MATURAÇÃO",
        f"  Gerado em  : {ts}",
        f"  Total casos: {len(resultados)}",
        "=" * 80,
        "",
    ]

    erros_total = 0
    correcoes_total = 0

    for r in resultados:
        sep = f"─── CASO {r['caso']:02d}  ({r['tipo']}) " + "─" * (54 - len(r['tipo']))
        linhas.append(sep)

        if r["tipo"] == "MECANICA":
            linhas.append(f"  Altura torre        : {r['altura_m']:.1f} m")
            linhas.append(f"  Largura escada      : {r['largura_escada_mm']} mm")
            linhas.append(f"  Tipo de fixação     : {r['fixacao'].upper()}")
            linhas.append(
                f"  Verificação deflexão: δ_calc = {r['delta_calc_mm']:.2f} mm  "
                f"≤  δ_lim = {r['delta_lim_mm']:.2f} mm  "
                f"(L/{DEFLEXAO_LIMITE[r['fixacao']]:.0f})"
            )
            linhas.append(f"  Perfil final        : {r['perfil_final']}")
            linhas.append(f"  STATUS              : {r['status']}")
            if r["upgrades_realizados"]:
                linhas.append(f"  Auto-correções      : {' → '.join(r['upgrades_realizados'])}")
                correcoes_total += len(r["upgrades_realizados"])
            for e in r["erros"]:
                linhas.append(f"  [INTERFERÊNCIA] {e}")
                erros_total += 1

        else:  # CIVIL
            sap = r["sapata"]
            chu = r["chumbador"]
            linhas.append(f"  Carga               : {r['carga_t']:.0f} t  ({r['carga_kN']:.1f} kN)")
            linhas.append(
                f"  Sapata dimensionada : {sap['lado_m']:.2f} m × {sap['lado_m']:.2f} m  "
                f"(h = {sap['h_sapata_m']:.2f} m)  |  A_req = {sap['A_req_m2']:.3f} m²"
            )
            linhas.append(
                f"  Chumbadores         : {chu['especificacao']}  "
                f"L_anc = {chu['comprimento_ancoragem_mm']} mm"
            )
            linhas.append(f"  Ref. normativa      : {chu['norma_ref']}")
            linhas.append(f"  STATUS              : {r['status']}")
            for e in r["erros"]:
                linhas.append(f"  [INTERFERÊNCIA] {e}")
                erros_total += 1
            for c in r["correcoes"]:
                linhas.append(f"  [CORRIGIDO]     {c}")
                correcoes_total += 1
            if "solucao_corrigida" in sap:
                sc = sap["solucao_corrigida"]
                linhas.append(f"  Solução adotada     : {sc['tipo']}")
                linhas.append(f"                        lado = {sc['lado_m']:.2f} m  |  A = {sc['A_req_m2']:.2f} m²")

        linhas.append("")

    # ── Resumo global ────────────────────────────────────────────────────────
    total = len(resultados)
    taxa_ok = ((total - erros_total) / total) * 100.0 if total else 0.0

    linhas += [
        "=" * 80,
        "  RESUMO GLOBAL DE AUTO-DIAGNÓSTICO",
        "=" * 80,
        f"  Casos testados                : {total}",
        f"  Erros de interferência/design : {erros_total}",
        f"  Auto-correções aplicadas      : {correcoes_total}",
        f"  Taxa de sucesso (sem interv.) : {taxa_ok:.1f} %",
        "",
        "  PARÂMETROS DE VENTO/SOLO ADOTADOS:",
        f"  • Carga de vento uniforme     : {VENTO_N_MM:.2f} N/mm  (0,6 kPa × 0,5 m projeção)",
        f"  • Capacidade admissível solo  : {Q_ADM_KPA:.0f} kPa  (argila firme — conservador)",
        f"  • Módulo de elasticidade aço  : {E_ACO_MPA:,.0f} MPa",
        "",
        "  REFERÊNCIAS NORMATIVAS APLICADAS:",
        "  • NBR 8800:2008  — Tab. 7.1 / Eq. B.2   (deflexões e perfis estruturais)",
        "  • NBR 6118:2014  — item 22.5.1 / cap. 23 (sapatas e fundações profundas)",
        "  • NBR 5884:2005  — catálogo de perfis W   (dimensões e propriedades)",
        "  • N-1710 Rev. C  — §6.4 / §8.3 / §9.2.4  (escadas, sapatas e chumbadores)",
        "  • NR-12:2022     — Anexo I                (proteção de acesso industrial)",
        "=" * 80,
    ]
    return "\n".join(linhas)


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de entrada
# ──────────────────────────────────────────────────────────────────────────────

def executar_galeria(output_dir: Path) -> None:
    """Executa os 20 casos e grava stress_test_report.txt."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Definição dos 20 casos ─────────────────────────────────────────────────
    casos_mecanica = [
        (1,   3.0,  400, "soldada"),
        (2,   4.5,  400, "parafusada"),
        (3,   6.0,  450, "soldada"),
        (4,   7.5,  450, "parafusada"),
        (5,   9.0,  450, "soldada"),
        (6,  10.0,  500, "parafusada"),
        (7,  11.0,  500, "soldada"),
        (8,  12.0,  500, "parafusada"),
        (9,  13.0,  500, "soldada"),
        (10, 15.0,  500, "parafusada"),
    ]

    casos_civil = [
        (11,  10.0),
        (12,  20.0),
        (13,  30.0),
        (14,  40.0),
        (15,  50.0),
        (16,  60.0),
        (17,  70.0),
        (18,  80.0),
        (19,  90.0),
        (20, 100.0),
    ]

    resultados: list[dict[str, Any]] = []

    for num, alt, larg, fix in casos_mecanica:
        resultados.append(processar_caso_mecanica(num, alt, larg, fix))

    for num, carga in casos_civil:
        resultados.append(processar_caso_civil(num, carga))

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    relatorio = _formatar_relatorio(resultados, ts)

    report_path = output_dir / "stress_test_report.txt"
    report_path.write_text(relatorio, encoding="utf-8")
    print(f"\n[OK] stress_test_report.txt gravado em: {report_path}\n")
    print(relatorio)


if __name__ == "__main__":
    base = Path(__file__).resolve().parents[2] / "data" / "output"
    executar_galeria(base)
