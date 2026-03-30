;;;; ═══════════════════════════════════════════════════════════════════════════
;;;; Engenharia CAD — Script Vigilante (Watcher)
;;;; Versão: 2.0
;;;; ═══════════════════════════════════════════════════════════════════════════
;;;;
;;;; PROPÓSITO:
;;;;   Roda continuamente dentro do AutoCAD no PC do cliente (PC B).
;;;;   Monitora uma pasta de rede (bridge folder) em busca de arquivos
;;;;   job_*.lsp gerados pelo servidor Engenharia CAD, executa-os e marca como
;;;;   processados (.done) para evitar duplicidade.
;;;;
;;;; COMANDOS DO AUTOCAD:
;;;;   FORGE_START  — Inicia o monitoramento da pasta.
;;;;   FORGE_STOP   — Para o monitoramento.
;;;;   FORGE_STATUS — Exibe o estado atual do vigilante.
;;;;   FORGE_PATH   — Altera a pasta monitorada em tempo de execução.
;;;;
;;;; INSTALAÇÃO:
;;;;   1. Copie este arquivo para uma pasta local no PC do cliente,
;;;;      por exemplo: C:\EngenhariaCAD\forge_vigilante.lsp
;;;;
;;;;   2. No AutoCAD, digite APPLOAD (ou menu Ferramentas > Carregar Aplicativo).
;;;;
;;;;   3. Navegue até o arquivo forge_vigilante.lsp e clique "Carregar".
;;;;      — Para carga automática em toda sessão, adicione-o à lista
;;;;        "Conteúdo de Inicialização" (botão no canto inferior do APPLOAD).
;;;;
;;;;   4. Digite FORGE_START na linha de comando do AutoCAD.
;;;;      O vigilante começará a monitorar a pasta configurada.
;;;;
;;;; CONFIGURAÇÃO:
;;;;   A pasta padrão é C:/AutoCAD_Drop/
;;;;   Para alterar, use o comando FORGE_PATH ou edite a variável abaixo.
;;;;
;;;; ═══════════════════════════════════════════════════════════════════════════


;;; ── Carregar extensões Visual LISP (necessário para vl-* funções) ──────
(vl-load-com)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; VARIÁVEIS GLOBAIS
;;; ═══════════════════════════════════════════════════════════════════════════

;; Pasta que o Vigilante monitora (usar barras normais /)
(if (not *forge-watch-path*)
  (setq *forge-watch-path* "C:/AutoCAD_Drop/")
)

;; Flag de controle: T = monitorando, nil = parado
(setq *forge-running* nil)

;; Intervalo de verificação em milissegundos (1500 = 1.5 segundos)
(setq *forge-interval* 1500)

