SELO DE CONFORMIDADE: REGAP-CONFORME | UNIDADE: REGAP BETIM/MG

# Memorial Tecnico Executivo - Pacote Executivo

- Data UTC: 2026-03-25T16:57:27.945506+00:00
- Local: REGAP - Betim/MG
- Modo de calculo critico: 100% local
- Normas: NBR 8800, NR-12, N-1710, N-1810, N-13

## 1. Estrutura
- Quantidade de porticos: 10
- Flecha maxima adotada: 81.865 mm
- Limite normativo: 100.0 mm (L/250)
- Vento adotado: 38.0 m/s em Betim/MG

## 2. Interferencias
- Conflitos iniciais detectados: 5
- Conflitos resolvidos apos deslocamento: 0
- Escada deslocada: True
- Tubulacao deslocada: True

## 3. Verificacao de Estabilidade

Formulas aplicadas (NBR 8800 - ELU):
- Esbeltez: L/r = (K*L)/r
- Flambagem: Fe = pi^2*E/(KL/r)^2 e Fcr conforme regime de flambagem
- Momento resistente: Md = phi_b*fy*Zx
- Taxa de utilizacao: eta = max(Nsd/Pn, Msd/Md, Nsd/Pn + Msd/Md)

### 3.1 Resultado por Viga
| Viga | Perfil | L/r | K | Md (kN.m) | Eta | Resultado |
|---|---|---:|---:|---:|---:|---|
| P-001-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-002-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-003-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-004-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-005-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-006-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-007-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-008-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-009-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |
| P-010-VIGA | W410x60 | 31.873 | 1.000 | 763.830 | 0.2243 | PASS |

### 3.2 Resultado por Chumbador
| Base | Grupo de chumbadores | Nt,sd (kN) | Nt,Rd (kN) | Eta | Resultado |
|---|---|---:|---:|---:|---|
| P-001 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-002 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-003 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-004 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-005 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-006 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-007 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-008 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-009 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |
| P-010 | 8x D30 | 132.020 | 132.536 | 0.9961 | PASS |

## 4. Civil
- Reacoes de apoio exportadas para dimensionamento de placa de base e chumbadores.
- Chumbadores validados por razao solicitacao/resistencia em ELU.

## 5. Fabricacao
- Massa total inventariada: 26875.1 kg
- Custo total estimado: R$ 314543.0
- Plano de corte alvo < 3%: True

## 6. Pintura e Preparacao de Superficie
- Esquema Petrobras N-13: Pintura de manutencao.
- Preparacao de superficie: jateamento ao metal quase branco Sa 2 1/2.

## 7. Observacoes
- Projeto executivo emitido com layers Petrobras, vistas, cortes, notas tecnicas e XData de rastreabilidade.
- Consumivel de solda especificado como E7018 com garganta definida por espessura de chapa.
