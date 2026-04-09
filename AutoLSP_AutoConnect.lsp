;;;; ═══════════════════════════════════════════════════════════════════════════
;;;; Engenharia CAD — AutoConnect LSP (v2.0)
;;;; Conexão Automática Pós-Licença
;;;; ═══════════════════════════════════════════════════════════════════════════
;;;;
;;;; PROPÓSITO:
;;;;   Este script é carregado automaticamente após validação da licença.
;;;;   Configura o ambiente AutoCAD para receber comandos do backend.
;;;;
;;;; COMANDOS:
;;;;   AUTOCONNECT  — Inicia conexão com backend
;;;;   FORGE_STATUS — Exibe status da conexão
;;;;   FORGE_TEST   — Testa desenho via backend
;;;;
;;;; ═══════════════════════════════════════════════════════════════════════════

(vl-load-com)

;;; ═══════════════════════════════════════════════════════════════════════════
;;; VARIÁVEIS GLOBAIS
;;; ═══════════════════════════════════════════════════════════════════════════

;; URL do backend (configurável)
(if (not *backend-url*)
  (setq *backend-url* "http://localhost:8000")
)

;; Pasta de monitoramento bridge
(if (not *forge-watch-path*)
  (setq *forge-watch-path* "C:/AutoCAD_Drop/")
)

;; Status de conexão
(setq *forge-connected* nil)
(setq *forge-running* nil)

;; Intervalo de verificação (ms)
(setq *forge-interval* 2000)

