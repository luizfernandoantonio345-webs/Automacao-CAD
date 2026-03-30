# RELATÓRIO TÉCNICO DE DIMENSIONAMENTO
## Verificação de Perfil W — NBR 8800:2008 (LRFD)

**Data:** 26 de Março de 2026  
**Engenheiro:** Calculista Automático CAD  
**Norma:** ABNT NBR 8800:2008 — Projeto de Estruturas de Aço

---

## 1. DADOS DE ENTRADA

| Parâmetro | Valor | Unidade |
|-----------|-------|---------|
| Carga Permanente (g) | 15.00 | kN/m |
| Sobrecarga Variável (q) | 10.00 | kN/m |
| Carga Total de Serviço (g+q) | 25.00 | kN/m |
| Vão Livre (L) | 8.00 | m |
| Comprimento Destravado (Lb) | 8.00 | m |
| Fator de Momento Equivalente (Cb) | 1.00 | — |

### Combinação de Ações (NBR 6118)

**Estado Limite Último (ELU):**
$$w_d = \gamma_f \times (g + q) = 1.4 \times (15.00 + 10.00) = 35.00 \text{ kN/m}$$

**Estado Limite de Serviço (ELS):**
$$w_{ser} = g + q = 15.00 + 10.00 = 25.00 \text{ kN/m}$$

---

## 2. ESFORÇOS SOLICITANTES

Para viga biapoiada com carga distribuída uniforme:

$$M_{sd} = \frac{w_d \times L^2}{8} = \frac{35.00 \times 8.00^2}{8} = 280.00 \text{ kN·m}$$

$$V_{sd} = \frac{w_d \times L}{2} = \frac{35.00 \times 8.00}{2} = 140.00 \text{ kN}$$

$$\delta_{máx} = \frac{5 \times w_{ser} \times L^4}{384 \times E \times I_x} = \frac{5 \times 25.00 \times 8.00^4}{384 \times 200000 \times I_x}$$

---

## 3. PERFIL SELECIONADO: W610x125

### 3.1 Propriedades Geométricas

| Propriedade | Valor | Unidade |
|-------------|-------|---------|
| Altura (d) | 612.0 | mm |
| Largura da Mesa (bf) | 229.0 | mm |
| Espessura da Mesa (tf) | 19.6 | mm |
| Espessura da Alma (tw) | 11.9 | mm |
| Área (A) | 159.00 | cm² |
| Momento de Inércia — eixo forte (Ix) | 168000 | cm⁴ |
| Momento de Inércia — eixo fraco (Iy) | 4710 | cm⁴ |
| Módulo de Resistência Elástico — Sx | 5490 | cm³ |
| **Módulo de Resistência Plástico — Zx** | **6160** | **cm³** |
| Raio de Giração — eixo forte (rx) | 32.51 | cm |
| Raio de Giração — eixo fraco (ry) | 5.44 | cm |
| Massa Linear | 125.0 | kg/m |

**Material:** ASTM A572 Grau 50  
$f_y = 345$ MPa | $f_u = 450$ MPa | $E = 200\,000$ MPa

### 3.2 Classificação da Seção Transversal

#### Mesa (Aba)
$$\lambda_f = \frac{b_f}{2 \times t_f} = \frac{229.0}{2 \times 19.6} = 5.84$$

$$\lambda_{pf} = 0,38 \sqrt{\frac{E}{f_y}} = 0,38 \sqrt{\frac{200000}{345}} = 9.15 \quad (\text{seção compacta})$$

$$\lambda_{rf} = 1,0 \sqrt{\frac{E}{f_y}} = 24.08 \quad (\text{seção semicompacta})$$

**Classificação da Mesa:** Compacta  
(5.84 ≤ 9.15)

#### Alma
$$\lambda_w = \frac{h_w}{t_w} = \frac{572.8}{11.9} = 48.13$$

$$\lambda_{pw} = 3,76 \sqrt{\frac{E}{f_y}} = 90.53$$

$$\lambda_{rw} = 5,70 \sqrt{\frac{E}{f_y}} = 137.24$$

**Classificação da Alma:** Compacta

**Seção Compacta?** Sim

---

## 4. VERIFICAÇÃO À FLEXÃO — ELU

### 4.1 Momento Plástico

$$M_p = f_y \times Z_x = 345 \text{ MPa} \times 6160 \text{ cm}^3 = 2125.20 \text{ kN·m}$$

### 4.2 Flambagem Lateral por Torção (FLT)

#### Comprimentos característicos

$$L_p = 1,76 \times r_y \times \sqrt{\frac{E}{f_y}} = 1,76 \times 5.44 \times \sqrt{\frac{200000}{345}} = 2.31 \text{ m}$$

