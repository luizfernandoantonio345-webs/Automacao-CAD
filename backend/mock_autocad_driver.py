# ═══════════════════════════════════════════════════════════════════════════════
# MOCK AUTOCAD DRIVER - DESENVOLVIMENTO SEM AUTOCAD
# ═══════════════════════════════════════════════════════════════════════════════
"""
Mock do driver AutoCAD para desenvolvimento e testes.

Este mock simula todas as operações do AutoCAD sem precisar do software instalado.
Útil para:
- Desenvolvimento frontend sem AutoCAD
- Testes automatizados
- CI/CD pipelines
- Demonstrações

Uso:
    # Definir variável de ambiente
    export MOCK_AUTOCAD=1
    
    # Ou via código
    from backend.mock_autocad_driver import MockAutoCADDriver
    driver = MockAutoCADDriver()
"""
from __future__ import annotations

import os
import time
import json
import random
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, UTC

logger = logging.getLogger("engcad.mock_autocad")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTIDADES SIMULADAS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MockEntity:
    """Entidade CAD simulada."""
    id: str
    type: str
    layer: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


@dataclass
class MockLayer:
    """Layer simulada."""
    name: str
    color: int = 7  # Branco
    linetype: str = "Continuous"
    visible: bool = True
    locked: bool = False


@dataclass
class MockDrawing:
    """Desenho simulado."""
    filename: str = "untitled.dwg"
    path: Optional[str] = None
    entities: List[MockEntity] = field(default_factory=list)
    layers: Dict[str, MockLayer] = field(default_factory=dict)
    modified: bool = False
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        # Criar layer 0 padrão
        if "0" not in self.layers:
            self.layers["0"] = MockLayer(name="0")


# ═══════════════════════════════════════════════════════════════════════════════
# MOCK DRIVER
# ═══════════════════════════════════════════════════════════════════════════════

