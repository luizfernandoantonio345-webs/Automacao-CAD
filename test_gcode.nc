(===================================================)
(  ENGENHARIA CAD - CORTE PLASMA CNC)
(===================================================)
(  Gerado em: 2026-04-02 13:16:43)
(  Material: mild_steel)
(  Espessura: 6.0mm)
(  Amperagem: 45A)
(  Velocidade: 2000.0mm/min)
(  Kerf: 1.5mm)
(===================================================)
(  Cortes: 1)
(  Comprimento de corte: 398.6mm)
(  Deslocamento rapido: 96.3mm)
(  Tempo estimado: 0.2 min)
(===================================================)

G21 (Unidades: milimetros)
G90 (Coordenadas absolutas)
G17 (Plano XY)
G54 (Sistema de coordenadas da peÃ§a)
M05 (Plasma desligado)
M67 (THC desligado)
G00 Z10.000 (Altura segura)

(=== CORTE 1/1 - EXTERNO ===)
G00 X96.250 Y0.750 (Movimento rapido)
G02 X99.250 Y0.750 I3.000 J0.000 F2000 (Lead-in arco)
G00 Z3.000 (Altura de pierce)
M03 (Plasma ON)
G04 P500 (Pierce delay: 0.5s)
M65 (THC ON)
G01 Z1.500 F500 (Altura de corte)
G01 X99.250 Y99.250 F2000
G01 X0.000 Y100.000 F2000
G01 X0.000 Y100.000 F2000
G01 X0.750 Y0.750 F2000
G01 X99.250 Y0.750 F2000
M05 (Plasma OFF)
M67 (THC OFF)
G00 Z10.000

(=== FIM DO PROGRAMA ===)
M05 (Plasma OFF)
M67 (THC OFF)
G00 Z10.000 (Altura segura)
G00 X0 Y0 (Retorno ao zero)
M02 (Fim do programa)
%
