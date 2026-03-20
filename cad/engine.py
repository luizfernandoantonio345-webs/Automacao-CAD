from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.models import Artifact, BuildResult, DrawingSpec, ShapeSpec
from core.ports import CadEngine


@dataclass(slots=True)
class _Viewport:
    width: float
    height: float
    margin: float = 16.0

    @property
    def canvas_width(self) -> float:
        return self.width + self.margin * 2

    @property
    def canvas_height(self) -> float:
        return self.height + self.margin * 2


class SvgCadEngine(CadEngine):
    """Concrete CAD engine that emits SVG plus a JSON manifest."""

    def build(self, spec: DrawingSpec, output_dir: Path) -> BuildResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        viewport = self._compute_viewport(spec)
        svg_text = self._render_svg(spec, viewport)

        svg_path = output_dir / f"{spec.name}.svg"
        manifest_path = output_dir / f"{spec.name}.manifest.json"

        svg_path.write_text(svg_text, encoding="utf-8")
        manifest_path.write_text(
            json.dumps(self._manifest(spec, svg_path), indent=2),
            encoding="utf-8",
        )

        artifacts = [
            Artifact(kind="drawing", path=svg_path, metadata={"format": "svg"}),
            Artifact(kind="manifest", path=manifest_path, metadata={"format": "json"}),
        ]
        return BuildResult(
            drawing_name=spec.name,
            output_dir=output_dir,
            artifacts=artifacts,
            summary=(
                f"Generated {len(spec.shapes)} shapes in SVG format for drawing "
                f"'{spec.name}'."
            ),
        )

    def _compute_viewport(self, spec: DrawingSpec) -> _Viewport:
        max_x = 0.0
        max_y = 0.0
        for shape in spec.shapes:
            shape_max_x, shape_max_y = self._shape_extent(shape)
            max_x = max(max_x, shape_max_x)
            max_y = max(max_y, shape_max_y)
        return _Viewport(width=max_x or 100.0, height=max_y or 100.0)

    def _shape_extent(self, shape: ShapeSpec) -> tuple[float, float]:
        x = shape.params.get("x", 0.0)
        y = shape.params.get("y", 0.0)
        if shape.kind == "rectangle":
            return x + shape.params.get("width", 0.0), y + shape.params.get("height", 0.0)
        if shape.kind == "circle":
            radius = shape.params.get("radius", 0.0)
            return x + radius, y + radius
        if shape.kind == "slot":
            return x + shape.params.get("length", 0.0), y + shape.params.get("width", 0.0)
        return x, y

    def _render_svg(self, spec: DrawingSpec, viewport: _Viewport) -> str:
        body = "\n".join(self._render_shape(shape, viewport) for shape in spec.shapes)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{viewport.canvas_width}" height="{viewport.canvas_height}" '
            f'viewBox="0 0 {viewport.canvas_width} {viewport.canvas_height}">\n'
            f'  <rect x="0" y="0" width="{viewport.canvas_width}" '
            f'height="{viewport.canvas_height}" fill="#fcfcf8" stroke="none"/>\n'
            f'  <g stroke="#112233" stroke-width="2" fill="none">\n{body}\n  </g>\n'
            f'  <text x="{viewport.margin}" y="{viewport.canvas_height - 4}" '
            f'font-size="12" fill="#445">{spec.name}</text>\n'
            "</svg>\n"
        )

    def _render_shape(self, shape: ShapeSpec, viewport: _Viewport) -> str:
        x = viewport.margin + shape.params.get("x", 0.0)
        y = viewport.margin + shape.params.get("y", 0.0)
        if shape.kind == "rectangle":
            width = shape.params["width"]
            height = shape.params["height"]
            return (
                f'    <rect x="{x}" y="{y}" width="{width}" height="{height}" '
                f'rx="{shape.params.get("corner_radius", 0)}"/>'
            )
        if shape.kind == "circle":
            return (
                f'    <circle cx="{x}" cy="{y}" r="{shape.params["radius"]}" '
                f'data-role="{shape.role}"/>'
            )
        if shape.kind == "slot":
            length = shape.params["length"]
            width = shape.params["width"]
            radius = width / 2
            return (
                "    <path d=\""
                f"M {x + radius} {y} "
                f"L {x + length - radius} {y} "
                f"A {radius} {radius} 0 0 1 {x + length - radius} {y + width} "
                f"L {x + radius} {y + width} "
                f"A {radius} {radius} 0 0 1 {x + radius} {y} Z\"/>"
            )
        raise ValueError(f"Unsupported CAD shape kind: {shape.kind}")

    def _manifest(self, spec: DrawingSpec, svg_path: Path) -> dict[str, Any]:
        return {
            "drawing_name": spec.name,
            "units": spec.units,
            "artifact": str(svg_path),
            "shape_count": len(spec.shapes),
            "shapes": [
                {
                    "id": shape.id,
                    "kind": shape.kind,
                    "role": shape.role,
                    "params": shape.params,
                }
                for shape in spec.shapes
            ],
        }
