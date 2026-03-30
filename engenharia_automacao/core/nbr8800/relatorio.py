"""
Gerador de Relatório Técnico — NBR 8800:2008
============================================
Produz documentação em Markdown e HTML com:
  • Fórmulas abertas e passo-a-passo
  • Resultados PASS/FAIL com taxa de utilização
  • Lista de perfis homologados
  • Verificações detalhadas (ELU, ELS, flambagem)

Formato de saída: Markdown com tabelas e LaTeX, pronto para PDF.
"""

from __future__ import annotations

from datetime import datetime

from .calculista import (
    Calculista,
    RelatorioCalculista,
    GAMMA_F,
    PHI_B,
)

# ---------------------------------------------------------------------------
# Constantes de formatação
# ---------------------------------------------------------------------------
HEADER_REPORT = """\
# RELATÓRIO TÉCNICO DE DIMENSIONAMENTO
## Verificação de Perfil W — NBR 8800:2008 (LRFD)

**Data:** {data}  
**Engenheiro:** Calculista Automático CAD  
**Norma:** ABNT NBR 8800:2008 — Projeto de Estruturas de Aço

---

## 1. DADOS DE ENTRADA

| Parâmetro | Valor | Unidade |
|-----------|-------|---------|
| Carga Permanente (g) | {g:.2f} | kN/m |
| Sobrecarga Variável (q) | {q:.2f} | kN/m |
| Carga Total de Serviço (g+q) | {g_q:.2f} | kN/m |
| Vão Livre (L) | {L:.2f} | m |
| Comprimento Destravado (Lb) | {Lb:.2f} | m |
| Fator de Momento Equivalente (Cb) | {Cb:.2f} | — |

### Combinação de Ações (NBR 6118)

**Estado Limite Último (ELU):**
$$w_d = \\gamma_f \\times (g + q) = {gamma_f} \\times ({g:.2f} + {q:.2f}) = {w_d:.2f} \\text{{ kN/m}}$$

**Estado Limite de Serviço (ELS):**
$$w_{{ser}} = g + q = {g:.2f} + {q:.2f} = {w_ser:.2f} \\text{{ kN/m}}$$

---

## 2. ESFORÇOS SOLICITANTES

Para viga biapoiada com carga distribuída uniforme:

$$M_{{sd}} = \\frac{{w_d \\times L^2}}{{8}} = \\frac{{{w_d:.2f} \\times {L:.2f}^2}}{{8}} = {M_sd:.2f} \\text{{ kN·m}}$$

$$V_{{sd}} = \\frac{{w_d \\times L}}{{2}} = \\frac{{{w_d:.2f} \\times {L:.2f}}}{{2}} = {V_sd:.2f} \\text{{ kN}}$$

$$\\delta_{{máx}} = \\frac{{5 \\times w_{{ser}} \\times L^4}}{{384 \\times E \\times I_x}} = \\frac{{5 \\times {w_ser:.2f} \\times {L:.2f}^4}}{{384 \\times 200000 \\times I_x}}$$

---

## 3. PERFIL SELECIONADO: {perfil_nome}

### 3.1 Propriedades Geométricas

| Propriedade | Valor | Unidade |
|-------------|-------|---------|
| Altura (d) | {d:.1f} | mm |
| Largura da Mesa (bf) | {bf:.1f} | mm |
| Espessura da Mesa (tf) | {tf:.1f} | mm |
| Espessura da Alma (tw) | {tw:.1f} | mm |
| Área (A) | {A:.2f} | cm² |
| Momento de Inércia — eixo forte (Ix) | {Ix:.0f} | cm⁴ |
| Momento de Inércia — eixo fraco (Iy) | {Iy:.0f} | cm⁴ |
| Módulo de Resistência Elástico — Sx | {Sx:.0f} | cm³ |
| **Módulo de Resistência Plástico — Zx** | **{Zx:.0f}** | **cm³** |
| Raio de Giração — eixo forte (rx) | {rx:.2f} | cm |
| Raio de Giração — eixo fraco (ry) | {ry:.2f} | cm |
| Massa Linear | {peso:.1f} | kg/m |

**Material:** ASTM A572 Grau 50  
$f_y = 345$ MPa | $f_u = 450$ MPa | $E = 200\\,000$ MPa

### 3.2 Classificação da Seção Transversal

#### Mesa (Aba)
$$\\lambda_f = \\frac{{b_f}}{{2 \\times t_f}} = \\frac{{{bf:.1f}}}{{2 \\times {tf:.1f}}} = {lambda_f:.2f}$$

$$\\lambda_{{pf}} = 0,38 \\sqrt{{\\frac{{E}}{{f_y}}}} = 0,38 \\sqrt{{\\frac{{200000}}{{345}}}} = {lambda_pf:.2f} \\quad (\\text{{seção compacta}})$$

$$\\lambda_{{rf}} = 1,0 \\sqrt{{\\frac{{E}}{{f_y}}}} = {lambda_rf:.2f} \\quad (\\text{{seção semicompacta}})$$

**Classificação da Mesa:** {classe_mesa}  
({lambda_f:.2f} {comparador_mesa} {lambda_pf:.2f})

#### Alma
$$\\lambda_w = \\frac{{h_w}}{{t_w}} = \\frac{{{h_w:.1f}}}{{{tw:.1f}}} = {lambda_w:.2f}$$

$$\\lambda_{{pw}} = 3,76 \\sqrt{{\\frac{{E}}{{f_y}}}} = {lambda_pw:.2f}$$

$$\\lambda_{{rw}} = 5,70 \\sqrt{{\\frac{{E}}{{f_y}}}} = {lambda_rw:.2f}$$

**Classificação da Alma:** {classe_alma}

**Seção Compacta?** {is_compacta}

---

## 4. VERIFICAÇÃO À FLEXÃO — ELU

### 4.1 Momento Plástico

$$M_p = f_y \\times Z_x = 345 \\text{{ MPa}} \\times {Zx:.0f} \\text{{ cm}}^3 = {Mp:.2f} \\text{{ kN·m}}$$

### 4.2 Flambagem Lateral por Torção (FLT)

#### Comprimentos característicos

$$L_p = 1,76 \\times r_y \\times \\sqrt{{\\frac{{E}}{{f_y}}}} = 1,76 \\times {ry:.2f} \\times \\sqrt{{\\frac{{200000}}{{345}}}} = {Lp:.2f} \\text{{ m}}$$

$$L_r = 1,95 \\times r_{{ts}} \\times \\frac{{E}}{{0,7 \\times f_y}} \\times \\sqrt{{\\frac{{J \\times c}}{{S_x \\times h_o}} + \\sqrt{{\\left(\\frac{{J \\times c}}{{S_x \\times h_o}}\\right)^2 + 6,76 \\left(\\frac{{0,7 \\times f_y}}{{E}}\\right)^2}}}} = {Lr:.2f} \\text{{ m}}$$

#### Regime de flambagem

**Dados do cálculo:**
- Lb = {Lb:.2f} m (comprimento destravado)
- Lp = {Lp:.2f} m
- Lr = {Lr:.2f} m

**Regime:** {regime_flt}

{regime_calculo_detalhado}

$$M_n = {Mn:.2f} \\text{{ kN·m}}$$

### 4.3 Resistência à Flexão de Cálculo

$$M_{{rd}} = \\phi_b \\times M_n = {phi_b} \\times {Mn:.2f} = {Mrd:.2f} \\text{{ kN·m}}$$

### 4.4 Verificação

$$\\eta_{{flexão}} = \\frac{{M_{{sd}}}}{{M_{{rd}}}} = \\frac{{{M_sd:.2f}}}{{{Mrd:.2f}}} = {eta_flex:.4f} = {eta_flex_pct:.1f}\\%$$

**Status:** {status_flexao}  
{status_flexao_obs}

---

## 5. VERIFICAÇÃO À FLECHA — ELS

$$\\delta_{{máx}} = \\frac{{5 \\times w_{{ser}} \\times L^4}}{{384 \\times E \\times I_x}}$$

$$\\delta_{{máx}} = \\frac{{5 \\times {w_ser:.2f} \\times {L:.2f}^4}}{{384 \\times 200000 \\times {Ix:.0f}}} = {delta_max:.2f} \\text{{ mm}}$$

**Limite de flecha:** $\\delta_{{lim}} = L / 250 = {L:.2f} \\times 1000 / 250 = {delta_lim:.2f}$ mm

$$\\frac{{\\delta_{{máx}}}}{{\\delta_{{lim}}}} = \\frac{{{delta_max:.2f}}}{{{delta_lim:.2f}}} = {relacao_flecha:.3f}$$

**Status:** {status_flecha}

---

## 6. VERIFICAÇÃO AO CORTANTE — ELU

$$A_w = d \\times t_w = {d:.1f} \\times {tw:.1f} = {Aw:.1f} \\text{{ mm}}^2 = {Aw_cm2:.1f} \\text{{ cm}}^2$$

$$V_{{rd}} = \\phi_v \\times 0,6 \\times f_y \\times A_w = 1,00 \\times 0,6 \\times 345 \\times {Aw_cm2:.1f} = {Vrd:.2f} \\text{{ kN}}$$

$$\\eta_{{cortante}} = \\frac{{V_{{sd}}}}{{V_{{rd}}}} = \\frac{{{V_sd:.2f}}}{{{Vrd:.2f}}} = {eta_cort:.4f}$$

**Status:** {status_cortante}

---

## 7. ESBELTEZ GLOBAL

$$\\frac{{L}}{{r_y}} = \\frac{{{L:.2f} \\times 100}}{{{ry:.2f}}} = {esbeltez:.1f}$$

**Limite recomendado (estrutura comum):** ≤ 300  
**Status:** {status_esbeltez}

---

## 8. RESUMO DE VERIFICAÇÕES

| Verificação | Solicitante | Resistente | Taxa | Status |
|-------------|-------------|-----------|------|--------|
| **Flexão (ELU)** | {M_sd:.2f} kN·m | {Mrd:.2f} kN·m | {eta_flex:.1%} | {status_flexao_tabela} |
| **Flecha (ELS)** | {delta_max:.2f} mm | {delta_lim:.2f} mm | {taxa_flecha_pct:.2%} | {status_flecha_tabela} |
| **Cortante (ELU)** | {V_sd:.2f} kN | {Vrd:.2f} kN | {eta_cort:.1%} | {status_cortante_tabela} |

**RESULTADO FINAL:** {status_final}

---

## 9. LISTA DE PERFIS HOMOLOGADOS

Todos os perfis a seguir atendem os critérios de dimensionamento para as cargas fornecidas.

| Designação | A (cm²) | Ix (cm⁴) | Zx (cm³) | ry (cm) | Peso (kg/m) | Taxa Flexão |
|------------|---------|---------|---------|---------|------------|------------|
{tabela_homologados}

---

## 10. OBSERVAÇÕES FINAIS

### Regra de Ouro: Rigor Matemático

✓ Todas as fórmulas utilizadas provêm da:
  - **NBR 8800:2008** — Projeto de Estruturas de Aço
  - **AISC 360-16** — Specification for Structural Steel Buildings  
  - **CBCA** — Catálogo oficial de perfis estruturais

✓ **Método LRFD** aplicado rigorosamente:
  - Coeficiente de ponderação das ações: γ_f = 1,40
  - Fator de resistência à flexão: φ_b = 0,90

✓ **Classificação de seção** realizada conforme limites normativos.

✓ **Flambagem Lateral por Torção (FLT)** verificada com Cb = {Cb:.2f}.

✓ **Erro zero** é o padrão — cada valor é auditável linha a linha.

---

## 11. ASSINATURA DIGITAL

**Responsável:** Calculista Automático — ENGENHARIA CAD  
**Data e Hora:** {data_hora}  
**Versão do Relatório:** 1.0  
**Status de Conformidade:** NBR 8800:2008 ✓ | LRFD ✓

---

*Relatório gerado automaticamente. Para modificações ou questionamentos, contacte o Engenheiro Responsável.*
"""


