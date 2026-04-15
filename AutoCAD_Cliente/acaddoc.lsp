;;;; ═══════════════════════════════════════════════════════════════════════════
;;;; Engenharia CAD — Auto-Load Script (acaddoc.lsp)
;;;; Versão: 1.0
;;;; ═══════════════════════════════════════════════════════════════════════════
;;;;
;;;; PROPÓSITO:
;;;;   Este arquivo é carregado automaticamente pelo AutoCAD ao abrir cada
;;;;   documento. Ele carrega o forge_vigilante.lsp e inicia o monitoramento.
;;;;
;;;; INSTALAÇÃO AUTOMÁTICA:
;;;;   O instalador copia este arquivo para:
;;;;   %APPDATA%\Autodesk\AutoCAD <versão>\<idioma>\Support\acaddoc.lsp
;;;;
;;;; ═══════════════════════════════════════════════════════════════════════════

(vl-load-com)

;;; Caminho onde o Engenharia CAD foi instalado
(setq *engcad-install-path* "C:/EngenhariaCAD/")

;;; Carregar forge_vigilante.lsp se existir
(defun engcad:auto-load (/ vigilante-path)
  (setq vigilante-path (strcat *engcad-install-path* "forge_vigilante.lsp"))
  
  ;; Verificar se o arquivo existe
  (if (findfile vigilante-path)
    (progn
      ;; Carregar o vigilante
      (if (vl-catch-all-error-p
            (vl-catch-all-apply 'load (list vigilante-path)))
        (princ "\n[Engenharia CAD] Erro ao carregar forge_vigilante.lsp")
        (progn
          (princ "\n")
          (princ "╔═══════════════════════════════════════════════════════════════╗\n")
          (princ "║           ENGENHARIA CAD - FORGE VIGILANTE v2.0               ║\n")
          (princ "╠═══════════════════════════════════════════════════════════════╣\n")
          (princ "║  Sistema carregado com sucesso!                               ║\n")
          (princ "║                                                               ║\n")
          (princ "║  Comandos disponíveis:                                        ║\n")
          (princ "║    FORGE_START  - Iniciar monitoramento                       ║\n")
          (princ "║    FORGE_STOP   - Parar monitoramento                         ║\n")
          (princ "║    FORGE_STATUS - Ver status atual                            ║\n")
          (princ "║                                                               ║\n")
          (princ "║  Iniciando automaticamente em 3 segundos...                   ║\n")
          (princ "╚═══════════════════════════════════════════════════════════════╝\n")
          
          ;; Agendar início automático do vigilante
          (vl-cmdf "_.DELAY" "3000")
          
          ;; Iniciar o vigilante automaticamente
          (if (and (not *forge-running*) (fboundp 'c:FORGE_START))
            (progn
              (c:FORGE_START)
              (princ "\n[Engenharia CAD] Vigilante iniciado automaticamente!\n")
            )
          )
        )
      )
    )
    ;; Arquivo não encontrado - avisar mas não travar
    (progn
      (princ "\n[Engenharia CAD] forge_vigilante.lsp não encontrado em: ")
      (princ vigilante-path)
      (princ "\n[Engenharia CAD] Execute o instalador novamente ou use APPLOAD.\n")
    )
  )
  (princ)
)

;;; Executar auto-load ao carregar este arquivo
(engcad:auto-load)

;;; Limpar
(princ)
