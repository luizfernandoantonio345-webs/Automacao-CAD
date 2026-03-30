from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    def to_dict(self) -> dict[str, float]:
        return {
            "min_x": round(self.min_x, 3),
            "min_y": round(self.min_y, 3),
            "min_z": round(self.min_z, 3),
            "max_x": round(self.max_x, 3),
            "max_y": round(self.max_y, 3),
            "max_z": round(self.max_z, 3),
        }


class BasePetrobrasGenerator:
    """Core universal para geração multidisciplinar com AABB e interferência."""

    disciplina: str = "universal"

    @staticmethod
    def compute_bounding_box(origin: dict[str, float], size: dict[str, float]) -> BoundingBox:
        x, y, z = float(origin.get("x", 0.0)), float(origin.get("y", 0.0)), float(origin.get("z", 0.0))
        dx, dy, dz = float(size.get("dx", 0.0)), float(size.get("dy", 0.0)), float(size.get("dz", 0.0))
        return BoundingBox(
            min_x=x,
            min_y=y,
            min_z=z,
            max_x=x + dx,
            max_y=y + dy,
            max_z=z + dz,
        )

    @staticmethod
    def _aabb_intersects(a: BoundingBox, b: BoundingBox, clearance_mm: float = 0.0) -> bool:
        c = float(clearance_mm)
        return not (
            a.max_x + c < b.min_x or
            b.max_x + c < a.min_x or
            a.max_y + c < b.min_y or
            b.max_y + c < a.min_y or
            a.max_z + c < b.min_z or
            b.max_z + c < a.min_z
        )

    def detect_interferences(
        self,
        components: list[dict[str, Any]],
        clearance_mm: float = 0.0,
    ) -> dict[str, Any]:
        bboxes: list[dict[str, Any]] = []
        interferences: list[dict[str, Any]] = []

        for comp in components:
            comp_id = str(comp.get("id", f"C-{len(bboxes)+1}"))
            bbox = self.compute_bounding_box(comp.get("origin", {}), comp.get("size", {}))
            bboxes.append({"id": comp_id, "bbox": bbox, "raw": comp})

        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                a = bboxes[i]
                b = bboxes[j]
                if self._aabb_intersects(a["bbox"], b["bbox"], clearance_mm=clearance_mm):
                    interferences.append(
                        {
                            "component_a": a["id"],
                            "component_b": b["id"],
                            "bbox_a": a["bbox"].to_dict(),
                            "bbox_b": b["bbox"].to_dict(),
                            "clearance_mm": float(clearance_mm),
                        }
                    )

        return {
            "disciplina": self.disciplina,
            "components": [
                {
                    "id": item["id"],
                    "bbox": item["bbox"].to_dict(),
                }
                for item in bboxes
            ],
            "interferences": interferences,
            "has_interference": len(interferences) > 0,
            "count": len(interferences),
        }
