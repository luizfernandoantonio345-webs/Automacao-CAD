from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from engenharia_automacao.app.auth import AuthService, AuthenticationError, LicenseError
from engenharia_automacao.app.controllers.project_controller import ProjectController, ValidationError
from engenharia_automacao.core.config import USE_LOGIN


class MainWindow:
    """UI desktop com dois modos: entrada manual e leitura por Excel."""

    def __init__(self, controller: ProjectController | None = None) -> None:
        self.controller = controller or ProjectController()
        self.root = tk.Tk()
        self.root.title("Engenharia Automacao")
        self.root.resizable(False, False)
        self.manual_entries: dict[str, tk.Entry] = {}
        self.excel_path_var = tk.StringVar()
        self.excel_output_var = tk.StringVar()
        self.auth_service = AuthService()
        self.current_user: dict | None = None

        if USE_LOGIN and not self._login():
            self.root.destroy()
            return

        self._build()

    def _login(self) -> bool:
        while True:
            email = simpledialog.askstring("Login", "E-mail:", parent=self.root)
            if email is None:
                return False
            senha = simpledialog.askstring("Login", "Senha:", parent=self.root, show="*")
            if senha is None:
                return False

            try:
                usuario = self.auth_service.authenticate(email.strip(), senha.strip())
            except AuthenticationError as exc:
                messagebox.showerror("Erro de login", str(exc), parent=self.root)
                continue

            if not self.auth_service.verificar_limite(usuario):
                messagebox.showerror("Limite atingido", "Limite de uso atingido. Contate o administrador.", parent=self.root)
                return False

            self.current_user = usuario
            messagebox.showinfo("Login bem sucedido", f"Bem-vindo {usuario.get('empresa')}", parent=self.root)
            return True

    def _build(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        manual_tab = ttk.Frame(notebook, padding=12)
        excel_tab = ttk.Frame(notebook, padding=12)
        notebook.add(manual_tab, text="Manual")
        notebook.add(excel_tab, text="Excel")

        self._build_manual_tab(manual_tab)
        self._build_excel_tab(excel_tab)

    def _build_manual_tab(self, parent: ttk.Frame) -> None:
        fields = [
            ("diameter", "Diametro"),
            ("length", "Comprimento"),
            ("company", "Empresa"),
            ("part_name", "Nome da peca"),
            ("code", "Codigo"),
        ]
        for row, (field, label) in enumerate(fields):
            ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(parent, width=34)
            entry.grid(row=row, column=1, pady=4)
            self.manual_entries[field] = entry

        ttk.Button(parent, text="Gerar projeto", command=self._handle_manual_generate).grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(12, 0),
        )

    def _build_excel_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Arquivo Excel", width=18).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=self.excel_path_var, width=34).grid(row=0, column=1, pady=4)
        ttk.Button(parent, text="Selecionar", command=self._select_excel_file).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(parent, text="Pasta de saida", width=18).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=self.excel_output_var, width=34).grid(row=1, column=1, pady=4)
        ttk.Button(parent, text="Selecionar", command=self._select_output_dir).grid(row=1, column=2, padx=(8, 0))

        ttk.Button(parent, text="Gerar projetos", command=self._handle_excel_generate).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(12, 0),
        )

    def _select_excel_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecionar planilha",
            filetypes=[("Excel", "*.xlsx *.xls")],
        )
        if selected:
            self.excel_path_var.set(selected)

    def _select_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Selecionar pasta de saida")
        if selected:
            self.excel_output_var.set(selected)

    def _handle_manual_generate(self) -> None:
        payload = {field: entry.get() for field, entry in self.manual_entries.items()}
        output_file = filedialog.asksaveasfilename(
            title="Salvar arquivo LISP",
            defaultextension=".lsp",
            filetypes=[("AutoLISP", "*.lsp")],
            initialfile=f"{payload.get('code', '').strip() or 'projeto'}.lsp",
        )
        if not output_file:
            return

        try:
            saved_path = self.controller.generate_manual(payload, Path(output_file))
            if self.current_user:
                self.auth_service.incrementar_uso(self.current_user, quantidade=1)
        except ValidationError as exc:
            messagebox.showerror("Erro de validacao", str(exc))
            return
        except (FileNotFoundError, OSError, ValueError, LicenseError) as exc:
            messagebox.showerror("Erro", str(exc))
            return

        messagebox.showinfo("Sucesso", f"Arquivo gerado em:\n{saved_path}")

    def _handle_excel_generate(self) -> None:
        excel_file = self.excel_path_var.get().strip()
        output_dir = self.excel_output_var.get().strip()
        if not excel_file or not output_dir:
            messagebox.showerror("Erro", "Selecione a planilha e a pasta de saida.")
            return

        try:
            generated_files = self.controller.generate_from_excel(excel_file, output_dir)
        except ValidationError as exc:
            messagebox.showerror("Erro de validacao", str(exc))
            return
        except (FileNotFoundError, OSError, ValueError) as exc:
            messagebox.showerror("Erro", str(exc))
            return

        messagebox.showinfo("Sucesso", f"{len(generated_files)} arquivo(s) gerado(s).")

    def start(self) -> None:
        self.root.mainloop()