;; Contadores
(if (not *forge-jobs-processed*)
  (setq *forge-jobs-processed* 0)
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; FUNÇÕES AUXILIARES
;;; ═══════════════════════════════════════════════════════════════════════════

(defun forge:log (msg / timestamp)
  "Imprime mensagem formatada no console."
  (setq timestamp
    (if (getvar "DATE")
      (menucmd (strcat "M=$(edtime,$(getvar,date),HH:MM:SS)"))
      "00:00:00"
    )
  )
  (princ (strcat "\n[Engenharia CAD " timestamp "] " msg))
  (princ)
)


(defun forge:ensure-path (path)
  "Garante que o caminho termina com / e cria se não existir."
  (if (and path (> (strlen path) 0))
    (progn
      ;; Normalizar separadores
      (setq path (vl-string-translate "\\" "/" path))
      ;; Garantir trailing slash
      (if (not (= (substr path (strlen path) 1) "/"))
        (setq path (strcat path "/"))
      )
      ;; Criar diretório se não existir
      (if (not (vl-file-directory-p path))
        (vl-mkdir path)
      )
      path
    )
    "C:/AutoCAD_Drop/"
  )
)


(defun forge:list-jobs (folder / files result)
  "Lista arquivos job_*.lsp na pasta."
  (setq files (vl-directory-files folder "job_*.lsp" 1))
  (if files
    (mapcar '(lambda (f) (strcat folder f)) files)
    nil
  )
)


(defun forge:execute-job (filepath / result basename)
  "Executa um arquivo job LSP com tratamento de erro."
  (setq basename (vl-filename-base filepath))
  (forge:log (strcat "Executando: " basename ".lsp"))
  
  (setq result
    (vl-catch-all-apply 'load (list filepath))
  )
  
  (if (vl-catch-all-error-p result)
    (progn
      (forge:log (strcat "ERRO: " (vl-catch-all-error-message result)))
      nil
    )
    (progn
      (forge:log (strcat "OK: " basename))
      (setq *forge-jobs-processed* (1+ *forge-jobs-processed*))
      ;; Renomear para .done
      (vl-file-rename filepath (strcat filepath ".done"))
      T
    )
  )
)


(defun forge:process-jobs (/ jobs)
  "Processa todos os jobs pendentes na pasta bridge."
  (setq jobs (forge:list-jobs *forge-watch-path*))
  (if jobs
    (progn
      (forge:log (strcat "Jobs encontrados: " (itoa (length jobs))))
      (foreach job jobs
        (forge:execute-job job)
      )
    )
  )
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; MONITORAMENTO (usando idle callback)
;;; ═══════════════════════════════════════════════════════════════════════════

(defun forge:idle-check (/ last-check)
  "Callback de verificação no idle do AutoCAD."
  (if *forge-running*
    (progn
      ;; Verificar a cada N segundos (baseado em MILLISECS)
      (if (or (not *forge-last-check*)
              (> (- (getvar "MILLISECS") *forge-last-check*) *forge-interval*))
        (progn
          (setq *forge-last-check* (getvar "MILLISECS"))
          (if (vl-file-directory-p *forge-watch-path*)
            (forge:process-jobs)
          )
        )
      )
    )
  )
)


(defun forge:start-monitoring ()
  "Inicia o monitoramento em background."
  (if (not *forge-running*)
    (progn
      (setq *forge-running* T)
      (setq *forge-last-check* 0)
      ;; Registrar callback de idle
      (if (not *forge-idle-reactor*)
        (setq *forge-idle-reactor*
          (vlr-editor-reactor nil '((:vlr-commandEnded . forge:on-command-end)))
        )
      )
      (forge:log "Monitoramento ATIVO")
      T
    )
    (progn
      (forge:log "Monitoramento já estava ativo")
      nil
    )
  )
)


(defun forge:on-command-end (reactor args)
  "Callback executado após cada comando - verifica jobs."
  (if *forge-running*
    (forge:idle-check)
  )
)


(defun forge:stop-monitoring ()
  "Para o monitoramento."
  (if *forge-running*
    (progn
      (setq *forge-running* nil)
      (if *forge-idle-reactor*
        (progn
          (vlr-remove *forge-idle-reactor*)
          (setq *forge-idle-reactor* nil)
        )
      )
      (forge:log "Monitoramento PARADO")
      T
    )
    nil
  )
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; COMANDOS DO AUTOCAD
;;; ═══════════════════════════════════════════════════════════════════════════

(defun C:AUTOCONNECT (/ )
  "Inicia conexão automática com o backend Engenharia CAD."
  (princ "\n")
  (princ "\n╔══════════════════════════════════════════════════════════╗")
  (princ "\n║       ENGENHARIA CAD — AutoConnect v2.0                  ║")
  (princ "\n╚══════════════════════════════════════════════════════════╝")
  (princ "\n")
  
  ;; 1. Configurar pasta bridge
  (setq *forge-watch-path* (forge:ensure-path *forge-watch-path*))
  (forge:log (strcat "Pasta bridge: " *forge-watch-path*))
  
  ;; 2. Verificar/criar pasta
  (if (not (vl-file-directory-p *forge-watch-path*))
    (progn
      (vl-mkdir *forge-watch-path*)
      (forge:log "Pasta criada com sucesso")
    )
  )
  
  ;; 3. Iniciar monitoramento
  (forge:start-monitoring)
  
  ;; 4. Marcar como conectado
  (setq *forge-connected* T)
  
  ;; 5. Exibir confirmação
  (princ "\n")
  (princ "\n  ✅ CONECTADO AO BACKEND!")
  (princ (strcat "\n  📁 Pasta: " *forge-watch-path*))
  (princ (strcat "\n  🌐 Backend: " *backend-url*))
  (princ "\n")
  (princ "\n  Comandos disponíveis:")
  (princ "\n    FORGE_STATUS  — Ver status da conexão")
  (princ "\n    FORGE_TEST    — Testar desenho")
  (princ "\n    FORGE_STOP    — Parar monitoramento")
  (princ "\n")
  
  ;; Alerta visual
  (alert (strcat "Engenharia CAD Conectado!\n\n"
                 "Pasta: " *forge-watch-path* "\n"
                 "Backend: " *backend-url*))
  (princ)
)


(defun C:FORGE_STATUS ()
  "Exibe status atual da conexão."
  (princ "\n")
  (princ "\n╔══════════════════════════════════════════════════════════╗")
  (princ "\n║            ENGENHARIA CAD — Status                       ║")
  (princ "\n╚══════════════════════════════════════════════════════════╝")
  (princ "\n")
  (princ (strcat "\n  Conectado:    " (if *forge-connected* "SIM ✅" "NÃO ❌")))
  (princ (strcat "\n  Monitorando:  " (if *forge-running* "ATIVO 🟢" "PARADO 🔴")))
  (princ (strcat "\n  Pasta:        " (if *forge-watch-path* *forge-watch-path* "N/A")))
  (princ (strcat "\n  Backend:      " (if *backend-url* *backend-url* "N/A")))
  (princ (strcat "\n  Jobs OK:      " (itoa *forge-jobs-processed*)))
  (princ "\n")
  (princ)
)


(defun C:FORGE_TEST ()
  "Cria um desenho de teste para verificar conexão."
  (princ "\n[Engenharia CAD] Criando desenho de teste...")
  
  ;; Desenhar círculo
  (command "_CIRCLE" "0,0" "100")
  
  ;; Desenhar linha
  (command "_LINE" "0,0" "500,0" "")
  
  ;; Zoom extents
  (command "_ZOOM" "E")
  
  (forge:log "Desenho de teste criado!")
  (princ)
)


(defun C:FORGE_STOP ()
  "Para o monitoramento."
  (forge:stop-monitoring)
  (setq *forge-connected* nil)
  (princ "\n[Engenharia CAD] Desconectado.\n")
  (princ)
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; INICIALIZAÇÃO
;;; ═══════════════════════════════════════════════════════════════════════════

(princ "\n")
(princ "\n════════════════════════════════════════════════════════════")
(princ "\n  Engenharia CAD — AutoConnect LSP v2.0 Carregado")
(princ "\n  Digite AUTOCONNECT para iniciar a conexão")
(princ "\n════════════════════════════════════════════════════════════")
(princ "\n")
(princ)