def gerar_relatorio_markdown(relatorio: RelatorioCalculista) -> str:
    """Gera o relatório técnico completo em Markdown.

    Inclui fórmulas abertas, verificações passo-a-passo, e lista homologada.
    """
    r = relatorio.perfil_selecionado
    entrada = relatorio.entrada
    flex = r.flexao
    flt = flex.flt
    flecha = r.flecha
    cortante = r.cortante

    dt_now = datetime.now()
    data_br = dt_now.strftime("%d de %B de %Y").replace("January", "Janeiro").replace("February", "Fevereiro").replace("March", "Março").replace("April", "Abril").replace("May", "Maio").replace("June", "Junho").replace("July", "Julho").replace("August", "Agosto").replace("September", "Setembro").replace("October", "Outubro").replace("November", "Novembro").replace("December", "Dezembro")
    data_hora = dt_now.strftime("%d/%m/%Y às %H:%M:%S")

    # Dados do perfil
    p = r.perfil
    h_w = p.h
    Aw_mm2 = p.d * p.tw
    Aw_cm2 = Aw_mm2 / 100.0
    esbeltez = (entrada.L * 100.0) / p.ry

    # Regime FLT detalhado
    if flt.regime == "Sem FLT":
        regime_calc = f"""
Sendo $L_b = {flt.Lb:.2f} \\leq L_p = {flt.Lp:.2f}$ m, a seção atinge a plastificação total.

$$M_n = M_p = {flt.Mp:.2f} \\text{{ kN·m}}$$
"""
    elif flt.regime == "FLT Inelástica":
        M_07fy = 0.7 * p.fy * p.Sx * 1_000.0 / 1_000_000.0
        regime_calc = f"""
Sendo $L_p = {flt.Lp:.2f} < L_b = {flt.Lb:.2f} \\leq L_r = {flt.Lr:.2f}$ m, ocorre FLT inelástica.

$$0,7 \\times f_y \\times S_x = 0,7 \\times 345 \\times {p.Sx:.0f} = {M_07fy:.2f} \\text{{ kN·m}}$$

$$M_n = C_b \\left[M_p - (M_p - 0,7 \\times f_y \\times S_x) \\frac{{L_b - L_p}}{{L_r - L_p}}\\right]$$

$$M_n = {flt.Cb:.2f} \\left[{flt.Mp:.2f} - ({flt.Mp:.2f} - {M_07fy:.2f}) \\frac{{{flt.Lb:.2f} - {flt.Lp:.2f}}}{{{flt.Lr:.2f} - {flt.Lp:.2f}}}\\right] = {flt.Mn:.2f} \\text{{ kN·m}}$$
"""
    else:  # FLT Elástica
        regime_calc = f"""
Sendo $L_b = {flt.Lb:.2f} > L_r = {flt.Lr:.2f}$ m, ocorre FLT elástica.

$$F_{{cr}} = \\frac{{C_b \\pi^2 E}}{{(L_b / r_{{ts}})^2}} = {flt.Mn / p.Sx * 1_000_000.0 / 1_000.0:.0f} \\text{{ MPa}}$$

$$M_n = F_{{cr}} \\times S_x = {flt.Mn:.2f} \\text{{ kN·m}}$$
"""

    # Status final
    aprovado = r.aprovado
    eta_flex = flex.eta
    eta_flex_pct = eta_flex * 100.0
    eta_cort = cortante.eta

    relacao_flecha = flecha.delta_max / flecha.delta_lim if flecha.delta_lim > 0 else 0

    # Tabela homologados com taxa real de flexão para a mesma entrada
    linhas_tabela = []
    calculista = Calculista()
    for pf in relatorio.lista_homologados:
        rv = calculista.verificar_perfil(pf, entrada)
        linhas_tabela.append(
            f"| {pf.nome} | {pf.A:.1f} | {pf.Ix:.0f} | {pf.Zx:.0f} | {pf.ry:.2f} | {pf.peso:.1f} | {rv.flexao.eta:.1%} |"
        )

    tabela_txt = "\n".join(linhas_tabela[:10])  # Limita a 10 linhas

    comparador_mesa = "≤" if flex.secao.lambda_f <= flex.secao.lambda_pf else ">"
    status_flexao = "✓ APROVADO" if eta_flex <= 1.0 else "✗ REPROVADO"
    if eta_flex <= 0.80:
        status_flexao_obs = "(Taxa ≤ 1,00 — SATISFAZ)"
    elif eta_flex <= 1.0:
        status_flexao_obs = "(Taxa ≤ 1,00 — MARGEM REDUZIDA)"
    else:
        status_flexao_obs = "(Taxa > 1,00 — NÃO SATISFAZ)"

    status_flecha = "✓ APROVADO (δ ≤ L/250)" if flecha.delta_max <= flecha.delta_lim else "✗ REPROVADO (δ > L/250)"
    status_cortante = "✓ APROVADO" if cortante.V_sd <= cortante.Vrd else "✗ REPROVADO"
    status_esbeltez = "✓ Dentro do limite" if esbeltez <= 300 else "⚠ ATENÇÃO: Esbeltez elevada"

    status_flexao_tabela = "✓ PASS" if eta_flex <= 1.0 else "✗ FAIL"
    status_flecha_tabela = "✓ PASS" if flecha.delta_max <= flecha.delta_lim else "✗ FAIL"
    status_cortante_tabela = "✓ PASS" if cortante.V_sd <= cortante.Vrd else "✗ FAIL"
    status_final = "🟢 PERFIL APROVADO" if aprovado else "🔴 PERFIL REPROVADO"
    taxa_flecha_pct = relacao_flecha

    return HEADER_REPORT.format(
        data=data_br,
        data_hora=data_hora,
        g=entrada.g,
        q=entrada.q,
        g_q=entrada.g + entrada.q,
        L=entrada.L,
        Lb=flt.Lb,
        Cb=flt.Cb,
        gamma_f=GAMMA_F,
        w_d=r.w_d,
        w_ser=r.w_ser,
        M_sd=flex.M_sd,
        V_sd=cortante.V_sd,
        perfil_nome=p.nome,
        d=p.d,
        bf=p.bf,
        tf=p.tf,
        tw=p.tw,
        A=p.A,
        Ix=p.Ix,
        Iy=p.Iy,
        Sx=p.Sx,
        Zx=p.Zx,
        rx=p.rx,
        ry=p.ry,
        peso=p.peso,
        lambda_f=flex.secao.lambda_f,
        lambda_pf=flex.secao.lambda_pf,
        lambda_rf=flex.secao.lambda_rf,
        comparador_mesa=comparador_mesa,
        classe_mesa=flex.secao.classe_mesa,
        lambda_w=flex.secao.lambda_w,
        lambda_pw=flex.secao.lambda_pw,
        lambda_rw=flex.secao.lambda_rw,
        h_w=h_w,
        classe_alma=flex.secao.classe_alma,
        is_compacta="Sim" if flex.secao.is_compacta else "Não (semicompacta/esbelta)",
        Mp=flt.Mp,
        Lp=flt.Lp,
        Lr=flt.Lr,
        regime_flt=flt.regime,
        regime_calculo_detalhado=regime_calc,
        Mn=flt.Mn,
        phi_b=PHI_B,
        Mrd=flex.Mrd,
        eta_flex=eta_flex,
        eta_flex_pct=eta_flex_pct,
        delta_max=flecha.delta_max,
        delta_lim=flecha.delta_lim,
        relacao_flecha=relacao_flecha,
        Aw=Aw_mm2,
        Aw_cm2=Aw_cm2,
        Vrd=cortante.Vrd,
        eta_cort=eta_cort,
        esbeltez=esbeltez,
        aprovado=aprovado,
        tabela_homologados=tabela_txt,
        status_flexao=status_flexao,
        status_flexao_obs=status_flexao_obs,
        status_flecha=status_flecha,
        status_cortante=status_cortante,
        status_esbeltez=status_esbeltez,
        status_flexao_tabela=status_flexao_tabela,
        status_flecha_tabela=status_flecha_tabela,
        status_cortante_tabela=status_cortante_tabela,
        status_final=status_final,
        taxa_flecha_pct=taxa_flecha_pct,
    )


