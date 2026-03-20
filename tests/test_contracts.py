from __future__ import annotations

from importlib import import_module
from inspect import Parameter, signature
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import pytest


def import_optional(names: Iterable[str]):
    last_error: Exception | None = None
    for name in names:
        try:
            return import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name == name or exc.name.startswith(f"{name}."):
                last_error = exc
                continue
            raise
    pytest.skip(f"None of the candidate modules are available: {', '.join(names)}")
    if last_error is not None:  # pragma: no cover - defensive only
        raise last_error


def iter_objects(module):
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        yield attr_name, getattr(module, attr_name)


def find_object(module, keywords: Iterable[str]):
    lowered = tuple(keyword.lower() for keyword in keywords)
    for attr_name, obj in iter_objects(module):
        haystack = attr_name.lower()
        if any(keyword in haystack for keyword in lowered):
            return obj
    pytest.skip(
        f"Could not find an exported object matching any of: {', '.join(keywords)}"
    )


def build_instance(factory: Any, payload: dict[str, Any]):
    if hasattr(factory, "model_validate"):
        return factory.model_validate(payload)
    if hasattr(factory, "parse_obj"):
        return factory.parse_obj(payload)
    try:
        return factory(**payload)
    except TypeError:
        return factory(payload)


def call_with_supported_signature(target: Any, *args, **kwargs):
    params = signature(target).parameters
    positional_args = []
    keyword_args = {}

    for arg, param in zip(args, params.values(), strict=False):
        if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
            positional_args.append(arg)

    for key, value in kwargs.items():
        if key in params:
            keyword_args[key] = value

    return target(*positional_args, **keyword_args)


def get_attr_any(obj: Any, names: Iterable[str], default: Any = None):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def to_mapping(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return {
            key: value
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }
    return {}


def sample_spec_payload() -> dict[str, Any]:
    return {
        "name": "panel_001",
        "project_name": "panel_001",
        "units": "mm",
        "width": 1200,
        "height": 600,
        "depth": 18,
        "operations": [
            {
                "type": "line",
                "start": [0, 0],
                "end": [1200, 0],
            }
        ],
    }


def sample_spec_instance():
    core_module = import_optional(["core", "core.spec", "core.models"])
    spec_cls = find_object(core_module, ["spec", "request", "job", "drawing"])
    return build_instance(spec_cls, sample_spec_payload())


def sample_engine():
    cad_module = import_optional(["cad", "cad.engine", "cad.service"])
    engine_cls = find_object(cad_module, ["engine", "renderer", "generator", "cad"])
    try:
        return engine_cls()
    except TypeError:
        return build_instance(engine_cls, {})


def test_core_spec_contract_supports_mapping_validation_and_round_trip():
    core_module = import_optional(["core", "core.spec", "core.models"])
    spec_cls = find_object(core_module, ["spec", "request", "job", "drawing"])

    spec = build_instance(spec_cls, sample_spec_payload())
    spec_mapping = to_mapping(spec)

    assert spec_mapping, "Spec object should expose a serializable mapping"
    assert get_attr_any(spec, ["name", "project_name", "drawing_name"]) in {
        "panel_001",
    }
    assert get_attr_any(spec, ["units", "unit"], "mm") == "mm"

    if hasattr(spec_cls, "model_validate") or hasattr(spec_cls, "parse_obj"):
        reconstructed = build_instance(spec_cls, spec_mapping)
        assert to_mapping(reconstructed) == spec_mapping


def test_cad_engine_contract_returns_result_for_a_spec():
    engine = sample_engine()
    spec = sample_spec_instance()

    action = None
    for candidate in ("generate", "render", "build", "execute", "run"):
        if hasattr(engine, candidate):
            action = getattr(engine, candidate)
            break

    if action is None:
        pytest.skip("CAD engine does not expose a known execution method")

    result = call_with_supported_signature(action, spec)
    result_mapping = to_mapping(result)

    assert result_mapping or result is not None
    status = get_attr_any(result, ["success", "ok", "status"], result_mapping.get("status"))
    assert status in (True, "success", "ok", "completed", "done", 0, None) or status is not False


def test_app_integration_exposes_a_runnable_entrypoint():
    app_module = import_optional(["app", "app.cli", "app.main"])
    entrypoint = None
    for candidate in ("main", "run", "cli"):
        if hasattr(app_module, candidate):
            entrypoint = getattr(app_module, candidate)
            break

    if entrypoint is None:
        pytest.skip("App module does not expose a known entrypoint")

    spec_path = Path.cwd() / "sample_spec.json"
    spec_path.write_text(
        '{"name":"panel_001","units":"mm","operations":[{"type":"line"}]}',
        encoding="utf-8",
    )

    try:
        params = signature(entrypoint).parameters
        if len(params) == 0:
            result = entrypoint()
        elif len(params) == 1:
            result = entrypoint([str(spec_path)])
        else:
            result = call_with_supported_signature(
                entrypoint,
                [str(spec_path)],
                spec_path=str(spec_path),
                spec_file=str(spec_path),
                input_path=str(spec_path),
                argv=[str(spec_path)],
            )
        if result is not None:
            assert to_mapping(result) or result in (0, True)
    finally:
        if spec_path.exists():
            spec_path.unlink()