;; Contadores de estatísticas
(if (not *forge-jobs-processed*)
  (setq *forge-jobs-processed* 0)
)
(if (not *forge-jobs-failed*)
  (setq *forge-jobs-failed* 0)
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; FUNÇÕES AUXILIARES
;;; ═══════════════════════════════════════════════════════════════════════════

(defun forge:log (msg / timestamp)
  "Imprime mensagem formatada no console do AutoCAD."
  (setq timestamp
    (menucmd (strcat "M=$(edtime,$(getvar,date),HH:MM:SS)"))
  )
  (princ (strcat "\n[Engenharia CAD " timestamp "] " msg))
  (princ)
)


(defun forge:ensure-trailing-slash (path)
  "Garante que o caminho termina com /."
  (if (and path (> (strlen path) 0))
    (if (not (member (substr path (strlen path) 1) '("/" "\\")))
      (strcat path "/")
      path
    )
    path
  )
)


(defun forge:file-exists-p (filepath)
  "Retorna T se o arquivo existe."
  (if (findfile filepath) T nil)
)


(defun forge:list-job-files (folder / pattern result file)
  "Lista todos os arquivos job_*.lsp na pasta especificada."
  (setq result '())
  (setq pattern (strcat folder "job_*.lsp"))
  (setq file (vl-directory-files folder "job_*.lsp" 1))
  (if file
    (foreach f file
      (setq result (cons (strcat folder f) result))
    )
  )
  ;; Retornar em ordem (mais antigo primeiro)
  (reverse result)
)


(defun forge:rename-to-done (filepath / newpath)
  "Renomeia arquivo .lsp para .done após processamento bem-sucedido."
  (setq newpath (strcat filepath ".done"))
  (if (vl-file-rename filepath newpath)
    (progn
      (forge:log (strcat "  Marcado como concluído: " (vl-filename-base filepath) ".done"))
      T
    )
    (progn
      ;; Se renomear falhar, tentar deletar
      (if (vl-file-delete filepath)
        (progn
          (forge:log (strcat "  Arquivo removido: " (vl-filename-base filepath)))
          T
        )
        (progn
          (forge:log (strcat "  AVISO: Não foi possível mover/deletar: " filepath))
          nil
        )
      )
    )
  )
)


(defun forge:execute-job (filepath / result err-obj err-msg basename)
  "Executa um arquivo .lsp com tratamento de erro robusto."
  (setq basename (vl-filename-base filepath))

  (forge:log (strcat "► Novo trabalho detectado: " basename ".lsp"))

  ;; Usar vl-catch-all-apply para capturar qualquer erro sem travar o AutoCAD
  (setq result
    (vl-catch-all-apply
      'load
      (list filepath)
    )
  )

  ;; Verificar se houve erro
  (if (vl-catch-all-error-p result)
    (progn
      (setq err-msg (vl-catch-all-error-message result))
      (forge:log (strcat "  ✗ ERRO ao executar " basename ": " err-msg))
      (setq *forge-jobs-failed* (1+ *forge-jobs-failed*))
      ;; Mesmo com erro, renomear para .done para não re-executar
      (forge:rename-to-done filepath)
      nil
    )
    (progn
      (forge:log (strcat "  ✓ Executado com sucesso: " basename))
      (setq *forge-jobs-processed* (1+ *forge-jobs-processed*))
      ;; Renomear para .done
      (forge:rename-to-done filepath)
      T
    )
  )
)


(defun forge:process-pending-jobs (/ jobs count)
  "Verifica pasta e processa todos os jobs pendentes."
  (setq jobs (forge:list-job-files *forge-watch-path*))

  (if jobs
    (progn
      (setq count (length jobs))
      (forge:log
        (strcat "Encontrado(s) " (itoa count) " trabalho(s) pendente(s)...")
      )
      (foreach job jobs
        (forge:execute-job job)
      )
      (forge:log
        (strcat "Ciclo concluído — Total processados: "
          (itoa *forge-jobs-processed*)
          " | Falhas: "
          (itoa *forge-jobs-failed*)
        )
      )
    )
  )
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; LOOP PRINCIPAL (via reactor de timer)
;;; ═══════════════════════════════════════════════════════════════════════════

(defun forge:timer-callback (reactor-obj args)
  "Callback do timer que verifica a pasta periodicamente."
  (if *forge-running*
    (progn
      ;; Verificar se a pasta existe antes de processar
      (if (vl-file-directory-p *forge-watch-path*)
        ;; Processar jobs com proteção contra erro total
        (vl-catch-all-apply 'forge:process-pending-jobs nil)
        ;; Pasta inacessível — avisar mas não parar
        ;; (avisa apenas a cada ~30 ciclos para não poluir o console)
        (if (= 0 (rem (getvar "MILLISECS") 45000))
          (forge:log
            (strcat "AVISO: Pasta inacessível: " *forge-watch-path*)
          )
        )
      )
    )
  )
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; COMANDOS DO AUTOCAD
;;; ═══════════════════════════════════════════════════════════════════════════

(defun c:FORGE_START (/ timer-name)
  "Inicia o monitoramento da pasta Engenharia CAD."
  (princ "\n")
  (princ "\n╔══════════════════════════════════════════════════════════╗")
  (princ "\n║          Engenharia CAD Vigilante — Iniciando...              ║")
  (princ "\n╚══════════════════════════════════════════════════════════╝")

  ;; Validar pasta
  (if (not *forge-watch-path*)
    (progn
      (princ "\n[Engenharia CAD] ERRO: Nenhuma pasta configurada.")
      (princ "\n[Engenharia CAD] Use FORGE_PATH para definir a pasta de monitoramento.")
      (princ)
      (exit)
    )
  )

  ;; Verificar se já está rodando
  (if *forge-running*
    (progn
      (forge:log "Vigilante já está ativo.")
      (princ)
      (exit)
    )
  )

  ;; Garantir trailing slash
  (setq *forge-watch-path* (forge:ensure-trailing-slash *forge-watch-path*))

  ;; Verificar acessibilidade da pasta
  (if (not (vl-file-directory-p *forge-watch-path*))
    (progn
      (forge:log
        (strcat "AVISO: Pasta não acessível agora: " *forge-watch-path*)
      )
      (forge:log "O monitoramento iniciará assim que a pasta ficar disponível.")
    )
    (forge:log (strcat "Pasta monitorada: " *forge-watch-path*))
  )

  ;; Ativar flag
  (setq *forge-running* T)

  ;; Registrar reactor de timer (a cada *forge-interval* milissegundos)
  ;; Remover timer anterior se existir
  (if *forge-timer*
    (progn
      (vl-catch-all-apply 'vlr-remove (list *forge-timer*))
      (setq *forge-timer* nil)
    )
  )

  ;; Usar VLR-Editor-Reactor com evento :vlr-commandEnded como fallback
  ;; já que AutoLISP não possui timer nativo verdadeiro.
  ;; A abordagem mais confiável é usar (command) em loop com delay.
  ;; Vamos usar a abordagem de idle callback:
  (forge:log "Vigilante ATIVO — monitorando em background.")
  (forge:log (strcat "Intervalo: " (rtos (/ *forge-interval* 1000.0) 2 1) "s"))
  (forge:log "Use FORGE_STOP para encerrar.")
  (princ)

  ;; Iniciar o loop de monitoramento no idle do AutoCAD
  (forge:start-idle-loop)
)


(defun c:FORGE_STOP ()
  "Para o monitoramento da pasta Engenharia CAD."
  (if (not *forge-running*)
    (progn
      (forge:log "Vigilante não está ativo.")
      (princ)
      (exit)
    )
  )

  ;; Desativar
  (setq *forge-running* nil)

  ;; Remover idle reactor
  (if *forge-idle-reactor*
    (progn
      (vl-catch-all-apply 'vlr-remove (list *forge-idle-reactor*))
      (setq *forge-idle-reactor* nil)
    )
  )

  (princ "\n")
  (princ "\n╔══════════════════════════════════════════════════════════╗")
  (princ "\n║          Engenharia CAD Vigilante — Encerrado                 ║")
  (princ "\n╚══════════════════════════════════════════════════════════╝")
  (forge:log
    (strcat "Sessão encerrada — Processados: "
      (itoa *forge-jobs-processed*)
      " | Falhas: "
      (itoa *forge-jobs-failed*)
    )
  )
  (princ)
)


(defun c:FORGE_STATUS ()
  "Exibe o estado atual do Vigilante Engenharia CAD."
  (princ "\n")
  (princ "\n┌──────────────────────────────────────────────────────────┐")
  (princ "\n│            Engenharia CAD Vigilante — Status                   │")
  (princ "\n├──────────────────────────────────────────────────────────┤")
  (princ (strcat "\n│  Estado:        "
    (if *forge-running* "● ATIVO" "○ INATIVO")
    (if *forge-running*
      "                                    │"
      "                                   │"
    )
  ))
  (princ (strcat "\n│  Pasta:         " *forge-watch-path*))
  (princ (strcat "\n│  Acessível:     "
    (if (vl-file-directory-p *forge-watch-path*) "Sim" "NÃO")
  ))
  (princ (strcat "\n│  Processados:   " (itoa *forge-jobs-processed*)))
  (princ (strcat "\n│  Falhas:        " (itoa *forge-jobs-failed*)))

  ;; Contar jobs pendentes
  (if (vl-file-directory-p *forge-watch-path*)
    (progn
      (setq pending (length (forge:list-job-files *forge-watch-path*)))
      (princ (strcat "\n│  Pendentes:     " (itoa pending)))
    )
  )

  (princ "\n└──────────────────────────────────────────────────────────┘")
  (princ)
)


(defun c:FORGE_PATH (/ newpath)
  "Altera a pasta monitorada pelo Vigilante."
  (setq newpath
    (getstring T
      (strcat "\nPasta atual: " *forge-watch-path*
              "\nNova pasta (Enter para manter): "
      )
    )
  )

  (if (and newpath (> (strlen newpath) 0))
    (progn
      ;; Normalizar barras
      (setq newpath (vl-string-translate "\\" "/" newpath))
      (setq newpath (forge:ensure-trailing-slash newpath))

      (if (vl-file-directory-p newpath)
        (progn
          (setq *forge-watch-path* newpath)
          (forge:log (strcat "Pasta alterada para: " newpath))
        )
        (progn
          (setq *forge-watch-path* newpath)
          (forge:log
            (strcat "Pasta definida: " newpath
                    " (AVISO: inacessível agora)"
            )
          )
        )
      )
    )
    (forge:log "Pasta mantida sem alteração.")
  )
  (princ)
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; MECANISMO DE TIMER — Idle Reactor
;;; ═══════════════════════════════════════════════════════════════════════════
;;; O AutoLISP não possui timer nativo. Usamos um VLR-Editor-Reactor no
;;; evento :vlr-sysVarChanged combinado com polling no idle do editor.
;;; A cada vez que o AutoCAD fica ocioso, verificamos se o intervalo passou.

(setq *forge-idle-reactor* nil)
(setq *forge-last-check* 0)


(defun forge:idle-check (reactor-obj args / now elapsed)
  "Chamado quando o AutoCAD fica ocioso — verifica se é hora de processar."
  (if *forge-running*
    (progn
      (setq now (getvar "MILLISECS"))
      ;; Lidar com wrap-around do MILLISECS (reseta após ~24 dias)
      (if (< now *forge-last-check*)
        (setq *forge-last-check* 0)
      )
      (setq elapsed (- now *forge-last-check*))

      (if (>= elapsed *forge-interval*)
        (progn
          (setq *forge-last-check* now)
          ;; Processar com proteção total
          (vl-catch-all-apply 'forge:process-pending-jobs nil)
          ;; Verificar auto-update periodicamente
          (setq *forge-update-check-counter*
                (1+ (if *forge-update-check-counter* *forge-update-check-counter* 0)))
          (if (>= *forge-update-check-counter* *forge-update-check-interval*)
            (progn
              (setq *forge-update-check-counter* 0)
              (vl-catch-all-apply 'forge:check-self-update nil)
            )
          )
        )
      )
    )
  )
)


(defun forge:start-idle-loop ()
  "Registra o reactor de idle para monitoramento contínuo."
  ;; Remover anterior se existir
  (if *forge-idle-reactor*
    (vl-catch-all-apply 'vlr-remove (list *forge-idle-reactor*))
  )

  ;; Registrar no evento de idle do editor
  ;; :vlr-beginClose é seguro; usamos :vlr-commandEnded como trigger principal
  (setq *forge-idle-reactor*
    (vlr-editor-reactor
      nil
      '(
        (:vlr-commandWillStart . forge:idle-check)
        (:vlr-commandEnded     . forge:idle-check)
        (:vlr-commandCancelled . forge:idle-check)
        (:vlr-lispWillStart    . forge:idle-check)
        (:vlr-lispEnded        . forge:idle-check)
      )
    )
  )

  ;; Resetar timestamp
  (setq *forge-last-check* (getvar "MILLISECS"))

  ;; Processar imediatamente ao iniciar (caso haja jobs pendentes)
  (forge:process-pending-jobs)
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; AUTO-UPDATE — Verifica e aplica atualizações automaticamente
;;; ═══════════════════════════════════════════════════════════════════════════

(setq *forge-current-version* "2.0")
(setq *forge-update-check-counter* 0)
(setq *forge-update-check-interval* 20)  ;; A cada 20 ciclos de idle (~30s)

(defun forge:check-self-update ( / update-file version-line new-version)
  "Verifica se existe forge_vigilante_update.lsp na pasta monitorada.
   Se existir e tiver versão superior, recarrega automaticamente."
  (setq update-file (strcat *forge-watch-path* "forge_vigilante_update.lsp"))
  (if (findfile update-file)
    (progn
      ;; Ler primeira linha para extrair versão (formato: ;;;; Versão: X.Y)
      (setq new-version (forge:extract-update-version update-file))
      (if (and new-version
               (> (atof new-version) (atof *forge-current-version*)))
        (progn
          (princ (strcat "\n[FORGE-UPDATE] Nova versão detectada: v"
                         new-version " (atual: v" *forge-current-version* ")"))
          (princ "\n[FORGE-UPDATE] Aplicando atualização...")
          ;; Parar o monitoramento atual antes de recarregar
          (if *forge-running*
            (progn
              (setq *forge-running* nil)
              (if *forge-idle-reactor*
                (vl-catch-all-apply 'vlr-remove (list *forge-idle-reactor*))
              )
            )
          )
          ;; Carregar o novo script (substitui todas as funções em memória)
          (vl-catch-all-apply 'load (list update-file))
          ;; Renomear para .applied para não reprocessar
          (vl-catch-all-apply
            'vl-file-rename
            (list update-file
                  (strcat *forge-watch-path* "forge_vigilante_update.applied"))
          )
          (princ "\n[FORGE-UPDATE] Atualização aplicada com sucesso!")
          T
        )
        (progn nil)  ;; Versão igual ou inferior — ignorar
      )
    )
    nil  ;; Arquivo de atualização não encontrado
  )
)

(defun forge:extract-update-version (filepath / fp line version)
  "Extrai a versão de um arquivo .lsp procurando a linha ;;;; Versão: X.Y"
  (setq version nil)
  (setq fp (open filepath "r"))
  (if fp
    (progn
      ;; Ler até 10 primeiras linhas procurando a versão
      (repeat 10
        (setq line (read-line fp))
        (if (and line (not version))
          (if (vl-string-search ";;; Vers" line)
            (progn
              ;; Extrair tudo após o último ":"
              (setq version (vl-string-trim " \t"
                (substr line (+ 2 (vl-string-search ":" line)))))
            )
          )
        )
      )
      (close fp)
    )
  )
  version
)


;;; ═══════════════════════════════════════════════════════════════════════════
;;; AUTO-INICIALIZAÇÃO
;;; ═══════════════════════════════════════════════════════════════════════════

;; Verificar se há atualização disponível ao carregar
(forge:check-self-update)

(princ "\n")
(princ "\n╔══════════════════════════════════════════════════════════╗")
(princ "\n║   Engenharia CAD Vigilante v2.0 — Carregado com Sucesso      ║")
(princ "\n╠══════════════════════════════════════════════════════════╣")
(princ "\n║                                                         ║")
(princ "\n║  Comandos disponíveis:                                  ║")
(princ "\n║    FORGE_START  — Iniciar monitoramento                 ║")
(princ "\n║    FORGE_STOP   — Parar monitoramento                   ║")
(princ "\n║    FORGE_STATUS — Ver estado atual                      ║")
(princ "\n║    FORGE_PATH   — Alterar pasta monitorada              ║")
(princ "\n║                                                         ║")
(princ "\n║  [AUTO-UPDATE] Verificação automática ativada           ║")
(princ "\n║                                                         ║")
(princ (strcat
  "\n║  Pasta configurada: "
  (if (> (strlen *forge-watch-path*) 35)
    (strcat (substr *forge-watch-path* 1 32) "...")
    *forge-watch-path*
  )
))
(princ "\n║                                                         ║")
(princ "\n║  Digite FORGE_START para começar.                       ║")
(princ "\n║                                                         ║")
(princ "\n╚══════════════════════════════════════════════════════════╝")
(princ)