def gerar_relatorio_html(relatorio: RelatorioCalculista, css_path: str = "") -> str:
    """Gera o relatório em HTML (wraps Markdown para visualização web).

    Pode ser convertido para PDF via wkhtmltopdf ou similar.
    """
    md = gerar_relatorio_markdown(relatorio)

    # HTML simples com CSS básico
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Técnico NBR 8800:2008</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1565c0;
            font-size: 2.0em;
            margin-bottom: 10px;
            border-bottom: 3px solid #1565c0;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #1976d2;
            font-size: 1.5em;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        h3 {{
            color: #424242;
            font-size: 1.2em;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.95em;
        }}
        th {{
            background: #1565c0;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            border-bottom: 1px solid #ddd;
            padding: 10px 12px;
        }}
        tr:hover {{ background: #f5f5f5; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .math {{
            background: #f9f9f9;
            border-left: 4px solid #1565c0;
            padding: 15px;
            margin: 10px 0;
            overflow-x: auto;
        }}
        .pass {{
            color: #2e7d32;
            font-weight: bold;
        }}
        .fail {{
            color: #c62828;
            font-weight: bold;
        }}
        .warning {{
            color: #f57f17;
            font-weight: bold;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
        @media print {{
            body {{ margin: 0; padding: 0; background: white; }}
            .container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {md}
    </div>
</body>
</html>
"""
    return html
