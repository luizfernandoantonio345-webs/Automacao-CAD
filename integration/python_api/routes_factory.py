from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .base_generator import BasePetrobrasGenerator
from .compliance_loader import get_rule, get_rule_param
from .dependencies import CONFIG
from .documentation_engine import generate_batch_documentation
from .execution_engine import (
    audit_regap_conformity,
    build_data_book_zip,
    export_execution_kit,
    generate_full_unit_project,
)
from .piping_autorouter import PipingAutoRouter
from .worker_mecanica import processar_escada_marinheiro


router = APIRouter(prefix="/factory", tags=["factory_10x"])


class Point3D(BaseModel):
    x: float
    y: float
    z: float


class UniversalComponent(BaseModel):
    id: str
    origin: Point3D
    size: Point3D


class UniversalAnalysisRequest(BaseModel):
    disciplina: str = "universal"
    clearance_mm: float = Field(default=0.0, ge=0.0)
    components: list[UniversalComponent]


class AutoRouterRequest(BaseModel):
    ponto_a: Point3D
    ponto_b: Point3D
    diametro_nominal_mm: float = Field(..., gt=0)
    material: str = "ASTM A106 Gr.B"
    schedule: str = "STD"


class BatchDocsRequest(BaseModel):
    components: list[dict[str, Any]]
    max_workers: int = Field(default=16, ge=1, le=64)


class PumpUnitRequest(BaseModel):
    altura_torre_m: float = Field(..., gt=2.0, le=200.0)
    ponto_succao: Point3D
    ponto_descarga: Point3D
    diametro_nominal_mm: float = Field(..., gt=0)


class FullUnitProjectRequest(BaseModel):
    altura_torre_m: float = Field(default=8.0, gt=2.0, le=200.0)
    qtd_porticos: int = Field(default=50, ge=1, le=200)
    diametro_nominal_mm: float = Field(default=100.0, gt=0)
    ponto_succao: Point3D = Field(default_factory=lambda: Point3D(x=1500.0, y=7600.0, z=0.0))
    ponto_descarga: Point3D = Field(default_factory=lambda: Point3D(x=23500.0, y=7600.0, z=6000.0))
    stock_lengths_m: list[float] = Field(default_factory=lambda: [6.0, 12.0])


class QualityGateRequest(FullUnitProjectRequest):
    max_clash_resolution_iterations: int = Field(default=12, ge=1, le=50)


