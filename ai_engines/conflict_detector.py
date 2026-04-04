"""
═══════════════════════════════════════════════════════════════════════════════
  CONFLICT DETECTOR AI - Detecção Inteligente de Conflitos e Colisões
═══════════════════════════════════════════════════════════════════════════════

Esta IA é especializada em:
  - Detecção de colisões entre tubulações
  - Identificação de interferências estruturais
  - Verificação de espaçamentos mínimos
  - Análise de cruzamentos inválidos
  - Validação de clearances de manutenção

═══════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseAI, AIResult, ai_registry

logger = logging.getLogger(__name__)


@dataclass
class BoundingBox:
    """Caixa delimitadora 3D."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float
    
    def intersects(self, other: 'BoundingBox', margin: float = 0) -> bool:
        """Verifica se duas bounding boxes se intersectam."""
        return (
            self.min_x - margin <= other.max_x + margin and
            self.max_x + margin >= other.min_x - margin and
            self.min_y - margin <= other.max_y + margin and
            self.max_y + margin >= other.min_y - margin and
            self.min_z - margin <= other.max_z + margin and
            self.max_z + margin >= other.min_z - margin
        )
    
    def expanded(self, margin: float) -> 'BoundingBox':
        """Retorna bbox expandida pela margem."""
        return BoundingBox(
            self.min_x - margin, self.min_y - margin, self.min_z - margin,
            self.max_x + margin, self.max_y + margin, self.max_z + margin
        )


@dataclass  
class ConflictResult:
    """Resultado de detecção de conflito."""
    type: str  # "collision", "clearance", "crossing", "spacing"
    severity: str  # "critical", "warning", "info"
    object1_id: str
    object2_id: str
    location: Tuple[float, float, float]
    distance: float
    required_distance: float
    description: str
    suggested_resolution: str


