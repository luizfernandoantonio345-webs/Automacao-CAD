;;; ═══════════════════════════════════════════════════════════════════════════
;;; ENGENHARIA CAD - FORGE VIGILANTE v2.0
;;; Sistema de automação CAD via comandos web
;;; 
;;; Instruções:
;;; 1. Carregue este arquivo: APPLOAD -> selecione este arquivo
;;; 2. Digite FORGE_START para ativar o monitor
;;; 3. Use o sistema web para enviar comandos
;;; ═══════════════════════════════════════════════════════════════════════════

(vl-load-com)

;;; Variáveis globais
(setq *forge-running* nil)
(setq *forge-drop-path* "C:\\AutoCAD_Drop\\")
(setq *forge-log* '())

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Funções de log
;;; ─────────────────────────────────────────────────────────────────────────────

(defun forge-log (msg)
  (princ (strcat "\n[FORGE " (forge-timestamp) "] " msg))
  (setq *forge-log* (cons (cons (forge-timestamp) msg) *forge-log*))
  (princ)
)

(defun forge-timestamp ()
  (setq ct (getvar "CDATE"))
  (setq hr (fix (/ (- ct (fix ct)) 0.01)))
  (setq mn (fix (/ (- (* (- ct (fix ct)) 100) hr) 0.01)))
  (strcat (itoa hr) ":" (if (< mn 10) "0" "") (itoa mn))
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Comando principal: FORGE_START
;;; ─────────────────────────────────────────────────────────────────────────────

(defun C:FORGE_START ( / )
  (princ "\n")
  (princ "\n╔═══════════════════════════════════════════════════════════════════╗")
  (princ "\n║                                                                   ║")
  (princ "\n║        ENGENHARIA CAD - FORGE VIGILANTE v2.0                     ║")
  (princ "\n║                                                                   ║")
  (princ "\n╠═══════════════════════════════════════════════════════════════════╣")
  (princ "\n║   STATUS: ATIVO                                                  ║")
  (princ (strcat "\n║   PASTA:  " *forge-drop-path* "                                   ║"))
  (princ "\n║                                                                   ║")
  (princ "\n║   Aguardando comandos do sistema web...                          ║")
  (princ "\n║   Digite FORGE_STOP para desativar                               ║")
  (princ "\n╚═══════════════════════════════════════════════════════════════════╝")
  (princ "\n")
  
  ;; Criar pasta se não existir
  (if (not (vl-file-directory-p *forge-drop-path*))
    (progn
      (vl-mkdir *forge-drop-path*)
      (forge-log "Pasta de comandos criada")
    )
  )
  
  (setq *forge-running* T)
  (forge-log "Monitor ATIVADO - Pronto para receber comandos!")
  
  ;; Iniciar loop de monitoramento
  (forge-monitor-loop)
  
  (princ)
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Comando: FORGE_STOP
;;; ─────────────────────────────────────────────────────────────────────────────

(defun C:FORGE_STOP ()
  (setq *forge-running* nil)
  (princ "\n")
  (princ "\n╔═══════════════════════════════════════════════════════════════════╗")
  (princ "\n║   FORGE VIGILANTE - DESATIVADO                                   ║")
  (princ "\n╚═══════════════════════════════════════════════════════════════════╝")
  (princ "\n")
  (princ)
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Loop de monitoramento
;;; ─────────────────────────────────────────────────────────────────────────────

(defun forge-monitor-loop ()
  (while *forge-running*
    (forge-check-and-execute)
    ;; Pequena pausa para não sobrecarregar
    (command "_.DELAY" 500)
  )
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Verificar e executar comandos
;;; ─────────────────────────────────────────────────────────────────────────────

(defun forge-check-and-execute ( / files f fpath)
  (setq files (vl-directory-files *forge-drop-path* "*.lsp" 1))
  
  (foreach f files
    (setq fpath (strcat *forge-drop-path* f))
    
    ;; Log do comando
    (princ (strcat "\n\n▶▶▶ COMANDO RECEBIDO: " f))
    (forge-log (strcat "Executando: " f))
    
    ;; Executar o arquivo LISP
    (if (vl-catch-all-error-p
          (vl-catch-all-apply 'load (list fpath)))
      (progn
        (forge-log (strcat "ERRO ao executar: " f))
        (princ "\n*** ERRO na execução do comando! ***")
      )
      (progn
        (forge-log (strcat "OK: " f))
        (princ "\n✓ Comando executado com sucesso!")
      )
    )
    
    ;; Deletar arquivo após execução
    (vl-file-delete fpath)
  )
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Comando: FORGE_STATUS
;;; ─────────────────────────────────────────────────────────────────────────────

(defun C:FORGE_STATUS ()
  (princ "\n")
  (princ "\n╔═══════════════════════════════════════════════════════════════════╗")
  (princ "\n║   FORGE VIGILANTE - STATUS                                       ║")
  (princ "\n╠═══════════════════════════════════════════════════════════════════╣")
  (princ (strcat "\n║   Monitor: " (if *forge-running* "ATIVO" "INATIVO") "                                              ║"))
  (princ (strcat "\n║   Pasta: " *forge-drop-path* "                                    ║"))
  (princ (strcat "\n║   Comandos no log: " (itoa (length *forge-log*)) "                                          ║"))
  (princ "\n╚═══════════════════════════════════════════════════════════════════╝")
  (princ "\n")
  (princ)
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Comando: FORGE_TEST - Teste rápido
;;; ─────────────────────────────────────────────────────────────────────────────

(defun C:FORGE_TEST ()
  (princ "\n[FORGE] Executando teste...")
  
  ;; Desenhar um retângulo de teste
  (command "._RECTANG" "0,0" "1000,500")
  (command "._CIRCLE" "500,250" "100")
  (command "._ZOOM" "E")
  
  (princ "\n")
  (princ "\n╔═══════════════════════════════════════════════════════════════════╗")
  (princ "\n║   TESTE CONCLUÍDO!                                               ║")
  (princ "\n║   Desenhado: Retângulo 1000x500 + Círculo R100                   ║")
  (princ "\n╚═══════════════════════════════════════════════════════════════════╝")
  (princ "\n")
  (princ)
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Comando: FORGE_LOG - Ver histórico
;;; ─────────────────────────────────────────────────────────────────────────────

(defun C:FORGE_LOG ()
  (princ "\n")
  (princ "\n═══════════════════════════════════════════════════════════════════")
  (princ "\n   HISTÓRICO DE COMANDOS")
  (princ "\n═══════════════════════════════════════════════════════════════════")
  
  (if (null *forge-log*)
    (princ "\n   (nenhum comando executado)")
    (foreach item (reverse *forge-log*)
      (princ (strcat "\n   [" (car item) "] " (cdr item)))
    )
  )
  
  (princ "\n═══════════════════════════════════════════════════════════════════")
  (princ "\n")
  (princ)
)

;;; ─────────────────────────────────────────────────────────────────────────────
;;; Mensagem de carregamento
;;; ─────────────────────────────────────────────────────────────────────────────

(princ "\n")
(princ "\n╔═══════════════════════════════════════════════════════════════════╗")
(princ "\n║   FORGE VIGILANTE v2.0 - Carregado com sucesso!                  ║")
(princ "\n╠═══════════════════════════════════════════════════════════════════╣")
(princ "\n║   Comandos disponíveis:                                          ║")
(princ "\n║                                                                   ║")
(princ "\n║   FORGE_START  - Ativa o monitor de comandos                     ║")
(princ "\n║   FORGE_STOP   - Desativa o monitor                              ║")
(princ "\n║   FORGE_STATUS - Mostra status atual                             ║")
(princ "\n║   FORGE_TEST   - Executa desenho de teste                        ║")
(princ "\n║   FORGE_LOG    - Mostra histórico de comandos                    ║")
(princ "\n╚═══════════════════════════════════════════════════════════════════╝")
(princ "\n")
(princ "\n>>> Digite FORGE_START para ativar o sistema <<<")
(princ "\n")
(princ)
