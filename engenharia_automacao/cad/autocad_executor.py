from __future__ import annotations

import logging
import time
from pathlib import Path


def executar_no_autocad(caminho_lsp: str):
    """Carrega e executa LISP no AutoCAD via COM (win32com)."""
    caminho = Path(caminho_lsp)
    if not caminho.exists():
        logging.error("Arquivo LISP nao encontrado: %s", caminho)
        return

    try:
        import win32com.client
    except ImportError:
        logging.error("win32com nao esta instalado; execucao automatica no AutoCAD esta indisponivel.")
        return

    try:
        logging.info("Conectando ao AutoCAD (COM)...")
        acad = win32com.client.Dispatch("AutoCAD.Application")
        acad.Visible = True
        doc = acad.ActiveDocument

        arquivo_lisp = str(caminho).replace("\\", "/")
        logging.info("Carregando LISP: %s", arquivo_lisp)
        doc.SendCommand(f'(load "{arquivo_lisp}")\n')
        time.sleep(1.0)

        logging.info("Executando comando DrawGeneratedPipe")
        doc.SendCommand("DrawGeneratedPipe\n")
        time.sleep(1.0)

        logging.info("Comando enviado para AutoCAD com sucesso.")
    except Exception as exc:
        logging.error("Erro ao executar no AutoCAD: %s", exc, exc_info=True)
