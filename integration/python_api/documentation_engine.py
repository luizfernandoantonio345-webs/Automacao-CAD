from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _render_component_markdown(component: dict[str, Any]) -> str:
    comp_id = str(component.get("id", "COMP-UNKNOWN"))
    categoria = component.get("categoria", "GENERICA")
    norma = component.get("norma", "N/A")
    peso_kg = component.get("peso_kg", 0.0)
    dados = component.get("dados", {})

    return (
        f"# Memorial de Cálculo - {comp_id}\n\n"
        f"- Categoria: **{categoria}**\n"
        f"- Norma de Referência: **{norma}**\n"
        f"- Peso Estimado: **{peso_kg} kg**\n"
        f"- Timestamp: **{datetime.now(timezone.utc).isoformat()}**\n\n"
        "## Premissas\n"
        "- Geometria gerada automaticamente por motor SmartDesign.\n"
        "- Verificação preliminar de interferência por bounding box.\n"
        "- Conformidade consultada a partir de dicionário dinâmico de normas.\n\n"
        "## Dados de Entrada\n\n"
        "```json\n"
        f"{dados}\n"
        "```\n\n"
        "## Folha de Dados\n"
        "- Tipo de componente: padronizado para fabricação\n"
        "- Criticidade: média\n"
        "- Revisão: 0\n"
    )


def _try_write_pdf_stub(md_path: Path, markdown_content: str) -> tuple[Path | None, bool]:
    pdf_path = md_path.with_suffix(".pdf")
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        y = 800
        for line in markdown_content.splitlines():
            c.drawString(40, y, line[:110])
            y -= 14
            if y < 40:
                c.showPage()
                y = 800
        c.save()
        return pdf_path, True
    except Exception:
        return None, False


def _generate_single_doc(component: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    comp_id = str(component.get("id", "COMP-UNKNOWN"))
    md_path = output_dir / f"{comp_id}.md"
    content = _render_component_markdown(component)
    md_path.write_text(content, encoding="utf-8")

    pdf_path, pdf_ok = _try_write_pdf_stub(md_path, content)
    return {
        "component_id": comp_id,
        "markdown": str(md_path),
        "pdf": str(pdf_path) if pdf_path else None,
        "pdf_generated": pdf_ok,
    }


def generate_batch_documentation(
    components: list[dict[str, Any]],
    output_dir: Path,
    max_workers: int = 16,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    workers = max(1, min(max_workers, 64))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        artifacts = list(executor.map(lambda comp: _generate_single_doc(comp, output_dir), components))

    return {
        "status": "ok",
        "components": len(components),
        "workers": workers,
        "artifacts": artifacts,
        "message": "Documentação em lote concluída (Markdown + PDF quando disponível).",
    }

