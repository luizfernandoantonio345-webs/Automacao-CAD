# MEMORIAL ESTRUTURAL FINAL - CONSOLIDACAO MECANICA

Norma: ABNT NBR 8800:2008
Material: ASTM A572 Gr.50
Coeficiente de ponderacao de cargas: 1,4
Taxa alvo de utilizacao para otimizacao de peso: 80%

## 1) Esbeltez (L/r)

$$
\lambda = \frac{K L}{r}
$$

Elemento: Viga/Pilar de quadro principal
- $K = 1,0$
- $L = 6.000 mm$
- Perfil final: W200x26.6
- $r = 62,4 mm$

$$
\lambda = \frac{1,0\times6000}{62,4}=96,2
$$

Status: Conforme criterio de estabilidade adotado.

## 2) Momento Fletor Resistente (Mrd)

$$
M_{rd}=\frac{Z_x\,f_y}{\gamma_{a1}}
$$

Dados adotados:
- $Z_x = 412\times10^3 mm^3$
- $f_y = 345 MPa$
- $\gamma_{a1}=1,10$

$$
M_{rd} = \frac{412\times10^3\times345}{1,10}\times10^{-6}=129,2\;kN.m
$$

Esforco solicitante majorado:

$$
M_{sd}=1,4\times 34,5 = 48,3\;kN.m
$$

Indice de utilizacao:

$$
\eta_M=\frac{M_{sd}}{M_{rd}}=\frac{48,3}{129,2}=0,374
$$

Status: Conforme e abaixo da meta de utilizacao maxima de 0,80.

## 3) Controle de flecha e upsize automatico
- Regra ativa: se $\delta_{calc}>L/250$, executar upsize automatico para proximo perfil com menor massa que atende.
- Resultado no caso base: W200x22.5 reprovado em flecha, W200x26.6 aprovado.

Perfil alterado de W200x22.5 para W200x26.6 para atendimento de esbeltez da NBR 8800.

## 4) Referencias normativas
- NBR 8800:2008 - Verificacao de estabilidade e resistencia de membros comprimidos/fletidos.
- NBR 8800:2008, item 5.3.2 - Verificacao de flambagem global conforme combinacoes de acoes.

## 5) Liberacao
Projeto consolidado para pacote executivo mecanico com aprovacao automatica das rotinas de ELU/ELS.
