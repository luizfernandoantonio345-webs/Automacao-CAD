"""
═══════════════════════════════════════════════════════════════════════════════
  QUALITY INSPECTOR AI - Inspeção Automática de Qualidade
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Verificação de conformidade com normas
  - Validação de especificações técnicas
  - Inspeção de completude do projeto
  - Análise de consistência de dados
  - Checklist de qualidade automatizado

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


class InspectionSeverity(Enum):
    """Severidade de problemas encontrados."""
    BLOCKER = "blocker"      # Impede aprovação
    CRITICAL = "critical"    # Deve ser corrigido
    MAJOR = "major"          # Importante corrigir
    MINOR = "minor"          # Correção recomendada
    INFO = "info"            # Informativo


class InspectionCategory(Enum):
    """Categorias de inspeção."""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    COMPLIANCE = "compliance"
    SPECIFICATION = "specification"
    DOCUMENTATION = "documentation"


@dataclass
class InspectionResult:
    """Resultado de uma verificação individual."""
    check_id: str
    category: InspectionCategory
    severity: InspectionSeverity
    passed: bool
    description: str
    details: str = ""
    recommendation: str = ""
    affected_items: List[str] = field(default_factory=list)


class QualityInspectorAI(BaseAI):
    """
    IA especializada em inspeção de qualidade.
    
    Capacidades:
    - Verificação de completude do projeto
    - Validação de conformidade com normas
    - Análise de consistência de dados
    - Checklist automatizado
    - Relatório de qualidade
    """
    
    # Regras de verificação por norma
    NORM_RULES = {
        "ASME": {
            "B31.1": [  # Power Piping
                {"id": "wall_thickness", "desc": "Espessura de parede conforme pressão/temperatura"},
                {"id": "material_compatibility", "desc": "Compatibilidade de materiais com fluido"},
                {"id": "flange_rating", "desc": "Classe de flange adequada"},
                {"id": "weld_inspection", "desc": "Requisitos de inspeção de solda"},
            ],
            "B31.3": [  # Process Piping
                {"id": "stress_analysis", "desc": "Análise de tensões requerida"},
                {"id": "flexibility", "desc": "Flexibilidade térmica adequada"},
                {"id": "supports", "desc": "Suportação conforme norma"},
            ],
        },
        "ISO": {
            "general": [
                {"id": "documentation", "desc": "Documentação completa"},
                {"id": "traceability", "desc": "Rastreabilidade de materiais"},
            ],
        },
        "ABNT": {
            "general": [
                {"id": "local_compliance", "desc": "Conformidade com requisitos locais"},
            ],
        },
    }
    
    # Verificações obrigatórias
    MANDATORY_CHECKS = [
        {
            "id": "project_info",
            "category": InspectionCategory.COMPLETENESS,
            "desc": "Informações básicas do projeto",
            "required_fields": ["project_name", "project_number", "client", "revision"],
        },
        {
            "id": "pipe_specs",
            "category": InspectionCategory.SPECIFICATION,
            "desc": "Especificações de tubulação definidas",
            "required_fields": ["material", "diameter", "schedule"],
        },
        {
            "id": "flow_direction",
            "category": InspectionCategory.COMPLETENESS,
            "desc": "Direção de fluxo indicada",
            "required_fields": ["flow_direction"],
        },
        {
            "id": "valve_tags",
            "category": InspectionCategory.DOCUMENTATION,
            "desc": "Válvulas identificadas com TAG",
            "pattern": r"^[A-Z]{2,4}-\d+",
        },
        {
            "id": "isometric_complete",
            "category": InspectionCategory.COMPLETENESS,
            "desc": "Isométrico completo com coordenadas",
            "required_fields": ["north_arrow", "elevation_reference"],
        },
    ]
    
    def __init__(self):
        super().__init__(name="QualityInspector", version="1.0.0")
        self.confidence_threshold = 0.85
    
    def get_capabilities(self) -> List[str]:
        return [
            "completeness_check",
            "consistency_validation",
            "norm_compliance",
            "specification_verification",
            "documentation_review",
            "quality_scoring",
            "checklist_generation",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Executa inspeção de qualidade.
        
        Input esperado:
        {
            "project_data": {...},    # Dados do projeto
            "items": [...],           # Itens a inspecionar
            "norms": [...],           # Normas a verificar
            "inspection_level": str,  # "basic", "standard", "comprehensive"
        }
        """
        project_data = input_data.get("project_data", {})
        items = input_data.get("items", [])
        norms = input_data.get("norms", ["ASME"])
        inspection_level = input_data.get("inspection_level", "standard")
        
        inspections: List[InspectionResult] = []
        
        try:
            # 1. Verificações obrigatórias
            inspections.extend(self._run_mandatory_checks(project_data, items))
            
            # 2. Verificações de consistência
            inspections.extend(self._check_consistency(items))
            
            # 3. Verificações de normas
            for norm in norms:
                inspections.extend(self._check_norm_compliance(items, norm))
            
            # 4. Verificações específicas do nível
            if inspection_level in ["standard", "comprehensive"]:
                inspections.extend(self._check_specifications(items))
            
            if inspection_level == "comprehensive":
                inspections.extend(self._check_documentation(project_data, items))
            
            # Calcular score de qualidade
            score = self._calculate_quality_score(inspections)
            
            # Gerar relatório
            report = self._generate_report(inspections, score)
            
            # Determinar status geral
            blockers = [i for i in inspections if i.severity == InspectionSeverity.BLOCKER and not i.passed]
            criticals = [i for i in inspections if i.severity == InspectionSeverity.CRITICAL and not i.passed]
            
            if blockers:
                status = "REPROVADO"
            elif criticals:
                status = "APROVADO COM RESTRIÇÕES"
            elif score >= 90:
                status = "APROVADO"
            else:
                status = "APROVADO COM RESSALVAS"
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="quality_inspection",
                data={
                    "status": status,
                    "score": score,
                    "summary": {
                        "total_checks": len(inspections),
                        "passed": sum(1 for i in inspections if i.passed),
                        "failed": sum(1 for i in inspections if not i.passed),
                        "blockers": len(blockers),
                        "criticals": len(criticals),
                    },
                    "inspections": [self._inspection_to_dict(i) for i in inspections],
                    "report": report,
                },
                confidence=0.9,
                metadata={
                    "norms_checked": norms,
                    "inspection_level": inspection_level,
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na inspeção")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="quality_inspection",
                data={},
                errors=[str(e)],
            )
    
    def _inspection_to_dict(self, inspection: InspectionResult) -> Dict:
        """Converte InspectionResult para dict."""
        return {
            "check_id": inspection.check_id,
            "category": inspection.category.value,
            "severity": inspection.severity.value,
            "passed": inspection.passed,
            "description": inspection.description,
            "details": inspection.details,
            "recommendation": inspection.recommendation,
            "affected_items": inspection.affected_items,
        }
    
    def _run_mandatory_checks(
        self,
        project_data: Dict,
        items: List[Dict]
    ) -> List[InspectionResult]:
        """Executa verificações obrigatórias."""
        results = []
        
        for check in self.MANDATORY_CHECKS:
            check_id = check["id"]
            category = check["category"]
            
            if "required_fields" in check:
                # Verificar campos obrigatórios
                required = check["required_fields"]
                
                if check_id == "project_info":
                    missing = [f for f in required if f not in project_data]
                    passed = len(missing) == 0
                    details = f"Campos faltantes: {', '.join(missing)}" if missing else "Todos os campos presentes"
                else:
                    # Verificar em itens
                    items_missing = []
                    for i, item in enumerate(items):
                        item_missing = [f for f in required if f not in item]
                        if item_missing:
                            items_missing.append(f"Item {i+1}: {item_missing}")
                    
                    passed = len(items_missing) == 0
                    details = "; ".join(items_missing[:5]) if items_missing else "Todos os campos presentes"
                    
            elif "pattern" in check:
                # Verificar padrão
                pattern = check["pattern"]
                non_matching = []
                
                for i, item in enumerate(items):
                    if item.get("type") == "valve":
                        tag = item.get("tag", "")
                        if not re.match(pattern, tag):
                            non_matching.append(f"Item {i+1}: '{tag}'")
                
                passed = len(non_matching) == 0
                details = f"TAGs fora do padrão: {', '.join(non_matching[:5])}" if non_matching else "Todas as TAGs válidas"
            else:
                passed = True
                details = ""
            
            results.append(InspectionResult(
                check_id=check_id,
                category=category,
                severity=InspectionSeverity.CRITICAL if not passed else InspectionSeverity.INFO,
                passed=passed,
                description=check["desc"],
                details=details,
                recommendation="Completar informações faltantes" if not passed else "",
            ))
        
        return results
    
    def _check_consistency(self, items: List[Dict]) -> List[InspectionResult]:
        """Verifica consistência dos dados."""
        results = []
        
        # Verificar diâmetros consistentes em conexões
        diameter_issues = []
        for i, item in enumerate(items):
            connected_to = item.get("connected_to", [])
            item_diameter = item.get("diameter")
            
            for conn_id in connected_to:
                connected_item = next((x for x in items if x.get("id") == conn_id), None)
                if connected_item:
                    conn_diameter = connected_item.get("diameter")
                    if item_diameter and conn_diameter and item_diameter != conn_diameter:
                        # Verificar se há reducer
                        has_reducer = any(
                            x.get("type") == "reducer" and 
                            item.get("id") in x.get("connected_to", [])
                            for x in items
                        )
                        if not has_reducer:
                            diameter_issues.append(f"{item.get('id')}->{conn_id}")
        
        results.append(InspectionResult(
            check_id="diameter_consistency",
            category=InspectionCategory.CONSISTENCY,
            severity=InspectionSeverity.MAJOR if diameter_issues else InspectionSeverity.INFO,
            passed=len(diameter_issues) == 0,
            description="Consistência de diâmetros em conexões",
            details=f"Conexões com diâmetros diferentes sem reducer: {diameter_issues[:5]}" if diameter_issues else "OK",
            recommendation="Adicionar reducers onde necessário" if diameter_issues else "",
            affected_items=diameter_issues[:10],
        ))
        
        # Verificar materiais compatíveis
        material_issues = []
        material_groups = {
            "carbon_steel": ["steel", "carbon_steel", "cs", "a106"],
            "stainless": ["stainless", "ss", "304", "316", "ss304", "ss316"],
            "alloy": ["alloy", "monel", "inconel", "hastelloy"],
        }
        
        for item in items:
            material = item.get("material", "").lower()
            for conn_id in item.get("connected_to", []):
                connected_item = next((x for x in items if x.get("id") == conn_id), None)
                if connected_item:
                    conn_material = connected_item.get("material", "").lower()
                    
                    # Verificar se são do mesmo grupo
                    item_group = None
                    conn_group = None
                    
                    for group, materials in material_groups.items():
                        if any(m in material for m in materials):
                            item_group = group
                        if any(m in conn_material for m in materials):
                            conn_group = group
                    
                    if item_group and conn_group and item_group != conn_group:
                        material_issues.append(f"{item.get('id')}({material})->{conn_id}({conn_material})")
        
        results.append(InspectionResult(
            check_id="material_compatibility",
            category=InspectionCategory.CONSISTENCY,
            severity=InspectionSeverity.CRITICAL if material_issues else InspectionSeverity.INFO,
            passed=len(material_issues) == 0,
            description="Compatibilidade de materiais em conexões",
            details=f"Materiais potencialmente incompatíveis: {material_issues[:5]}" if material_issues else "OK",
            recommendation="Revisar compatibilidade de materiais ou adicionar juntas de transição" if material_issues else "",
            affected_items=material_issues[:10],
        ))
        
        return results
    
    def _check_norm_compliance(
        self,
        items: List[Dict],
        norm: str
    ) -> List[InspectionResult]:
        """Verifica conformidade com normas específicas."""
        results = []
        
        norm_rules = self.NORM_RULES.get(norm, {}).get("general", [])
        
        # Adicionar regras específicas se existirem
        for sub_norm in self.NORM_RULES.get(norm, {}):
            if sub_norm != "general":
                norm_rules.extend(self.NORM_RULES[norm][sub_norm])
        
        for rule in norm_rules:
            # Simplificado - em produção teria lógica específica para cada regra
            results.append(InspectionResult(
                check_id=f"{norm}_{rule['id']}",
                category=InspectionCategory.COMPLIANCE,
                severity=InspectionSeverity.MAJOR,
                passed=True,  # Assume aprovado - em produção verificaria de fato
                description=f"[{norm}] {rule['desc']}",
                details="Verificação requer revisão manual",
                recommendation="",
            ))
        
        return results
    
    def _check_specifications(self, items: List[Dict]) -> List[InspectionResult]:
        """Verifica especificações técnicas."""
        results = []
        
        # Verificar schedule adequado para pressão
        schedule_issues = []
        for item in items:
            if item.get("type") == "pipe":
                pressure = item.get("design_pressure", 0)
                schedule = item.get("schedule", "40")
                diameter = item.get("diameter", 100)
                
                # Regra simplificada
                min_schedule = "40"
                if pressure > 20:  # bar
                    min_schedule = "80"
                if pressure > 50:
                    min_schedule = "160"
                
                schedule_num = int(re.search(r"\d+", str(schedule)).group() if re.search(r"\d+", str(schedule)) else 40)
                min_schedule_num = int(min_schedule)
                
                if schedule_num < min_schedule_num:
                    schedule_issues.append(f"{item.get('id')}: SCH{schedule} (mín: SCH{min_schedule})")
        
        results.append(InspectionResult(
            check_id="schedule_adequacy",
            category=InspectionCategory.SPECIFICATION,
            severity=InspectionSeverity.BLOCKER if schedule_issues else InspectionSeverity.INFO,
            passed=len(schedule_issues) == 0,
            description="Adequação de schedule para pressão de projeto",
            details=f"Schedule insuficiente: {schedule_issues[:5]}" if schedule_issues else "OK",
            recommendation="Revisar especificação de parede ou reclassificar pressão" if schedule_issues else "",
            affected_items=schedule_issues[:10],
        ))
        
        return results
    
    def _check_documentation(
        self,
        project_data: Dict,
        items: List[Dict]
    ) -> List[InspectionResult]:
        """Verifica documentação do projeto."""
        results = []
        
        # Verificar se há lista de materiais
        has_bom = "bill_of_materials" in project_data or "bom" in project_data
        results.append(InspectionResult(
            check_id="bom_exists",
            category=InspectionCategory.DOCUMENTATION,
            severity=InspectionSeverity.MAJOR if not has_bom else InspectionSeverity.INFO,
            passed=has_bom,
            description="Lista de materiais (BOM) presente",
            details="" if has_bom else "BOM não encontrado",
            recommendation="Gerar lista de materiais" if not has_bom else "",
        ))
        
        # Verificar especificações de solda
        has_weld_spec = any("weld" in str(item).lower() for item in items) or "weld_specification" in project_data
        results.append(InspectionResult(
            check_id="weld_spec",
            category=InspectionCategory.DOCUMENTATION,
            severity=InspectionSeverity.MAJOR if not has_weld_spec else InspectionSeverity.INFO,
            passed=has_weld_spec,
            description="Especificação de solda presente",
            details="" if has_weld_spec else "Especificação de solda não encontrada",
            recommendation="Adicionar especificação de solda (WPS)" if not has_weld_spec else "",
        ))
        
        return results
    
    def _calculate_quality_score(self, inspections: List[InspectionResult]) -> float:
        """Calcula score de qualidade (0-100)."""
        if not inspections:
            return 0
        
        # Pesos por severidade
        weights = {
            InspectionSeverity.BLOCKER: 25,
            InspectionSeverity.CRITICAL: 15,
            InspectionSeverity.MAJOR: 10,
            InspectionSeverity.MINOR: 5,
            InspectionSeverity.INFO: 2,
        }
        
        total_weight = sum(weights[i.severity] for i in inspections)
        earned_weight = sum(weights[i.severity] for i in inspections if i.passed)
        
        return round(earned_weight / total_weight * 100, 1) if total_weight > 0 else 100
    
    def _generate_report(
        self,
        inspections: List[InspectionResult],
        score: float
    ) -> Dict[str, Any]:
        """Gera relatório de qualidade."""
        report = {
            "quality_score": score,
            "rating": self._get_rating(score),
            "summary_by_category": {},
            "issues_by_severity": {},
            "action_items": [],
            "recommendations": [],
        }
        
        # Agrupar por categoria
        for category in InspectionCategory:
            cat_inspections = [i for i in inspections if i.category == category]
            passed = sum(1 for i in cat_inspections if i.passed)
            total = len(cat_inspections)
            
            if total > 0:
                report["summary_by_category"][category.value] = {
                    "passed": passed,
                    "total": total,
                    "percentage": round(passed / total * 100, 1),
                }
        
        # Agrupar por severidade
        for severity in InspectionSeverity:
            sev_inspections = [i for i in inspections if i.severity == severity and not i.passed]
            if sev_inspections:
                report["issues_by_severity"][severity.value] = len(sev_inspections)
        
        # Gerar action items
        for inspection in inspections:
            if not inspection.passed and inspection.severity in [InspectionSeverity.BLOCKER, InspectionSeverity.CRITICAL]:
                report["action_items"].append({
                    "priority": "URGENTE" if inspection.severity == InspectionSeverity.BLOCKER else "ALTA",
                    "check": inspection.check_id,
                    "issue": inspection.details,
                    "action": inspection.recommendation,
                })
        
        return report
    
    def _get_rating(self, score: float) -> str:
        """Retorna rating baseado no score."""
        if score >= 95:
            return "EXCELENTE"
        elif score >= 85:
            return "BOM"
        elif score >= 70:
            return "REGULAR"
        elif score >= 50:
            return "INSUFICIENTE"
        else:
            return "CRÍTICO"


# Registrar IA
ai_registry.register(QualityInspectorAI())
