from __future__ import annotations

from engenharia_automacao.app.ui.main_window import MainWindow


class App:
    """Ponto de montagem da interface desktop."""

    def __init__(self) -> None:
        self.window = MainWindow()

    def start(self) -> None:
        self.window.start()


def main() -> None:
    """Ponto de entrada da aplicacao."""
    App().start()


if __name__ == "__main__":
    main()