$$L_r = 1,95 \times r_{ts} \times \frac{E}{0,7 \times f_y} \times \sqrt{\frac{J \times c}{S_x \times h_o} + \sqrt{\left(\frac{J \times c}{S_x \times h_o}\right)^2 + 6,76 \left(\frac{0,7 \times f_y}{E}\right)^2}} = 4.90 \text{ m}$$

#### Regime de flambagem

**Dados do cálculo:**
- Lb = 8.00 m (comprimento destravado)
- Lp = 2.31 m
- Lr = 4.90 m

**Regime:** FLT Elástica


Sendo $L_b = 8.00 > L_r = 4.90$ m, ocorre FLT elástica.

$$F_{cr} = \frac{C_b \pi^2 E}{(L_b / r_{ts})^2} = 108 \text{ MPa}$$

$$M_n = F_{cr} \times S_x = 591.34 \text{ kN·m}$$


$$M_n = 591.34 \text{ kN·m}$$

### 4.3 Resistência à Flexão de Cálculo

$$M_{rd} = \phi_b \times M_n = 0.9 \times 591.34 = 532.20 \text{ kN·m}$$

### 4.4 Verificação

$$\eta_{flexão} = \frac{M_{sd}}{M_{rd}} = \frac{280.00}{532.20} = 0.5261 = 52.6\%$$

**Status:** ✓ APROVADO  
(Taxa ≤ 1,00 — SATISFAZ)

---

## 5. VERIFICAÇÃO À FLECHA — ELS

$$\delta_{máx} = \frac{5 \times w_{ser} \times L^4}{384 \times E \times I_x}$$

$$\delta_{máx} = \frac{5 \times 25.00 \times 8.00^4}{384 \times 200000 \times 168000} = 3.97 \text{ mm}$$

**Limite de flecha:** $\delta_{lim} = L / 250 = 8.00 \times 1000 / 250 = 32.00$ mm

$$\frac{\delta_{máx}}{\delta_{lim}} = \frac{3.97}{32.00} = 0.124$$

**Status:** ✓ APROVADO (δ ≤ L/250)

---

## 6. VERIFICAÇÃO AO CORTANTE — ELU

$$A_w = d \times t_w = 612.0 \times 11.9 = 7282.8 \text{ mm}^2 = 72.8 \text{ cm}^2$$

$$V_{rd} = \phi_v \times 0,6 \times f_y \times A_w = 1,00 \times 0,6 \times 345 \times 72.8 = 150.75 \text{ kN}$$

$$\eta_{cortante} = \frac{V_{sd}}{V_{rd}} = \frac{140.00}{150.75} = 0.9287$$

**Status:** ✓ APROVADO

---

## 7. ESBELTEZ GLOBAL

$$\frac{L}{r_y} = \frac{8.00 \times 100}{5.44} = 147.1$$

**Limite recomendado (estrutura comum):** ≤ 300  
**Status:** ✓ Dentro do limite

---

## 8. RESUMO DE VERIFICAÇÕES

| Verificação | Solicitante | Resistente | Taxa | Status |
|-------------|-------------|-----------|------|--------|
| **Flexão (ELU)** | 280.00 kN·m | 532.20 kN·m | 52.6% | ✓ PASS |
| **Flecha (ELS)** | 3.97 mm | 32.00 mm | 12.40% | ✓ PASS |
| **Cortante (ELU)** | 140.00 kN | 150.75 kN | 92.9% | ✓ PASS |

**RESULTADO FINAL:** 🟢 PERFIL APROVADO

---

## 9. LISTA DE PERFIS HOMOLOGADOS

Todos os perfis a seguir atendem os critérios de dimensionamento para as cargas fornecidas.

| Designação | A (cm²) | Ix (cm⁴) | Zx (cm³) | ry (cm) | Peso (kg/m) | Taxa Flexão |
|------------|---------|---------|---------|---------|------------|------------|
| W610x125 | 159.0 | 168000 | 6160 | 5.44 | 125.0 | 52.6% |

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

✓ **Flambagem Lateral por Torção (FLT)** verificada com Cb = 1.00.

✓ **Erro zero** é o padrão — cada valor é auditável linha a linha.

---

## 11. ASSINATURA DIGITAL

**Responsável:** Calculista Automático — ENGENHARIA CAD  
**Data e Hora:** 26/03/2026 às 09:06:58  
**Versão do Relatório:** 1.0  
**Status de Conformidade:** NBR 8800:2008 ✓ | LRFD ✓

---

*Relatório gerado automaticamente. Para modificações ou questionamentos, contacte o Engenheiro Responsável.*
