"""
═══════════════════════════════════════════════════════════════════════════════
  ENTERPRISE EXPORT MANAGER
  Exportação para PDF, Excel, DWG e Outros Formatos
═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import json
import base64
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass
from io import BytesIO
import uuid

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Formatos de exportação suportados."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    DWG = "dwg"
    DXF = "dxf"
    STEP = "step"
    IGES = "iges"
    PNG = "png"
    SVG = "svg"
    HTML = "html"
    MARKDOWN = "markdown"
    WORD = "word"


class ExportType(str, Enum):
    """Tipos de conteúdo para exportação."""
    PROJECT = "project"
    DRAWING = "drawing"
    REPORT = "report"
    MTO = "mto"
    ANALYSIS = "analysis"
    AUDIT_LOG = "audit_log"
    WORKFLOW = "workflow"
    DASHBOARD = "dashboard"


@dataclass
class ExportRequest:
    """Requisição de exportação."""
    id: str
    type: ExportType
    format: ExportFormat
    data: Dict[str, Any]
    options: Dict[str, Any]
    requested_by: str
    requested_at: str
    status: str
    result_url: Optional[str]
    error: Optional[str]


@dataclass
class ExportTemplate:
    """Template de exportação."""
    id: str
    name: str
    type: ExportType
    format: ExportFormat
    template_content: str
    styles: Dict[str, Any]
    header: Optional[str]
    footer: Optional[str]
    is_default: bool


class ExportManager:
    """Gerenciador de exportações."""
    
    _instance: Optional['ExportManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.exports: Dict[str, ExportRequest] = {}
        self.templates: Dict[str, ExportTemplate] = {}
        self._setup_default_templates()
        logger.info("ExportManager initialized")
    
    def _setup_default_templates(self):
        """Configura templates padrão."""
        # Template de relatório técnico
        self.templates["tpl_tech_report"] = ExportTemplate(
            id="tpl_tech_report",
            name="Relatório Técnico",
            type=ExportType.REPORT,
            format=ExportFormat.PDF,
            template_content="""
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        h1 { color: #1a365d; border-bottom: 2px solid #2b6cb0; }
                        h2 { color: #2b6cb0; }
                        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                        th { background-color: #2b6cb0; color: white; }
                        .header { display: flex; justify-content: space-between; }
                        .logo { height: 50px; }
                        .footer { text-align: center; font-size: 10px; color: #666; }
                    </style>
                </head>
                <body>
                    {{CONTENT}}
                </body>
                </html>
            """,
            styles={
                "primary_color": "#2b6cb0",
                "font_family": "Arial, sans-serif",
            },
            header="ENGENHARIA CAD - Relatório Técnico",
            footer="Documento gerado automaticamente por ForgeCad Enterprise",
            is_default=True,
        )
        
        # Template de MTO
        self.templates["tpl_mto"] = ExportTemplate(
            id="tpl_mto",
            name="Lista de Materiais (MTO)",
            type=ExportType.MTO,
            format=ExportFormat.EXCEL,
            template_content="",
            styles={
                "header_bg": "#2b6cb0",
                "alternating_rows": True,
            },
            header="MTO - Material Take-Off",
            footer=None,
            is_default=True,
        )
    
    async def export(
        self,
        export_type: ExportType,
        export_format: ExportFormat,
        data: Dict[str, Any],
        options: Dict[str, Any] = None,
        requested_by: str = "system",
    ) -> ExportRequest:
        """Executa uma exportação."""
        export_id = f"exp_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).isoformat()
        
        request = ExportRequest(
            id=export_id,
            type=export_type,
            format=export_format,
            data=data,
            options=options or {},
            requested_by=requested_by,
            requested_at=now,
            status="processing",
            result_url=None,
            error=None,
        )
        
        self.exports[export_id] = request
        
        try:
            # Executar exportação baseado no formato
            if export_format == ExportFormat.PDF:
                result = await self._export_pdf(export_type, data, options or {})
            elif export_format == ExportFormat.EXCEL:
                result = await self._export_excel(export_type, data, options or {})
            elif export_format == ExportFormat.CSV:
                result = await self._export_csv(export_type, data, options or {})
            elif export_format == ExportFormat.JSON:
                result = await self._export_json(export_type, data, options or {})
            elif export_format == ExportFormat.HTML:
                result = await self._export_html(export_type, data, options or {})
            elif export_format == ExportFormat.MARKDOWN:
                result = await self._export_markdown(export_type, data, options or {})
            else:
                result = await self._export_generic(export_type, export_format, data, options or {})
            
            request.status = "completed"
            request.result_url = result.get("url")
            
        except Exception as e:
            request.status = "failed"
            request.error = str(e)
            logger.error(f"Export failed: {e}")
        
        return request
    
    async def _export_pdf(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação PDF."""
        logger.info(f"Generating PDF for {export_type.value}")
        
        # Simulação de geração de PDF
        html_content = self._generate_html_content(export_type, data)
        
        # Em produção: usar weasyprint ou puppeteer para gerar PDF
        return {
            "url": f"/api/export/download/pdf/{uuid.uuid4().hex[:8]}",
            "content_type": "application/pdf",
            "size_bytes": len(html_content) * 2,  # Estimativa
        }
    
    async def _export_excel(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação Excel."""
        logger.info(f"Generating Excel for {export_type.value}")
        
        # Simulação - em produção usar openpyxl
        sheets_data = self._prepare_excel_data(export_type, data)
        
        return {
            "url": f"/api/export/download/xlsx/{uuid.uuid4().hex[:8]}",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "sheets": len(sheets_data),
        }
    
    async def _export_csv(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação CSV."""
        logger.info(f"Generating CSV for {export_type.value}")
        
        csv_content = self._generate_csv_content(data)
        
        return {
            "url": f"/api/export/download/csv/{uuid.uuid4().hex[:8]}",
            "content_type": "text/csv",
            "rows": csv_content.count("\n"),
        }
    
    async def _export_json(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação JSON."""
        logger.info(f"Generating JSON for {export_type.value}")
        
        json_content = json.dumps(data, indent=2, default=str)
        encoded = base64.b64encode(json_content.encode()).decode()
        
        return {
            "url": f"data:application/json;base64,{encoded}",
            "content_type": "application/json",
            "size_bytes": len(json_content),
        }
    
    async def _export_html(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação HTML."""
        logger.info(f"Generating HTML for {export_type.value}")
        
        html_content = self._generate_html_content(export_type, data)
        encoded = base64.b64encode(html_content.encode()).decode()
        
        return {
            "url": f"data:text/html;base64,{encoded}",
            "content_type": "text/html",
            "size_bytes": len(html_content),
        }
    
    async def _export_markdown(self, export_type: ExportType, data: Dict, options: Dict) -> Dict:
        """Gera exportação Markdown."""
        logger.info(f"Generating Markdown for {export_type.value}")
        
        md_content = self._generate_markdown_content(export_type, data)
        encoded = base64.b64encode(md_content.encode()).decode()
        
        return {
            "url": f"data:text/markdown;base64,{encoded}",
            "content_type": "text/markdown",
            "size_bytes": len(md_content),
        }
    
    async def _export_generic(self, export_type: ExportType, export_format: ExportFormat, data: Dict, options: Dict) -> Dict:
        """Exportação genérica para outros formatos."""
        logger.info(f"Generating {export_format.value} for {export_type.value}")
        
        return {
            "url": f"/api/export/download/{export_format.value}/{uuid.uuid4().hex[:8]}",
            "content_type": "application/octet-stream",
        }
    
    def _generate_html_content(self, export_type: ExportType, data: Dict) -> str:
        """Gera conteúdo HTML baseado no tipo."""
        title = data.get("title", "Relatório")
        
        if export_type == ExportType.PROJECT:
            content = self._generate_project_html(data)
        elif export_type == ExportType.MTO:
            content = self._generate_mto_html(data)
        elif export_type == ExportType.ANALYSIS:
            content = self._generate_analysis_html(data)
        else:
            content = f"<pre>{json.dumps(data, indent=2, default=str)}</pre>"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #1a365d; border-bottom: 3px solid #2b6cb0; padding-bottom: 10px; }}
                h2 {{ color: #2b6cb0; margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #2b6cb0; color: white; padding: 12px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 10px; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                .metric {{ display: inline-block; padding: 15px 25px; background: #e6f3ff; border-radius: 8px; margin: 10px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2b6cb0; }}
                .metric-label {{ font-size: 12px; color: #666; }}
                .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
                .logo {{ font-size: 24px; font-weight: bold; color: #2b6cb0; }}
                .date {{ color: #666; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">ENGENHARIA CAD</div>
                    <div class="date">{datetime.now().strftime("%d/%m/%Y %H:%M")}</div>
                </div>
                <h1>{title}</h1>
                {content}
                <div class="footer">
                    Gerado automaticamente por ForgeCad Enterprise v2.0
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_project_html(self, data: Dict) -> str:
        """Gera HTML para projeto."""
        return f"""
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{data.get('components', 0)}</div>
                <div class="metric-label">Componentes</div>
            </div>
            <div class="metric">
                <div class="metric-value">R$ {data.get('total_cost', 0):,.2f}</div>
                <div class="metric-label">Custo Total</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data.get('quality_score', 0)}%</div>
                <div class="metric-label">Quality Score</div>
            </div>
        </div>
        <h2>Detalhes do Projeto</h2>
        <table>
            <tr><th>Campo</th><th>Valor</th></tr>
            {"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in data.items() if k not in ['title'])}
        </table>
        """
    
    def _generate_mto_html(self, data: Dict) -> str:
        """Gera HTML para MTO."""
        items = data.get("items", [])
        rows = ""
        for item in items:
            rows += f"""
            <tr>
                <td>{item.get('code', '-')}</td>
                <td>{item.get('description', '-')}</td>
                <td>{item.get('quantity', 0)}</td>
                <td>{item.get('unit', '-')}</td>
                <td>R$ {item.get('unit_price', 0):,.2f}</td>
                <td>R$ {item.get('total', 0):,.2f}</td>
            </tr>
            """
        
        return f"""
        <h2>Lista de Materiais</h2>
        <table>
            <thead>
                <tr>
                    <th>Código</th>
                    <th>Descrição</th>
                    <th>Qtd</th>
                    <th>Un</th>
                    <th>Preço Unit.</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {rows if rows else "<tr><td colspan='6'>Nenhum item</td></tr>"}
            </tbody>
        </table>
        <h3>Totais</h3>
        <p><strong>Total Geral:</strong> R$ {data.get('total', 0):,.2f}</p>
        """
    
    def _generate_analysis_html(self, data: Dict) -> str:
        """Gera HTML para análise."""
        return f"""
        <h2>Resultados da Análise</h2>
        <div class="metrics">
            <div class="metric">
                <div class="metric-value">{data.get('entities_found', 0)}</div>
                <div class="metric-label">Entidades</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data.get('conflicts', 0)}</div>
                <div class="metric-label">Conflitos</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data.get('compliance', 0)}%</div>
                <div class="metric-label">Conformidade</div>
            </div>
        </div>
        <h2>Detalhes</h2>
        <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto;">
{json.dumps(data, indent=2, default=str)}
        </pre>
        """
    
    def _generate_markdown_content(self, export_type: ExportType, data: Dict) -> str:
        """Gera conteúdo Markdown."""
        title = data.get("title", "Relatório")
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        md = f"""# {title}

*Gerado em: {now}*

---

"""
        
        if export_type == ExportType.PROJECT:
            md += "## Métricas do Projeto\n\n"
            md += f"- **Componentes:** {data.get('components', 0)}\n"
            md += f"- **Custo Total:** R$ {data.get('total_cost', 0):,.2f}\n"
            md += f"- **Quality Score:** {data.get('quality_score', 0)}%\n\n"
        
        md += "## Dados Completos\n\n"
        md += "```json\n"
        md += json.dumps(data, indent=2, default=str)
        md += "\n```\n\n"
        
        md += "---\n\n*ForgeCad Enterprise v2.0*"
        
        return md
    
    def _prepare_excel_data(self, export_type: ExportType, data: Dict) -> List[Dict]:
        """Prepara dados para Excel."""
        if export_type == ExportType.MTO:
            return [{"name": "MTO", "data": data.get("items", [])}]
        return [{"name": "Dados", "data": [data]}]
    
    def _generate_csv_content(self, data: Dict) -> str:
        """Gera conteúdo CSV."""
        import csv
        from io import StringIO
        
        output = StringIO()
        
        if "items" in data:
            items = data["items"]
            if items:
                writer = csv.DictWriter(output, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)
        else:
            writer = csv.DictWriter(output, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
        
        return output.getvalue()
    
    def get_export(self, export_id: str) -> Optional[ExportRequest]:
        """Obtém uma exportação pelo ID."""
        return self.exports.get(export_id)
    
    def get_exports_by_user(self, user_email: str, limit: int = 20) -> List[ExportRequest]:
        """Retorna exportações de um usuário."""
        user_exports = [e for e in self.exports.values() if e.requested_by == user_email]
        return sorted(user_exports, key=lambda x: x.requested_at, reverse=True)[:limit]


# Singleton instance
export_manager = ExportManager()