class MockAutoCADDriver:
    """
    Driver mock que simula todas as operações do AutoCAD.
    
    Mantém estado interno para simular um documento CAD.
    """
    
    def __init__(self, simulate_delay: bool = True, fail_rate: float = 0.0):
        """
        Args:
            simulate_delay: Se deve simular delays de operações reais
            fail_rate: Taxa de falha simulada (0.0 a 1.0)
        """
        self.simulate_delay = simulate_delay
        self.fail_rate = fail_rate
        self._connected = False
        self._drawing: Optional[MockDrawing] = None
        self._command_buffer: List[str] = []
        self._entity_counter = 0
        
        logger.info("MockAutoCADDriver inicializado (delay=%s, fail_rate=%s)", 
                    simulate_delay, fail_rate)
    
    def _delay(self, min_ms: int = 10, max_ms: int = 100):
        """Simula delay de operação."""
        if self.simulate_delay:
            delay = random.uniform(min_ms / 1000, max_ms / 1000)
            time.sleep(delay)
    
    def _maybe_fail(self, operation: str):
        """Simula falha aleatória."""
        if random.random() < self.fail_rate:
            raise Exception(f"Falha simulada em {operation}")
    
    def _next_entity_id(self) -> str:
        """Gera próximo ID de entidade."""
        self._entity_counter += 1
        return f"MOCK_{self._entity_counter:06d}"
    
    # ─── Conexão ─────────────────────────────────────────────────────────────
    
    def connect(self) -> Dict[str, Any]:
        """Simula conexão com AutoCAD."""
        self._delay(50, 200)
        self._maybe_fail("connect")
        
        self._connected = True
        self._drawing = MockDrawing()
        
        logger.info("Mock: Conectado ao AutoCAD simulado")
        return {
            "success": True,
            "message": "Conectado ao AutoCAD (MOCK)",
            "version": "AutoCAD 2024 (Mock)",
            "mock": True
        }
    
    def disconnect(self) -> Dict[str, Any]:
        """Simula desconexão."""
        self._delay(10, 50)
        
        self._connected = False
        self._drawing = None
        
        return {"success": True, "message": "Desconectado"}
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status da conexão."""
        return {
            "connected": self._connected,
            "mock": True,
            "drawing": self._drawing.filename if self._drawing else None,
            "entity_count": len(self._drawing.entities) if self._drawing else 0,
            "layer_count": len(self._drawing.layers) if self._drawing else 0,
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica saúde da conexão."""
        return {
            "healthy": True,
            "mock": True,
            "message": "AutoCAD Mock funcionando normalmente"
        }
    
    # ─── Desenho ─────────────────────────────────────────────────────────────
    
    def draw_line(
        self,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        layer: str = "0"
    ) -> Dict[str, Any]:
        """Simula desenho de linha."""
        self._delay(5, 30)
        self._maybe_fail("draw_line")
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="LINE",
            layer=layer,
            properties={
                "start": start_point,
                "end": end_point,
                "length": ((end_point[0] - start_point[0])**2 + 
                          (end_point[1] - start_point[1])**2 + 
                          (end_point[2] - start_point[2])**2) ** 0.5
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "LINE",
            "length": entity.properties["length"]
        }
    
    def draw_pipe(
        self,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        diameter: float,
        layer: str = "PIPE"
    ) -> Dict[str, Any]:
        """Simula desenho de tubulação."""
        self._delay(10, 50)
        self._maybe_fail("draw_pipe")
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        # Criar layer se não existir
        self._ensure_layer(layer, color=6)  # Magenta para pipes
        
        length = ((end_point[0] - start_point[0])**2 + 
                  (end_point[1] - start_point[1])**2 + 
                  (end_point[2] - start_point[2])**2) ** 0.5
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="PIPE",
            layer=layer,
            properties={
                "start": start_point,
                "end": end_point,
                "diameter": diameter,
                "length": length,
                "volume": 3.14159 * (diameter/2)**2 * length
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "PIPE",
            "diameter": diameter,
            "length": length
        }
    
    def draw_circle(
        self,
        center: Tuple[float, float, float],
        radius: float,
        layer: str = "0"
    ) -> Dict[str, Any]:
        """Simula desenho de círculo."""
        self._delay(5, 30)
        self._maybe_fail("draw_circle")
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="CIRCLE",
            layer=layer,
            properties={
                "center": center,
                "radius": radius,
                "area": 3.14159 * radius**2,
                "circumference": 2 * 3.14159 * radius
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "CIRCLE",
            "radius": radius
        }
    
    def draw_arc(
        self,
        center: Tuple[float, float, float],
        radius: float,
        start_angle: float,
        end_angle: float,
        layer: str = "0"
    ) -> Dict[str, Any]:
        """Simula desenho de arco."""
        self._delay(5, 30)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        sweep_angle = end_angle - start_angle
        arc_length = abs(sweep_angle) * 3.14159 / 180 * radius
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="ARC",
            layer=layer,
            properties={
                "center": center,
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "arc_length": arc_length
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "ARC",
            "arc_length": arc_length
        }
    
    def draw_polyline(
        self,
        points: List[Tuple[float, float, float]],
        closed: bool = False,
        layer: str = "0"
    ) -> Dict[str, Any]:
        """Simula desenho de polyline."""
        self._delay(10, 50)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        # Calcular comprimento total
        total_length = 0
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            total_length += ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2) ** 0.5
        
        if closed and len(points) > 2:
            p1, p2 = points[-1], points[0]
            total_length += ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2) ** 0.5
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="POLYLINE",
            layer=layer,
            properties={
                "points": points,
                "closed": closed,
                "vertex_count": len(points),
                "total_length": total_length
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "POLYLINE",
            "vertex_count": len(points),
            "total_length": total_length
        }
    
    def insert_component(
        self,
        block_name: str,
        position: Tuple[float, float, float],
        rotation: float = 0,
        scale: float = 1.0,
        layer: str = "0"
    ) -> Dict[str, Any]:
        """Simula inserção de componente/bloco."""
        self._delay(20, 100)
        self._maybe_fail("insert_component")
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="INSERT",
            layer=layer,
            properties={
                "block_name": block_name,
                "position": position,
                "rotation": rotation,
                "scale": scale
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "INSERT",
            "block_name": block_name
        }
    
    def add_text(
        self,
        text: str,
        position: Tuple[float, float, float],
        height: float = 2.5,
        rotation: float = 0,
        layer: str = "TEXT"
    ) -> Dict[str, Any]:
        """Simula adição de texto."""
        self._delay(5, 30)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        self._ensure_layer(layer, color=2)  # Yellow para texto
        
        entity = MockEntity(
            id=self._next_entity_id(),
            type="TEXT",
            layer=layer,
            properties={
                "text": text,
                "position": position,
                "height": height,
                "rotation": rotation
            }
        )
        
        self._drawing.entities.append(entity)
        self._drawing.modified = True
        
        return {
            "success": True,
            "entity_id": entity.id,
            "type": "TEXT",
            "text": text
        }
    
    # ─── Layers ──────────────────────────────────────────────────────────────
    
    def _ensure_layer(self, name: str, color: int = 7):
        """Garante que layer existe."""
        if self._drawing and name not in self._drawing.layers:
            self._drawing.layers[name] = MockLayer(name=name, color=color)
    
    def create_layer(
        self,
        name: str,
        color: int = 7,
        linetype: str = "Continuous"
    ) -> Dict[str, Any]:
        """Simula criação de layer."""
        self._delay(5, 20)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        self._drawing.layers[name] = MockLayer(
            name=name,
            color=color,
            linetype=linetype
        )
        
        return {
            "success": True,
            "layer": name,
            "color": color
        }
    
    def create_layers(self, layers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Cria múltiplas layers."""
        self._delay(10, 50)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        created = []
        for layer_def in layers:
            name = layer_def.get("name", "Layer")
            color = layer_def.get("color", 7)
            linetype = layer_def.get("linetype", "Continuous")
            
            self._drawing.layers[name] = MockLayer(
                name=name,
                color=color,
                linetype=linetype
            )
            created.append(name)
        
        return {
            "success": True,
            "created": created,
            "count": len(created)
        }
    
    def get_layers(self) -> Dict[str, Any]:
        """Lista todas as layers."""
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        return {
            "success": True,
            "layers": [
                {
                    "name": l.name,
                    "color": l.color,
                    "linetype": l.linetype,
                    "visible": l.visible
                }
                for l in self._drawing.layers.values()
            ]
        }
    
    # ─── Comandos ────────────────────────────────────────────────────────────
    
    def send_command(self, command: str) -> Dict[str, Any]:
        """Simula envio de comando AutoCAD."""
        self._delay(5, 30)
        
        self._command_buffer.append({
            "command": command,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "command": command,
            "mock": True
        }
    
    def get_buffer(self) -> Dict[str, Any]:
        """Retorna buffer de comandos."""
        return {
            "commands": self._command_buffer.copy(),
            "count": len(self._command_buffer)
        }
    
    def clear_buffer(self) -> Dict[str, Any]:
        """Limpa buffer de comandos."""
        count = len(self._command_buffer)
        self._command_buffer.clear()
        return {"success": True, "cleared": count}
    
    def commit(self) -> Dict[str, Any]:
        """Simula commit de comandos."""
        self._delay(20, 100)
        
        count = len(self._command_buffer)
        self._command_buffer.clear()
        
        return {
            "success": True,
            "committed": count,
            "mock": True
        }
    
    # ─── Arquivo ─────────────────────────────────────────────────────────────
    
    def save(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Simula salvar desenho."""
        self._delay(100, 500)
        self._maybe_fail("save")
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        save_path = path or self._drawing.path or f"/tmp/mock_{int(time.time())}.dwg"
        self._drawing.path = save_path
        self._drawing.modified = False
        
        # Simular criação de arquivo (apenas log)
        logger.info("Mock: Salvando em %s (%d entidades)", 
                    save_path, len(self._drawing.entities))
        
        return {
            "success": True,
            "path": save_path,
            "entity_count": len(self._drawing.entities),
            "mock": True
        }
    
    def finalize(self) -> Dict[str, Any]:
        """Finaliza desenho."""
        self._delay(50, 200)
        
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        result = {
            "success": True,
            "entity_count": len(self._drawing.entities),
            "layer_count": len(self._drawing.layers),
            "modified": self._drawing.modified,
            "mock": True
        }
        
        return result
    
    # ─── Batch ───────────────────────────────────────────────────────────────
    
    def batch_draw(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executa múltiplas operações de desenho."""
        self._delay(50, 200)
        
        results = []
        for op in operations:
            op_type = op.get("type", "").upper()
            
            try:
                if op_type == "LINE":
                    result = self.draw_line(
                        tuple(op.get("start", [0, 0, 0])),
                        tuple(op.get("end", [0, 0, 0])),
                        op.get("layer", "0")
                    )
                elif op_type == "PIPE":
                    result = self.draw_pipe(
                        tuple(op.get("start", [0, 0, 0])),
                        tuple(op.get("end", [0, 0, 0])),
                        op.get("diameter", 50),
                        op.get("layer", "PIPE")
                    )
                elif op_type == "CIRCLE":
                    result = self.draw_circle(
                        tuple(op.get("center", [0, 0, 0])),
                        op.get("radius", 10),
                        op.get("layer", "0")
                    )
                elif op_type == "TEXT":
                    result = self.add_text(
                        op.get("text", ""),
                        tuple(op.get("position", [0, 0, 0])),
                        op.get("height", 2.5),
                        op.get("rotation", 0),
                        op.get("layer", "TEXT")
                    )
                elif op_type == "INSERT":
                    result = self.insert_component(
                        op.get("block_name", "BLOCK"),
                        tuple(op.get("position", [0, 0, 0])),
                        op.get("rotation", 0),
                        op.get("scale", 1.0),
                        op.get("layer", "0")
                    )
                else:
                    result = {"success": False, "error": f"Tipo desconhecido: {op_type}"}
                
                results.append(result)
                
            except Exception as e:
                results.append({"success": False, "error": str(e)})
        
        success_count = sum(1 for r in results if r.get("success"))
        
        return {
            "success": success_count == len(operations),
            "total": len(operations),
            "success_count": success_count,
            "failed_count": len(operations) - success_count,
            "results": results
        }
    
    # ─── Exportação ──────────────────────────────────────────────────────────
    
    def export_to_json(self) -> Dict[str, Any]:
        """Exporta desenho para JSON (útil para debug)."""
        if not self._drawing:
            return {"success": False, "error": "Nenhum desenho aberto"}
        
        return {
            "success": True,
            "drawing": {
                "filename": self._drawing.filename,
                "path": self._drawing.path,
                "created_at": self._drawing.created_at,
                "entity_count": len(self._drawing.entities),
                "entities": [
                    {
                        "id": e.id,
                        "type": e.type,
                        "layer": e.layer,
                        "properties": e.properties
                    }
                    for e in self._drawing.entities
                ],
                "layers": [
                    {
                        "name": l.name,
                        "color": l.color,
                        "linetype": l.linetype
                    }
                    for l in self._drawing.layers.values()
                ]
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY PARA ESCOLHER DRIVER
# ═══════════════════════════════════════════════════════════════════════════════

def get_autocad_driver(force_mock: bool = False):
    """
    Retorna o driver AutoCAD apropriado.
    
    Args:
        force_mock: Se True, sempre retorna mock
        
    Returns:
        MockAutoCADDriver ou AutoCADDriver real
    """
    use_mock = force_mock or os.getenv("MOCK_AUTOCAD", "").lower() in ("1", "true", "yes")
    
    if use_mock:
        logger.info("Usando MockAutoCADDriver")
        return MockAutoCADDriver()
    
    try:
        from backend.autocad_driver import AutoCADDriver
        logger.info("Usando AutoCADDriver real")
        return AutoCADDriver()
    except Exception as e:
        logger.warning("AutoCAD não disponível (%s), usando mock", e)
        return MockAutoCADDriver()


# ═══════════════════════════════════════════════════════════════════════════════
# TESTE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    driver = MockAutoCADDriver(simulate_delay=False)
    
    # Teste de conexão
    print("Conectando...")
    print(driver.connect())
    
    # Criar layers
    print("\nCriando layers...")
    print(driver.create_layers([
        {"name": "PIPE", "color": 6},
        {"name": "VALVE", "color": 1},
        {"name": "TEXT", "color": 2}
    ]))
    
    # Desenhar
    print("\nDesenhando...")
    print(driver.draw_pipe((0, 0, 0), (1000, 0, 0), 50, "PIPE"))
    print(driver.draw_pipe((1000, 0, 0), (1000, 500, 0), 50, "PIPE"))
    print(driver.insert_component("VALVE_GATE", (1000, 0, 0), layer="VALVE"))
    print(driver.add_text("TAG-001", (500, 50, 0), height=25, layer="TEXT"))
    
    # Status
    print("\nStatus:")
    print(json.dumps(driver.get_status(), indent=2))
    
    # Exportar
    print("\nExportando para JSON:")
    export = driver.export_to_json()
    print(f"Entidades: {export['drawing']['entity_count']}")
    
    # Salvar
    print("\nSalvando...")
    print(driver.save("/tmp/test_mock.dwg"))