def _output_root() -> Path:
    root = Path(CONFIG.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


@router.get("/compliance/{rule_code}")
async def get_compliance(rule_code: str) -> dict[str, Any]:
    try:
        return {"status": "ok", "rule": rule_code, "payload": get_rule(rule_code)}
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Regra não encontrada: {exc}") from exc


@router.post("/universal/analyze")
async def analyze_universal(req: UniversalAnalysisRequest) -> dict[str, Any]:
    gen = BasePetrobrasGenerator()
    gen.disciplina = req.disciplina

    components = [
        {
            "id": item.id,
            "origin": item.origin.model_dump(),
            "size": {
                "dx": item.size.x,
                "dy": item.size.y,
                "dz": item.size.z,
            },
        }
        for item in req.components
    ]
    result = gen.detect_interferences(components, clearance_mm=req.clearance_mm)
    return {"status": "ok", **result}


@router.post("/piping/autorouter")
async def run_piping_autorouter(req: AutoRouterRequest) -> dict[str, Any]:
    try:
        router_engine = PipingAutoRouter(_output_root())
        return router_engine.generate(
            ponto_a=req.ponto_a.model_dump(),
            ponto_b=req.ponto_b.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            material=req.material,
            schedule=req.schedule,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha no auto-router: {exc}") from exc


@router.post("/docs/batch")
async def run_batch_docs(req: BatchDocsRequest) -> dict[str, Any]:
    try:
        docs_dir = _output_root() / "docs"
        return generate_batch_documentation(req.components, docs_dir, max_workers=req.max_workers)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha na documentação em lote: {exc}") from exc


@router.post("/unidade-bombeamento")
async def generate_pump_unit(req: PumpUnitRequest) -> dict[str, Any]:
    try:
        out = _output_root()

        escada = processar_escada_marinheiro(req.altura_torre_m, out)

        router_engine = PipingAutoRouter(out)
        piping = router_engine.generate(
            ponto_a=req.ponto_succao.model_dump(),
            ponto_b=req.ponto_descarga.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            material=str(get_rule_param("N-1810", "materials.default_pipe_material", "ASTM A106 Gr.B")),
            schedule=str(get_rule_param("N-1810", "materials.default_schedule", "STD")),
        )

        support_components = [
            {
                "id": sup["id"],
                "categoria": "SUPORTE_TUBULACAO",
                "norma": "N-1810",
                "peso_kg": 18.0,
                "dados": str(sup),
            }
            for sup in piping["payload"]["routing"]["supports"]
        ]
        support_components.append(
            {
                "id": "ESCADA-MARINHEIRO-01",
                "categoria": "ESCADA_GUARDA_CORPO",
                "norma": "N-1710/NR-12",
                "peso_kg": escada["payload"]["resultado"]["peso_total_kg"],
                "dados": str(escada["payload"]["parametros_escada"]),
            }
        )

        docs = generate_batch_documentation(support_components, out / "docs", max_workers=32)
        return {
            "status": "ok",
            "modulo": "pump_unit_bootstrap",
            "artefatos": {
                "escada": escada["artifact"],
                "piping": piping["artifact"],
                "documentacao_count": docs["components"],
            },
            "normas_aplicadas": ["N-1710", "N-1810", "NR-12"],
            "message": "Unidade de bombeamento parametrizada gerada com fábrica de disciplinas.",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar unidade de bombeamento: {exc}") from exc


@router.post("/generate-full-unit-project")
async def generate_full_unit_project_route(req: FullUnitProjectRequest) -> dict[str, Any]:
    try:
        result = generate_full_unit_project(
            output_dir=_output_root(),
            altura_torre_m=req.altura_torre_m,
            qtd_porticos=req.qtd_porticos,
            ponto_succao=req.ponto_succao.model_dump(),
            ponto_descarga=req.ponto_descarga.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            stock_lengths_m=req.stock_lengths_m,
        )
        return {
            "status": "ok",
            "modulo": "smartdesign_core_engine",
            "message": "Pipeline unificado concluído com verificações estruturais, clash detection e consolidação técnica.",
            "artifacts": result["artifacts"],
            "validation": result["validation"],
            "summary": {
                "qtd_porticos": result["disciplinas"]["estrutura"]["summary"]["qtd_porticos"],
                "massa_total_kg": result["inventario_tecnico"]["resumo"]["massa_total_kg"],
                "custo_total_brl": result["inventario_tecnico"]["resumo"]["custo_total_brl"],
                "modo_critico": result["header"]["critical_execution_mode"],
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar pacote técnico unificado: {exc}") from exc


@router.post("/export-execution-kit")
async def export_execution_kit_route(req: FullUnitProjectRequest) -> dict[str, Any]:
    try:
        project_data = generate_full_unit_project(
            output_dir=_output_root(),
            altura_torre_m=req.altura_torre_m,
            qtd_porticos=req.qtd_porticos,
            ponto_succao=req.ponto_succao.model_dump(),
            ponto_descarga=req.ponto_descarga.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            stock_lengths_m=req.stock_lengths_m,
        )
        export_data = export_execution_kit(project_data, _output_root())
        return {
            "status": "ok",
            "modulo": "smartdesign_execution_kit",
            "message": "Pacote executivo exportado com desenho, BOM, memorial, ROI e rastreabilidade XData.",
            **export_data,
            "validation": project_data["validation"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao exportar pacote executivo: {exc}") from exc


@router.post("/data-book/generate")
async def generate_data_book_route(req: FullUnitProjectRequest) -> dict[str, Any]:
    try:
        project_data = generate_full_unit_project(
            output_dir=_output_root(),
            altura_torre_m=req.altura_torre_m,
            qtd_porticos=req.qtd_porticos,
            ponto_succao=req.ponto_succao.model_dump(),
            ponto_descarga=req.ponto_descarga.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            stock_lengths_m=req.stock_lengths_m,
        )
        export_data = export_execution_kit(project_data, _output_root())
        data_book = build_data_book_zip(export_data, _output_root())
        regap_audit = audit_regap_conformity(export_data)
        return {
            "status": "ok",
            "modulo": "smartdesign_data_book",
            "message": "Data-Book consolidado em zip com Memorial, Isometricos, MTO e Plano de Pintura.",
            "data_book": data_book,
            "regap_audit": regap_audit,
            "validation": project_data["validation"],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar Data-Book: {exc}") from exc


@router.post("/quality-gate/final")
async def run_cto_quality_gate(req: QualityGateRequest) -> dict[str, Any]:
    try:
        project_data = generate_full_unit_project(
            output_dir=_output_root(),
            altura_torre_m=req.altura_torre_m,
            qtd_porticos=req.qtd_porticos,
            ponto_succao=req.ponto_succao.model_dump(),
            ponto_descarga=req.ponto_descarga.model_dump(),
            diametro_nominal_mm=req.diametro_nominal_mm,
            stock_lengths_m=req.stock_lengths_m,
        )
        export_data = export_execution_kit(project_data, _output_root())
        data_book = build_data_book_zip(export_data, _output_root())
        regap_audit = audit_regap_conformity(export_data)

        clash = project_data["validation"]["clash_detection"]
        unresolved_clashes = int(clash.get("total_after", 0))
        loop_guard_triggered = unresolved_clashes > 0

        remediation_actions: list[str] = []
        if unresolved_clashes > 0:
            remediation_actions.append(
                "Executar novo roteamento deslocando a tubulacao em eixo Y com passo de 600 mm ate eliminar AABB residual."
            )
            remediation_actions.append(
                "Reprocessar implantacao da escada com deslocamento vertical incremental e aumento de clearance N-1810."
            )
            remediation_actions.append(
                "Revisar envelope de suportes para remover sobreposicao com vigas do portico antes do DXF final."
            )

        if regap_audit.get("status") != "ok":
            remediation_actions.append(
                "Regenerar documentos sem selo REGAP aplicando token REGAP-CONFORME nos artefatos obrigatorios do Data-Book."
            )

        if not remediation_actions:
            remediation_actions.append("Nenhuma acao corretiva necessaria: pacote aprovado para fabricacao e emissao.")

        final_status = "approved" if (unresolved_clashes == 0 and regap_audit.get("status") == "ok") else "rejected"

        return {
            "status": "ok",
            "modulo": "cto_quality_gate",
            "final_gate": {
                "status": final_status,
                "owner": "CTO",
                "criteria": {
                    "clash_detection_chat1_chat2": "ok" if unresolved_clashes == 0 else "nao_conforme",
                    "regap_conformity_seal": regap_audit.get("status"),
                    "data_book_zip": "ok" if data_book.get("zip_path") else "nao_conforme",
                    "loop_guard": "triggered" if loop_guard_triggered else "ok",
                },
            },
            "clash_detection": clash,
            "regap_audit": regap_audit,
            "data_book": data_book,
            "technical_solution": remediation_actions,
            "artifacts": export_data.get("artifacts", {}),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "problem": f"Falha no quality gate final: {exc}",
                "technical_solution": [
                    "Verificar consistencia de coordenadas de sucao/descarga e altura da torre.",
                    "Reexecutar pipeline com parametros default e clearance minimo N-1810.",
                    "Persistir export_manifest e revisar documentos ausentes antes de nova tentativa.",
                ],
            },
        ) from exc