class ConflictDetectorAI(BaseAI):
    """
    IA especializada em detecção de conflitos.
    
    Capacidades:
    - Detecção de colisões entre objetos
    - Verificação de clearances mínimos
    - Análise de cruzamentos de tubulação
    - Validação de espaçamentos
    - Detecção de interferências estruturais
    """
    
    # Distâncias mínimas por tipo (em mm)
    MIN_CLEARANCES = {
        "pipe_to_pipe": 50,
        "pipe_to_structure": 100,
        "pipe_to_equipment": 150,
        "valve_access": 300,
        "maintenance_access": 600,
        "hot_pipe_to_cold": 200,
        "electrical_clearance": 300,
    }
    
    # Severidades
    SEVERITY_LEVELS = {
        "collision": "critical",
        "clearance_violation": "warning",
        "crossing_issue": "warning",
        "spacing_issue": "info",
    }
    
    def __init__(self):
        super().__init__(name="ConflictDetector", version="1.0.0")
        self.confidence_threshold = 0.8
    
    def get_capabilities(self) -> List[str]:
        return [
            "collision_detection",
            "clearance_validation",
            "crossing_analysis",
            "spacing_verification",
            "structural_interference",
            "maintenance_access_check",
            "clash_report_generation",
        ]
    
    async def process(self, input_data: Dict[str, Any]) -> AIResult:
        """
        Processa dados para detecção de conflitos.
        
        Input esperado:
        {
            "objects": [...],         # Lista de objetos a verificar
            "structures": [...],      # Estruturas fixas
            "check_types": [...],     # Tipos de verificação
            "custom_clearances": {},  # Clearances customizados
        }
        """
        objects = input_data.get("objects", [])
        structures = input_data.get("structures", [])
        check_types = input_data.get("check_types", ["all"])
        custom_clearances = input_data.get("custom_clearances", {})
        
        # Merge clearances
        clearances = {**self.MIN_CLEARANCES, **custom_clearances}
        
        conflicts: List[ConflictResult] = []
        warnings = []
        
        try:
            # 1. Detecção de colisões diretas
            if "all" in check_types or "collision" in check_types:
                collisions = self._detect_collisions(objects)
                conflicts.extend(collisions)
            
            # 2. Verificação de clearances
            if "all" in check_types or "clearance" in check_types:
                clearance_issues = self._check_clearances(objects, clearances)
                conflicts.extend(clearance_issues)
            
            # 3. Análise de cruzamentos
            if "all" in check_types or "crossing" in check_types:
                crossing_issues = self._analyze_crossings(objects)
                conflicts.extend(crossing_issues)
            
            # 4. Verificação com estruturas
            if "all" in check_types or "structure" in check_types:
                structure_conflicts = self._check_structure_interference(objects, structures)
                conflicts.extend(structure_conflicts)
            
            # 5. Verificação de acesso para manutenção
            if "all" in check_types or "maintenance" in check_types:
                access_issues = self._check_maintenance_access(objects, clearances)
                conflicts.extend(access_issues)
            
            # Classificar por severidade
            critical = [c for c in conflicts if c.severity == "critical"]
            warning = [c for c in conflicts if c.severity == "warning"]
            info = [c for c in conflicts if c.severity == "info"]
            
            # Gerar relatório
            report = self._generate_clash_report(conflicts)
            
            # Calcular confiança
            confidence = 0.95 if objects else 0.5
            
            return AIResult(
                success=True,
                ai_name=self.name,
                operation="conflict_detection",
                data={
                    "summary": {
                        "total_conflicts": len(conflicts),
                        "critical": len(critical),
                        "warnings": len(warning),
                        "info": len(info),
                        "objects_analyzed": len(objects),
                    },
                    "conflicts": [self._conflict_to_dict(c) for c in conflicts],
                    "report": report,
                    "status": (
                        "CRITICAL - Ação imediata necessária" if critical else
                        "WARNING - Revisão recomendada" if warning else
                        "OK - Nenhum conflito crítico"
                    ),
                },
                confidence=confidence,
                warnings=warnings,
                metadata={
                    "check_types": check_types,
                    "clearances_used": clearances,
                }
            )
            
        except Exception as e:
            logger.exception(f"[{self.name}] Erro na detecção")
            return AIResult(
                success=False,
                ai_name=self.name,
                operation="conflict_detection",
                data={},
                errors=[str(e)],
            )
    
    def _conflict_to_dict(self, conflict: ConflictResult) -> Dict:
        """Converte ConflictResult para dict."""
        return {
            "type": conflict.type,
            "severity": conflict.severity,
            "object1_id": conflict.object1_id,
            "object2_id": conflict.object2_id,
            "location": conflict.location,
            "distance": conflict.distance,
            "required_distance": conflict.required_distance,
            "description": conflict.description,
            "suggested_resolution": conflict.suggested_resolution,
        }
    
    def _get_bounding_box(self, obj: Dict) -> Optional[BoundingBox]:
        """Extrai bounding box de um objeto."""
        if "bounding_box" in obj:
            bb = obj["bounding_box"]
            return BoundingBox(
                bb.get("min_x", 0), bb.get("min_y", 0), bb.get("min_z", 0),
                bb.get("max_x", 0), bb.get("max_y", 0), bb.get("max_z", 0)
            )
        
        # Calcular a partir de coordenadas
        if "start" in obj and "end" in obj:
            s, e = obj["start"], obj["end"]
            radius = obj.get("diameter", 100) / 2
            return BoundingBox(
                min(s.get("x", 0), e.get("x", 0)) - radius,
                min(s.get("y", 0), e.get("y", 0)) - radius,
                min(s.get("z", 0), e.get("z", 0)) - radius,
                max(s.get("x", 0), e.get("x", 0)) + radius,
                max(s.get("y", 0), e.get("y", 0)) + radius,
                max(s.get("z", 0), e.get("z", 0)) + radius,
            )
        
        return None
    
    def _detect_collisions(self, objects: List[Dict]) -> List[ConflictResult]:
        """Detecta colisões diretas entre objetos."""
        conflicts = []
        
        for i, obj1 in enumerate(objects):
            bb1 = self._get_bounding_box(obj1)
            if not bb1:
                continue
            
            for j, obj2 in enumerate(objects[i+1:], i+1):
                bb2 = self._get_bounding_box(obj2)
                if not bb2:
                    continue
                
                if bb1.intersects(bb2):
                    # Calcular ponto de interseção aproximado
                    center = (
                        (bb1.min_x + bb1.max_x + bb2.min_x + bb2.max_x) / 4,
                        (bb1.min_y + bb1.max_y + bb2.min_y + bb2.max_y) / 4,
                        (bb1.min_z + bb1.max_z + bb2.min_z + bb2.max_z) / 4,
                    )
                    
                    conflicts.append(ConflictResult(
                        type="collision",
                        severity="critical",
                        object1_id=obj1.get("id", f"obj_{i}"),
                        object2_id=obj2.get("id", f"obj_{j}"),
                        location=center,
                        distance=0,
                        required_distance=self.MIN_CLEARANCES["pipe_to_pipe"],
                        description=f"Colisão detectada entre {obj1.get('type', 'objeto')} e {obj2.get('type', 'objeto')}",
                        suggested_resolution="Rerotar um dos objetos ou ajustar elevação",
                    ))
        
        return conflicts
    
    def _check_clearances(
        self,
        objects: List[Dict],
        clearances: Dict[str, float]
    ) -> List[ConflictResult]:
        """Verifica clearances mínimos entre objetos."""
        conflicts = []
        min_clearance = clearances.get("pipe_to_pipe", 50)
        
        for i, obj1 in enumerate(objects):
            bb1 = self._get_bounding_box(obj1)
            if not bb1:
                continue
            
            expanded_bb1 = bb1.expanded(min_clearance)
            
            for j, obj2 in enumerate(objects[i+1:], i+1):
                bb2 = self._get_bounding_box(obj2)
                if not bb2:
                    continue
                
                # Se bboxes expandidas se intersectam mas originais não
                if expanded_bb1.intersects(bb2) and not bb1.intersects(bb2):
                    # Calcular distância aproximada
                    distance = self._calculate_min_distance(bb1, bb2)
                    
                    if distance < min_clearance:
                        center = (
                            (bb1.min_x + bb1.max_x + bb2.min_x + bb2.max_x) / 4,
                            (bb1.min_y + bb1.max_y + bb2.min_y + bb2.max_y) / 4,
                            (bb1.min_z + bb1.max_z + bb2.min_z + bb2.max_z) / 4,
                        )
                        
                        conflicts.append(ConflictResult(
                            type="clearance_violation",
                            severity="warning",
                            object1_id=obj1.get("id", f"obj_{i}"),
                            object2_id=obj2.get("id", f"obj_{j}"),
                            location=center,
                            distance=distance,
                            required_distance=min_clearance,
                            description=f"Clearance insuficiente: {distance:.1f}mm (mínimo: {min_clearance}mm)",
                            suggested_resolution="Aumentar espaçamento entre objetos",
                        ))
        
        return conflicts
    
    def _calculate_min_distance(self, bb1: BoundingBox, bb2: BoundingBox) -> float:
        """Calcula distância mínima aproximada entre duas bounding boxes."""
        dx = max(0, max(bb1.min_x - bb2.max_x, bb2.min_x - bb1.max_x))
        dy = max(0, max(bb1.min_y - bb2.max_y, bb2.min_y - bb1.max_y))
        dz = max(0, max(bb1.min_z - bb2.max_z, bb2.min_z - bb1.max_z))
        return math.sqrt(dx**2 + dy**2 + dz**2)
    
    def _analyze_crossings(self, objects: List[Dict]) -> List[ConflictResult]:
        """Analisa cruzamentos de tubulações."""
        conflicts = []
        
        # Filtrar apenas tubos
        pipes = [obj for obj in objects if obj.get("type") == "pipe"]
        
        for i, pipe1 in enumerate(pipes):
            for j, pipe2 in enumerate(pipes[i+1:], i+1):
                # Verificar se há cruzamento
                crossing = self._check_pipe_crossing(pipe1, pipe2)
                
                if crossing:
                    conflicts.append(ConflictResult(
                        type="crossing_issue",
                        severity="warning",
                        object1_id=pipe1.get("id", f"pipe_{i}"),
                        object2_id=pipe2.get("id", f"pipe_{j}"),
                        location=crossing["location"],
                        distance=crossing["clearance"],
                        required_distance=self.MIN_CLEARANCES["pipe_to_pipe"],
                        description=f"Cruzamento de tubulações detectado",
                        suggested_resolution="Verificar elevações e adicionar suportes se necessário",
                    ))
        
        return conflicts
    
    def _check_pipe_crossing(self, pipe1: Dict, pipe2: Dict) -> Optional[Dict]:
        """Verifica se dois tubos se cruzam."""
        # Simplificado - em produção usaria geometria 3D completa
        start1 = pipe1.get("start", {})
        end1 = pipe1.get("end", {})
        start2 = pipe2.get("start", {})
        end2 = pipe2.get("end", {})
        
        # Verificar se estão no mesmo plano Z aproximado
        z1_avg = (start1.get("z", 0) + end1.get("z", 0)) / 2
        z2_avg = (start2.get("z", 0) + end2.get("z", 0)) / 2
        
        if abs(z1_avg - z2_avg) < 100:  # Mesmo nível (±100mm)
            # Verificar interseção em XY
            # (Simplificado)
            return None
        
        return None
    
    def _check_structure_interference(
        self,
        objects: List[Dict],
        structures: List[Dict]
    ) -> List[ConflictResult]:
        """Verifica interferência com estruturas."""
        conflicts = []
        
        for obj in objects:
            bb_obj = self._get_bounding_box(obj)
            if not bb_obj:
                continue
            
            for struct in structures:
                bb_struct = self._get_bounding_box(struct)
                if not bb_struct:
                    continue
                
                min_clearance = self.MIN_CLEARANCES.get("pipe_to_structure", 100)
                expanded = bb_obj.expanded(min_clearance)
                
                if expanded.intersects(bb_struct):
                    distance = self._calculate_min_distance(bb_obj, bb_struct)
                    
                    if distance < min_clearance:
                        conflicts.append(ConflictResult(
                            type="structural_interference",
                            severity="critical" if distance == 0 else "warning",
                            object1_id=obj.get("id", "unknown"),
                            object2_id=struct.get("id", "structure"),
                            location=(
                                (bb_obj.min_x + bb_obj.max_x) / 2,
                                (bb_obj.min_y + bb_obj.max_y) / 2,
                                (bb_obj.min_z + bb_obj.max_z) / 2,
                            ),
                            distance=distance,
                            required_distance=min_clearance,
                            description=f"Interferência com estrutura: {struct.get('type', 'estrutura')}",
                            suggested_resolution="Rerotar tubulação ou adicionar passagem na estrutura",
                        ))
        
        return conflicts
    
    def _check_maintenance_access(
        self,
        objects: List[Dict],
        clearances: Dict[str, float]
    ) -> List[ConflictResult]:
        """Verifica espaço para acesso de manutenção."""
        conflicts = []
        maintenance_clearance = clearances.get("maintenance_access", 600)
        
        # Identificar válvulas e equipamentos que precisam de acesso
        maintainable = [
            obj for obj in objects 
            if obj.get("type") in ["valve", "pump", "instrument", "heat_exchanger"]
        ]
        
        for item in maintainable:
            bb = self._get_bounding_box(item)
            if not bb:
                continue
            
            # Verificar se há espaço suficiente ao redor
            expanded = bb.expanded(maintenance_clearance)
            
            obstructions = []
            for obj in objects:
                if obj.get("id") == item.get("id"):
                    continue
                
                obj_bb = self._get_bounding_box(obj)
                if obj_bb and expanded.intersects(obj_bb):
                    obstructions.append(obj)
            
            if obstructions:
                conflicts.append(ConflictResult(
                    type="maintenance_access",
                    severity="info",
                    object1_id=item.get("id", "unknown"),
                    object2_id=", ".join(o.get("id", "obj") for o in obstructions[:3]),
                    location=(
                        (bb.min_x + bb.max_x) / 2,
                        (bb.min_y + bb.max_y) / 2,
                        (bb.min_z + bb.max_z) / 2,
                    ),
                    distance=0,
                    required_distance=maintenance_clearance,
                    description=f"Acesso para manutenção pode estar obstruído ({len(obstructions)} objetos próximos)",
                    suggested_resolution="Verificar clearance para manutenção e operação",
                ))
        
        return conflicts
    
    def _generate_clash_report(self, conflicts: List[ConflictResult]) -> Dict[str, Any]:
        """Gera relatório de clash detection."""
        report = {
            "generated_at": None,  # Será preenchido pelo timestamp do AIResult
            "summary": {
                "total": len(conflicts),
                "by_severity": {},
                "by_type": {},
            },
            "conflicts_by_area": {},
            "recommendations": [],
        }
        
        # Contar por severidade e tipo
        for conflict in conflicts:
            # Por severidade
            report["summary"]["by_severity"][conflict.severity] = (
                report["summary"]["by_severity"].get(conflict.severity, 0) + 1
            )
            # Por tipo
            report["summary"]["by_type"][conflict.type] = (
                report["summary"]["by_type"].get(conflict.type, 0) + 1
            )
            
            # Por área (simplificado)
            area_key = f"zona_{int(conflict.location[0] // 1000)}_{int(conflict.location[1] // 1000)}"
            if area_key not in report["conflicts_by_area"]:
                report["conflicts_by_area"][area_key] = []
            report["conflicts_by_area"][area_key].append(conflict.type)
        
        # Gerar recomendações
        if report["summary"]["by_severity"].get("critical", 0) > 0:
            report["recommendations"].append({
                "priority": "URGENTE",
                "action": "Resolver colisões críticas antes de prosseguir com o projeto",
            })
        
        if report["summary"]["by_type"].get("clearance_violation", 0) > 3:
            report["recommendations"].append({
                "priority": "ALTA",
                "action": "Revisar layout geral - múltiplas violações de clearance indicam problemas de espaço",
            })
        
        return report


# Registrar IA
ai_registry.register(ConflictDetectorAI())
