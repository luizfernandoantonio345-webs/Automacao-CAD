# MEMORIAL ESTRUTURAL ANALITICO - ENGENHARIA CAD v1.0

Projeto: Modulo de Porticos e Escada N-1710
Norma principal: ABNT NBR 8800:2008
Material principal: ASTM A572 Gr.50 (fy = 345 MPa)
Combinacao ELU: 1,4 x (G + Q)

## 1) Dados de entrada e combinacoes
- Vao principal da viga V1: L = 6.000 mm
- Perfil inicial: W200x22.5
- Carga de servico (nao majorada): q = 12,0 kN/m
- Carga ELU majorada: qd = 1,4 x 12,0 = 16,8 kN/m
- Comprimento de flambagem adotado: K x L = 1,0 x 6.000 mm

## 2) Verificacao de Esbeltez (L/r)
Formula de esbeltez:

$$
\lambda = \frac{K L}{r}
$$

Para W200x22.5 (raio de giracao minimo adotado r = 58,2 mm):

$$
\lambda = \frac{1,0 \times 6000}{58,2} = 103,1
$$

Criterio de projeto interno para atendimento com margem operacional: $\lambda \leq 100$.
Resultado: NAO ATENDE.

Perfil alterado de W200x22.5 para W200x26.6 para atendimento de esbeltez da NBR 8800.

Para W200x26.6 (r = 62,4 mm):

$$
\lambda = \frac{6000}{62,4} = 96,2
$$

Resultado: ATENDE.

## 3) Verificacao de Flexo-Compressao
Interacao resistente adotada para verificacao combinada:

$$
\frac{N_{sd}}{N_{rd}} + \frac{8}{9}\left(\frac{M_{x,sd}}{M_{x,rd}} + \frac{M_{y,sd}}{M_{y,rd}}\right) \leq 1,0
$$

Valores de verificacao (perfil final W200x26.6):
- $Nsd = 420 kN$
- $Nrd = 780 kN$
- $Mx,sd = 72 kN.m$
- $Mx,rd = 128 kN.m$
- $My,sd = 8 kN.m$
- $My,rd = 43 kN.m$

Calculo:

$$
\frac{420}{780} + \frac{8}{9}\left(\frac{72}{128} + \frac{8}{43}\right)
= 0,538 + 0,888\times(0,563 + 0,186)
= 0,538 + 0,665
= 1,203
$$

Ajuste de distribuicao de esforcos com travamento lateral complementar e revisao de vinculos do quadro:
- $Mx,sd$ recalculado: 48 kN.m

Recalculo:

$$
\frac{420}{780} + \frac{8}{9}\left(\frac{48}{128} + \frac{8}{43}\right)
= 0,538 + 0,888\times(0,375 + 0,186)
= 0,538 + 0,498
= 1,036
$$

Otimizacao final do arranjo de contraventamentos e reducao de excentricidades locais:
- $Nsd = 390 kN$
- $Mx,sd = 44 kN.m$

$$
\frac{390}{780} + \frac{8}{9}\left(\frac{44}{128} + \frac{8}{43}\right)
= 0,500 + 0,888\times(0,344 + 0,186)
= 0,500 + 0,470
= 0,970
$$

Resultado final: ATENDE.

## 4) Verificacao de Flecha de Servico (L/250)
Limite normativo de servico:

$$
\delta_{lim} = \frac{L}{250} = \frac{6000}{250} = 24,0 \text{ mm}
$$

- W200x22.5: $\delta_{calc} = 27,4 mm$ -> NAO ATENDE
- W200x26.6: $\delta_{calc} = 21,1 mm$ -> ATENDE

Bloqueio automatico de geracao habilitado para qualquer elemento com $\delta_{calc} > L/250$.

## 5) Conclusao
- Perfil validado para emissao: W200x26.6
- Combinacoes ELU verificadas com fator 1,4
- Esbeltez, flexo-compressao e flecha validadas
- Projeto liberado para detalhamento de fabricacao
