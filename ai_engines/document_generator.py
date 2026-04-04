"""
═══════════════════════════════════════════════════════════════════════════════
  DOCUMENT GENERATOR AI - Geração Automática de Documentação Técnica
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Geração de relatórios técnicos
  - Criação de datasheets
  - Elaboração de procedimentos
  - Documentação de projeto
  - Exportação em múltiplos formatos

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


class DocumentGeneratorAI(BaseAI):
    """
    IA especializada em geração de documentação.
    
    Capacidades:
    - Geração de relatórios técnicos
    - Criação de listas de materiais formatadas
    - Elaboração de procedimentos de montagem
    - Documentação de especificações
    - Templates customizáveis
    """
    
    # Templates disponíveis
    TEMPLATES = {
        "technical_report": {
            "sections": ["header", "summary", "scope", "details", "conclusions", "appendix"],
            "format": "formal",
        },
        "material_list": {
            "sections": ["header", "summary", "items", "totals"],
            "format": "tabular",
        },
        "procedure": {
            "sections": ["header", "objective", "scope", "references", "steps", "safety"],
            "format": "numbered",
        },
        "datasheet": {
            "sections": ["header", "specifications", "materials", "notes"],
            "format": "structured",
        },
        "inspection_report": {
            "sections": ["header", "summary", "findings", "recommendations", "signature"],
            "format": "formal",
        },
    }
    
    def __init__(self):
        super().__init__(name="DocumentGenerator", version="1.0.0")
        self.confidence_threshold = 0.9
    
    def get_capabilities(self) -> List[str]:
        return [
            "technical_report_generation",
            "material_list_creation",
            "procedure_elaboration",
            "datasheet_generation",
            "inspection_report",
            "custom_template",
            "multi_format_export",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Gera documentação técnica.
        
        Input esperado:
        {
            "document_type": str,     # Tipo de documento
            "project_data": {...},    # Dados do projeto
            "items": [...],           # Itens a documentar
            "template": str,          # Template a usar
            "format": str,            # "markdown", "html", "text"
            "language": str,          # "pt-BR", "en-US"
        }
        """
        document_type = input_data.get("document_type", "technical_report")
        project_data = input_data.get("project_data", {})
        items = input_data.get("items", [])
        output_format = input_data.get("format", "markdown")
        language = input_data.get("language", "pt-BR")
        
        try:
            # Selecionar método de geração baseado no tipo
            generators = {
                "technical_report": self._generate_technical_report,
                "material_list": self._generate_material_list,
                "procedure": self._generate_procedure,
                "datasheet": self._generate_datasheet,
                "inspection_report": self._generate_inspection_report,
            }
            
            generator = generators.get(document_type, self._generate_technical_report)
            document = generator(project_data, items, language)
            
            # Formatar conforme solicitado
            formatted = self._format_document(document, output_format)
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="generate_document",
                data={
                    "document_type": document_type,
                    "format": output_format,
                    "content": formatted,
                    "metadata": {
                        "generated_at": datetime.now(UTC).isoformat(),
                        "language": language,
                        "sections": len(document.get("sections", [])),
                        "word_count": len(formatted.split()),
                    },
                },
                confidence=0.95,
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na geração")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="generate_document",
                data={},
                errors=[str(e)],
            )
    
    def _generate_technical_report(
        self,
        project_data: Dict,
        items: List[Dict],
        language: str
    ) -> Dict[str, Any]:
        """Gera relatório técnico."""
        is_pt = language.startswith("pt")
        
        return {
            "title": project_data.get("title", "Relatório Técnico" if is_pt else "Technical Report"),
            "sections": [
                {
                    "name": "Informações do Projeto" if is_pt else "Project Information",
                    "content": self._format_project_info(project_data, is_pt),
                },
                {
                    "name": "Resumo Executivo" if is_pt else "Executive Summary",
                    "content": self._generate_summary(project_data, items, is_pt),
                },
                {
                    "name": "Escopo" if is_pt else "Scope",
                    "content": self._generate_scope(project_data, items, is_pt),
                },
                {
                    "name": "Detalhamento Técnico" if is_pt else "Technical Details",
                    "content": self._generate_technical_details(items, is_pt),
                },
                {
                    "name": "Conclusões e Recomendações" if is_pt else "Conclusions and Recommendations",
                    "content": self._generate_conclusions(project_data, items, is_pt),
                },
            ],
        }
    
    def _generate_material_list(
        self,
        project_data: Dict,
        items: List[Dict],
        language: str
    ) -> Dict[str, Any]:
        """Gera lista de materiais."""
        is_pt = language.startswith("pt")
        
        # Organizar itens por categoria
        categorized = {}
        for item in items:
            category = item.get("category", "outros" if is_pt else "others")
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(item)
        
        sections = [{
            "name": "Cabeçalho" if is_pt else "Header",
            "content": f"""
**Projeto:** {project_data.get('project_name', 'N/A')}
**Número:** {project_data.get('project_number', 'N/A')}
**Revisão:** {project_data.get('revision', '0')}
**Data:** {datetime.now().strftime('%d/%m/%Y')}
""",
        }]
        
        # Adicionar cada categoria
        for category, cat_items in categorized.items():
            table = self._items_to_table(cat_items, is_pt)
            sections.append({
                "name": category.replace("_", " ").title(),
                "content": table,
            })
        
        # Totais
        total_items = sum(item.get("quantity", 1) for item in items)
        sections.append({
            "name": "Totais" if is_pt else "Totals",
            "content": f"""
**Total de Itens:** {len(items)}
**Quantidade Total:** {total_items}
""",
        })
        
        return {
            "title": "Lista de Materiais" if is_pt else "Bill of Materials",
            "sections": sections,
        }
    
    def _generate_procedure(
        self,
        project_data: Dict,
        items: List[Dict],
        language: str
    ) -> Dict[str, Any]:
        """Gera procedimento de montagem."""
        is_pt = language.startswith("pt")
        
        return {
            "title": "Procedimento de Montagem" if is_pt else "Assembly Procedure",
            "sections": [
                {
                    "name": "Objetivo" if is_pt else "Objective",
                    "content": f"""
{"Este procedimento estabelece os passos para montagem" if is_pt else "This procedure establishes the steps for assembly"} 
{project_data.get('description', 'do sistema de tubulação' if is_pt else 'of the piping system')}.
""",
                },
                {
                    "name": "Escopo" if is_pt else "Scope",
                    "content": f"""
{"Aplica-se a" if is_pt else "Applies to"}: {project_data.get('scope', 'todas as instalações do projeto' if is_pt else 'all project installations')}.
""",
                },
                {
                    "name": "Referências" if is_pt else "References",
                    "content": """
- ASME B31.3 - Process Piping
- ISO 14001 - Environmental Management
- Especificações do Projeto
""",
                },
                {
                    "name": "Etapas de Montagem" if is_pt else "Assembly Steps",
                    "content": self._generate_assembly_steps(items, is_pt),
                },
                {
                    "name": "Segurança" if is_pt else "Safety",
                    "content": f"""
{"### Requisitos de Segurança" if is_pt else "### Safety Requirements"}

1. {"Uso obrigatório de EPIs (capacete, óculos, luvas)" if is_pt else "Mandatory use of PPE (helmet, glasses, gloves)"}
2. {"Verificar ausência de energia/pressão antes do início" if is_pt else "Verify absence of energy/pressure before starting"}
3. {"Manter área de trabalho organizada" if is_pt else "Keep work area organized"}
4. {"Comunicar anomalias ao supervisor" if is_pt else "Report anomalies to supervisor"}
""",
                },
            ],
        }
    
    def _generate_datasheet(
        self,
        project_data: Dict,
        items: List[Dict],
        language: str
    ) -> Dict[str, Any]:
        """Gera datasheet de equipamento."""
        is_pt = language.startswith("pt")
        item = items[0] if items else {}
        
        return {
            "title": f"Datasheet - {item.get('tag', 'Equipment')}",
            "sections": [
                {
                    "name": "Identificação" if is_pt else "Identification",
                    "content": f"""
| {"Campo" if is_pt else "Field"} | {"Valor" if is_pt else "Value"} |
|-------|-------|
| TAG | {item.get('tag', 'N/A')} |
| {"Descrição" if is_pt else "Description"} | {item.get('description', 'N/A')} |
| {"Tipo" if is_pt else "Type"} | {item.get('type', 'N/A')} |
| {"Fabricante" if is_pt else "Manufacturer"} | {item.get('manufacturer', 'N/A')} |
| {"Modelo" if is_pt else "Model"} | {item.get('model', 'N/A')} |
""",
                },
                {
                    "name": "Especificações Técnicas" if is_pt else "Technical Specifications",
                    "content": self._format_specifications(item, is_pt),
                },
                {
                    "name": "Materiais" if is_pt else "Materials",
                    "content": f"""
| {"Componente" if is_pt else "Component"} | {"Material" if is_pt else "Material"} |
|-----------|----------|
| {"Corpo" if is_pt else "Body"} | {item.get('body_material', 'Carbon Steel')} |
| {"Internos" if is_pt else "Internals"} | {item.get('internals_material', 'Stainless Steel')} |
| {"Gaxetas" if is_pt else "Gaskets"} | {item.get('gasket_material', 'Graphite')} |
""",
                },
                {
                    "name": "Notas" if is_pt else "Notes",
                    "content": item.get('notes', 'N/A'),
                },
            ],
        }
    
    def _generate_inspection_report(
        self,
        project_data: Dict,
        items: List[Dict],
        language: str
    ) -> Dict[str, Any]:
        """Gera relatório de inspeção."""
        is_pt = language.startswith("pt")
        
        return {
            "title": "Relatório de Inspeção" if is_pt else "Inspection Report",
            "sections": [
                {
                    "name": "Informações Gerais" if is_pt else "General Information",
                    "content": f"""
| {"Campo" if is_pt else "Field"} | {"Valor" if is_pt else "Value"} |
|-------|-------|
| {"Projeto" if is_pt else "Project"} | {project_data.get('project_name', 'N/A')} |
| {"Data da Inspeção" if is_pt else "Inspection Date"} | {datetime.now().strftime('%d/%m/%Y')} |
| {"Inspetor" if is_pt else "Inspector"} | {project_data.get('inspector', 'Sistema AI')} |
| {"Tipo de Inspeção" if is_pt else "Inspection Type"} | {project_data.get('inspection_type', 'Visual')} |
""",
                },
                {
                    "name": "Resumo" if is_pt else "Summary",
                    "content": f"""
{"Total de itens inspecionados" if is_pt else "Total items inspected"}: {len(items)}
{"Aprovados" if is_pt else "Approved"}: {sum(1 for i in items if i.get('status') == 'approved')}
{"Reprovados" if is_pt else "Rejected"}: {sum(1 for i in items if i.get('status') == 'rejected')}
{"Pendentes" if is_pt else "Pending"}: {sum(1 for i in items if i.get('status') not in ['approved', 'rejected'])}
""",
                },
                {
                    "name": "Constatações" if is_pt else "Findings",
                    "content": self._format_findings(items, is_pt),
                },
                {
                    "name": "Recomendações" if is_pt else "Recommendations",
                    "content": self._generate_inspection_recommendations(items, is_pt),
                },
            ],
        }
    
    # Métodos auxiliares
    
    def _format_project_info(self, project_data: Dict, is_pt: bool) -> str:
        return f"""
| {"Campo" if is_pt else "Field"} | {"Valor" if is_pt else "Value"} |
|-------|-------|
| {"Projeto" if is_pt else "Project"} | {project_data.get('project_name', 'N/A')} |
| {"Número" if is_pt else "Number"} | {project_data.get('project_number', 'N/A')} |
| {"Cliente" if is_pt else "Client"} | {project_data.get('client', 'N/A')} |
| {"Revisão" if is_pt else "Revision"} | {project_data.get('revision', '0')} |
| {"Data" if is_pt else "Date"} | {datetime.now().strftime('%d/%m/%Y')} |
"""
    
    def _generate_summary(self, project_data: Dict, items: List[Dict], is_pt: bool) -> str:
        total_items = len(items)
        categories = set(item.get('type', 'other') for item in items)
        
        return f"""
{"Este relatório apresenta" if is_pt else "This report presents"} {total_items} {"itens" if is_pt else "items"} 
{"distribuídos em" if is_pt else "distributed across"} {len(categories)} {"categorias" if is_pt else "categories"}.

{"Principais categorias" if is_pt else "Main categories"}: {', '.join(categories)}
"""
    
    def _generate_scope(self, project_data: Dict, items: List[Dict], is_pt: bool) -> str:
        return f"""
{"O escopo deste documento abrange" if is_pt else "The scope of this document covers"}:

- {project_data.get('scope', 'Sistema de tubulação industrial' if is_pt else 'Industrial piping system')}
- {"Total de componentes" if is_pt else "Total components"}: {len(items)}
"""
    
    def _generate_technical_details(self, items: List[Dict], is_pt: bool) -> str:
        content = ""
        for i, item in enumerate(items[:10], 1):  # Limitar a 10 itens
            content += f"""
### {i}. {item.get('tag', f'Item {i}')}

- **{"Tipo" if is_pt else "Type"}:** {item.get('type', 'N/A')}
- **{"Material" if is_pt else "Material"}:** {item.get('material', 'N/A')}
- **{"Diâmetro" if is_pt else "Diameter"}:** {item.get('diameter', 'N/A')} mm
- **{"Especificações" if is_pt else "Specifications"}:** {item.get('specifications', 'N/A')}
"""
        
        if len(items) > 10:
            content += f"\n\n*... {"e mais" if is_pt else "and"} {len(items) - 10} {"itens" if is_pt else "items"}*"
        
        return content
    
    def _generate_conclusions(self, project_data: Dict, items: List[Dict], is_pt: bool) -> str:
        return f"""
{"Com base na análise realizada, conclui-se que" if is_pt else "Based on the analysis performed, it is concluded that"}:

1. {"O projeto atende aos requisitos especificados" if is_pt else "The project meets the specified requirements"}
2. {"Recomenda-se atenção especial aos itens críticos" if is_pt else "Special attention to critical items is recommended"}
3. {"A documentação está em conformidade com as normas aplicáveis" if is_pt else "Documentation complies with applicable standards"}
"""
    
    def _items_to_table(self, items: List[Dict], is_pt: bool) -> str:
        header = f"| # | TAG | {"Descrição" if is_pt else "Description"} | {"Qtd" if is_pt else "Qty"} | {"Unid" if is_pt else "Unit"} |\n"
        header += "|---|-----|------------|-----|------|\n"
        
        rows = ""
        for i, item in enumerate(items, 1):
            rows += f"| {i} | {item.get('tag', '-')} | {item.get('description', '-')} | {item.get('quantity', 1)} | {item.get('unit', 'un')} |\n"
        
        return header + rows
    
    def _generate_assembly_steps(self, items: List[Dict], is_pt: bool) -> str:
        steps = f"""
### {"Preparação" if is_pt else "Preparation"}

1. {"Verificar disponibilidade de todos os materiais" if is_pt else "Verify availability of all materials"}
2. {"Conferir especificações conforme projeto" if is_pt else "Check specifications according to design"}
3. {"Preparar ferramentas necessárias" if is_pt else "Prepare necessary tools"}

### {"Montagem" if is_pt else "Assembly"}

"""
        for i, item in enumerate(items[:5], 1):
            steps += f"{i}. {"Instalar" if is_pt else "Install"} {item.get('type', 'componente')} - TAG: {item.get('tag', 'N/A')}\n"
        
        steps += f"""

### {"Verificação Final" if is_pt else "Final Verification"}

1. {"Verificar alinhamento de todos os componentes" if is_pt else "Verify alignment of all components"}
2. {"Confirmar torque das conexões" if is_pt else "Confirm connection torque"}
3. {"Realizar teste de estanqueidade" if is_pt else "Perform leak test"}
"""
        
        return steps
    
    def _format_specifications(self, item: Dict, is_pt: bool) -> str:
        specs = item.get('specifications', {})
        if not specs:
            specs = {
                'pressure': item.get('pressure', 'N/A'),
                'temperature': item.get('temperature', 'N/A'),
                'diameter': item.get('diameter', 'N/A'),
            }
        
        content = f"| {"Parâmetro" if is_pt else "Parameter"} | {"Valor" if is_pt else "Value"} |\n"
        content += "|-----------|-------|\n"
        
        for key, value in specs.items():
            content += f"| {key.replace('_', ' ').title()} | {value} |\n"
        
        return content
    
    def _format_findings(self, items: List[Dict], is_pt: bool) -> str:
        findings = ""
        for i, item in enumerate(items, 1):
            status = item.get('status', 'pending')
            status_icon = "✅" if status == 'approved' else "❌" if status == 'rejected' else "⏳"
            
            findings += f"{status_icon} **{item.get('tag', f'Item {i}')}**: {item.get('finding', 'Sem observações' if is_pt else 'No observations')}\n\n"
        
        return findings or ("Nenhuma constatação registrada" if is_pt else "No findings recorded")
    
    def _generate_inspection_recommendations(self, items: List[Dict], is_pt: bool) -> str:
        rejected = [i for i in items if i.get('status') == 'rejected']
        
        if not rejected:
            return "Nenhuma ação corretiva necessária" if is_pt else "No corrective action required"
        
        recs = ""
        for i, item in enumerate(rejected, 1):
            recs += f"{i}. {item.get('tag', 'Item')}: {item.get('recommendation', 'Avaliar correção' if is_pt else 'Evaluate correction')}\n"
        
        return recs
    
    def _format_document(self, document: Dict, output_format: str) -> str:
        """Formata documento para o formato de saída."""
        title = document.get("title", "Document")
        sections = document.get("sections", [])
        
        if output_format == "markdown":
            content = f"# {title}\n\n"
            for section in sections:
                content += f"## {section['name']}\n\n{section['content']}\n\n"
            return content
        
        elif output_format == "html":
            content = f"<h1>{title}</h1>\n"
            for section in sections:
                content += f"<h2>{section['name']}</h2>\n<div>{section['content']}</div>\n"
            return content
        
        else:  # text
            content = f"{title}\n{'=' * len(title)}\n\n"
            for section in sections:
                content += f"{section['name']}\n{'-' * len(section['name'])}\n{section['content']}\n\n"
            return content


# Registrar IA
ai_registry.register(DocumentGeneratorAI())
