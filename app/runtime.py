from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol
import json

from .spec import DrawingSpec, JobSpec, dump_normalized_spec


@dataclass(slots=True)
class Artifact:
    name: str
    path: Path
    kind: str = "file"


@dataclass(slots=True)
class GenerationResult:
    job_name: str
    status: str
    created_at: str
    artifacts: list[Artifact] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "job_name": self.job_name,
            "status": self.status,
            "created_at": self.created_at,
            "artifacts": [
                {"name": artifact.name, "path": str(artifact.path), "kind": artifact.kind}
                for artifact in self.artifacts
            ],
            "summary": self.summary,
        }


class CADService(Protocol):
    def generate(self, request: JobSpec, output_dir: Path) -> GenerationResult: ...


class LocalCADService:
    """Fallback service used when `core`/`cad` are not installed yet."""

    def generate(self, request: JobSpec, output_dir: Path) -> GenerationResult:
        output_dir.mkdir(parents=True, exist_ok=True)

        normalized_spec = dump_normalized_spec(request)
        drawing_path = output_dir / f"{request.drawing.name}.json"
        result_path = output_dir / "result.json"

        drawing_payload = {
            "drawing": normalized_spec["drawing"],
            "metadata": normalized_spec["metadata"],
        }
        drawing_path.write_text(json.dumps(drawing_payload, indent=2, ensure_ascii=True), encoding="utf-8")

        result = GenerationResult(
            job_name=request.job_name,
            status="completed",
            created_at=datetime.now(timezone.utc).isoformat(),
            artifacts=[Artifact(name=drawing_path.name, path=drawing_path)],
            summary={
                "engine": "local-fallback",
                "output_dir": str(output_dir),
                "element_count": len(request.drawing.elements),
                "parameter_count": len(request.drawing.parameters),
            },
        )
        result_path.write_text(json.dumps(result.to_json(), indent=2, ensure_ascii=True), encoding="utf-8")
        result.artifacts.append(Artifact(name=result_path.name, path=result_path))
        return result


def build_service() -> CADService:
    """Return the best available CAD service.

    The function prefers a real implementation from `core`/`cad` if the package
    is present. Otherwise it falls back to a local implementation that keeps
    the CLI executable while the rest of the system is being assembled.
    """

    service = _load_external_service()
    if service is not None:
        return service
    return LocalCADService()


def run_job(spec: JobSpec) -> GenerationResult:
    service = build_service()
    output_dir = spec.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    result = service.generate(spec, output_dir)
    _write_result_manifest(result, output_dir)
    return result


def write_sample_spec(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({
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
    }, indent=2, ensure_ascii=True), encoding="utf-8")
    return target


def _write_result_manifest(result: GenerationResult, output_dir: Path) -> None:
    manifest_path = output_dir / "run.manifest.json"
    manifest_path.write_text(json.dumps(result.to_json(), indent=2, ensure_ascii=True), encoding="utf-8")


def _load_external_service() -> CADService | None:
    candidates = [
        ("core.service", "GenerationService"),
        ("core.services", "GenerationService"),
        ("core", "GenerationService"),
        ("cad.service", "CADService"),
        ("cad.engine", "CADService"),
        ("cad", "CADService"),
    ]
    for module_name, attr_name in candidates:
        try:
            module = import_module(module_name)
        except Exception:
            continue
        service = getattr(module, attr_name, None)
        if service is None:
            continue
        if callable(service):
            try:
                instance = service()
            except TypeError:
                continue
            if hasattr(instance, "generate"):
                return instance  # type: ignore[return-value]
        elif hasattr(service, "generate"):
            return service  # type: ignore[return-value]
    return None
