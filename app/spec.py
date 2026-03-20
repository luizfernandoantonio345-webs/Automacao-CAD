from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json


class SpecError(ValueError):
    """Raised when the input spec is invalid."""


@dataclass(slots=True)
class DrawingSpec:
    name: str
    units: str = "mm"
    format: str = "json"
    parameters: dict[str, Any] = field(default_factory=dict)
    elements: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class JobSpec:
    job_name: str
    output_dir: Path
    drawing: DrawingSpec
    metadata: dict[str, Any] = field(default_factory=dict)


def load_spec(path: str | Path) -> JobSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return parse_spec(raw, source=str(path))


def parse_spec(raw: dict[str, Any], *, source: str = "<memory>") -> JobSpec:
    if not isinstance(raw, dict):
        raise SpecError(f"{source}: spec must be a JSON object")

    job_name = _require_str(raw, "job_name", source)
    output_dir = Path(raw.get("output_dir", "dist"))

    drawing_raw = raw.get("drawing")
    if not isinstance(drawing_raw, dict):
        raise SpecError(f"{source}: 'drawing' must be an object")

    drawing = DrawingSpec(
        name=_require_str(drawing_raw, "name", source),
        units=str(drawing_raw.get("units", "mm")),
        format=str(drawing_raw.get("format", "json")),
        parameters=_require_dict(drawing_raw.get("parameters", {}), "drawing.parameters", source),
        elements=_require_list_of_dicts(drawing_raw.get("elements", []), "drawing.elements", source),
    )

    metadata = _require_dict(raw.get("metadata", {}), "metadata", source)
    return JobSpec(job_name=job_name, output_dir=output_dir, drawing=drawing, metadata=metadata)


def dump_normalized_spec(spec: JobSpec) -> dict[str, Any]:
    return {
        "job_name": spec.job_name,
        "output_dir": str(spec.output_dir),
        "drawing": {
            "name": spec.drawing.name,
            "units": spec.drawing.units,
            "format": spec.drawing.format,
            "parameters": spec.drawing.parameters,
            "elements": spec.drawing.elements,
        },
        "metadata": spec.metadata,
    }


def sample_spec() -> dict[str, Any]:
    return {
        "job_name": "sample-cad-job",
        "output_dir": "dist",
        "drawing": {
            "name": "sample-part",
            "units": "mm",
            "format": "json",
            "parameters": {
                "width": 120,
                "height": 80,
                "thickness": 12,
            },
            "elements": [
                {
                    "type": "rectangle",
                    "layer": "outline",
                    "x": 0,
                    "y": 0,
                    "width": 120,
                    "height": 80,
                }
            ],
        },
        "metadata": {
            "author": "app",
            "purpose": "starter spec",
        },
    }


def _require_str(payload: dict[str, Any], key: str, source: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SpecError(f"{source}: '{key}' must be a non-empty string")
    return value


def _require_dict(value: Any, key: str, source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpecError(f"{source}: '{key}' must be an object")
    return value


def _require_list_of_dicts(value: Any, key: str, source: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SpecError(f"{source}: '{key}' must be an array")
    items: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise SpecError(f"{source}: '{key}[{index}]' must be an object")
        items.append(item)
    return items
