from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .business_impact import gerar_business_impact
from .dependencies import CONFIG
from .piping_module import gerar_bom_linha_reta_duas_curvas
from .worker_mecanica import processar_escada_marinheiro

# Imports para o módulo NBR 8800 e Isométricos
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engenharia_automacao.core.nbr8800 import Calculista, EntradaCalculo
from engenharia_automacao.core.nbr8800.relatorio import gerar_relatorio_markdown, gerar_relatorio_html
from engenharia_automacao.core.isometrica import (
    SistemaIsometrico,
    Ponto3D,
    Tubo,
    Valvula,
    TipoValvula,
    GeradorDXF,
)


router = APIRouter(prefix="/mecanica", tags=["mecanica"])


class PerfilHomologadoRequest(BaseModel):
    designacao: str = Field(..., min_length=3)
    material: str = Field(default="ASTM A36", min_length=3)
    fabricacao: str = Field(default="laminado", min_length=3)
    massa_linear_kg_m: float = Field(..., gt=0)
    observacao: str | None = None


class PerfisHomologadosEscadaRequest(BaseModel):
    montante: PerfilHomologadoRequest | None = None
    degrau: PerfilHomologadoRequest | None = None
    gaiola_aro: PerfilHomologadoRequest | None = None
    gaiola_longitudinal: PerfilHomologadoRequest | None = None
    suporte_braco: PerfilHomologadoRequest | None = None


class EscadaMarinheiroRequest(BaseModel):
    altura_torre_m: float = Field(..., gt=2.0, le=200.0, description="Altura da torre em metros")
    comprimento_barra_comercial_mm: int = Field(default=12000, ge=3000, le=18000)
    perfis_homologados: PerfisHomologadosEscadaRequest | None = None


class BusinessImpactRequest(BaseModel):
    peso_total_aco_kg: float | None = Field(default=None, gt=0)


class PipingBomRequest(BaseModel):
    comprimento_reto_m: float = Field(..., gt=0)
    diametro_nominal_mm: float = Field(..., gt=0)
    material: str = "ASTM A106 Gr.B"
    schedule: str = "STD"


def _get_output_dir() -> Path:
    output_dir = Path(CONFIG.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _obter_peso_stress_result(output_dir: Path) -> float:
    stress_result = output_dir / "stress_test_result.json"
    if not stress_result.exists():
        raise FileNotFoundError("stress_test_result.json não encontrado")

    payload: dict[str, Any] = json.loads(stress_result.read_text(encoding="utf-8"))
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    peso = summary.get("peso_total_aco_kg")
    if peso is None:
        raise ValueError("peso_total_aco_kg não encontrado no summary")
    return float(peso)


@router.post("/escada-marinheiro")
async def gerar_escada_marinheiro(req: EscadaMarinheiroRequest) -> dict[str, Any]:
    try:
        result = processar_escada_marinheiro(
            req.altura_torre_m,
            _get_output_dir(),
            perfis_homologados=req.perfis_homologados.model_dump(exclude_none=True) if req.perfis_homologados else None,
            stock_length_mm=req.comprimento_barra_comercial_mm,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar escada: {exc}") from exc

    return {
        "status": "ok",
        "modulo": "mecanica_escadas",
        **result,
    }


@router.post("/business-impact")
async def gerar_relatorio_business_impact(req: BusinessImpactRequest) -> dict[str, Any]:
    output_dir = _get_output_dir()
    try:
        peso_total = req.peso_total_aco_kg if req.peso_total_aco_kg is not None else _obter_peso_stress_result(output_dir)
        result = gerar_business_impact(float(peso_total), output_dir)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar business impact: {exc}") from exc

    return {
        "status": "ok",
        "modulo": "business_impact",
        **result,
    }


@router.post("/tubulacao/bom")
async def gerar_bom_tubulacao(req: PipingBomRequest) -> dict[str, Any]:
    try:
        result = gerar_bom_linha_reta_duas_curvas(
            comprimento_reto_m=req.comprimento_reto_m,
            diametro_nominal_mm=req.diametro_nominal_mm,
            output_dir=_get_output_dir(),
            material=req.material,
            schedule=req.schedule,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Falha ao gerar BOM de tubulação: {exc}") from exc

    return {
        "status": "ok",
        "modulo": "tubulacao_isometrico",
        **result,
    }


# ===========================================================================
# ENDPOINTS INTEGRADOS — NBR 8800 + ISOMÉTRICOS
# ===========================================================================

class EntradaCalculoRequest(BaseModel):
    """Dados de entrada para dimensionamento estrutural NBR 8800."""
    g: float = Field(..., gt=0, description="Carga permanente [kN/m]")
    q: float = Field(..., gt=0, description="Sobrecarga variável [kN/m]")
    L: float = Field(..., gt=0.5, le=30.0, description="Vão da viga [m]")
    Lb: Optional[float] = Field(default=None, description="Comprimento destravado [m]")
    Cb: float = Field(default=1.0, ge=1.0, description="Fator de momento equivalente")


class TuboInput(BaseModel):
    """Segmento de tubo para modelagem isométrica."""
    nome: str
    P1: list[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] em metros")
    P2: list[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] em metros")
    diametro_m: float = Field(default=0.05, gt=0)
    material: str = "Aço Carbono"
    label: Optional[str] = None


class ValvulaInput(BaseModel):
    """Válvula ou componente para modelagem isométrica."""
    nome: str
    tipo: str = Field(..., description="gaveta|globo|retenção|purgador|tee|cotovelo|redutor|bola|borboleta")
    posicao: list[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] em metros")
    diametro_m: float = Field(default=0.05, gt=0)
    label: Optional[str] = None


class IsometricoInput(BaseModel):
    """Modelo de tubulação para geração de isométrico DXF."""
    tubos: list[TuboInput] = Field(default_factory=list)
    valvulas: list[ValvulaInput] = Field(default_factory=list)
    vao_maximo_suporte_m: float = Field(default=2.5, gt=0.5, description="Vão máximo para suporte automático [m]")
    titulo: str = "Isométrico de Tubulação"


class CalculoIsometricoRequest(BaseModel):
    """Request combinado: cálculo estrutural + geração isométrica."""
    calculo_estrutural: EntradaCalculoRequest
    isometrico: Optional[IsometricoInput] = None
    gerar_pdf: bool = Field(default=False, description="Gerar PDF do relatório técnico")


class CalculoIsometricoResponse(BaseModel):
    """Response do fluxo integrado."""
    status: str
    perfil_selecionado: str
    taxa_utilizacao: float
    aprovado: bool
    relatorio_md_path: str
    relatorio_html_path: Optional[str] = None
    relatorio_pdf_path: Optional[str] = None
    dxf_path: Optional[str] = None
    bom: Optional[dict] = None
    perfis_homologados: list[str] = []


def _tipo_valvula_from_str(tipo_str: str) -> TipoValvula:
    """Converte string para enum TipoValvula."""
    mapa = {
        "gaveta": TipoValvula.GAVETA,
        "globo": TipoValvula.GLOBO,
        "retenção": TipoValvula.RETENCAO,
        "retencao": TipoValvula.RETENCAO,
        "purgador": TipoValvula.PURGADOR,
        "tee": TipoValvula.TEE,
        "cotovelo": TipoValvula.COTOVELO,
        "redutor": TipoValvula.REDUTOR,
        "bola": TipoValvula.BOLA,
        "borboleta": TipoValvula.BUTTERFLY,
    }
    return mapa.get(tipo_str.lower(), TipoValvula.GAVETA)


@router.post("/calculo-isometrico", response_model=CalculoIsometricoResponse)
async def executar_calculo_isometrico(req: CalculoIsometricoRequest) -> CalculoIsometricoResponse:
    """
    **Endpoint Integrado: Calculista NBR 8800 + Gerador de Isométricos**

    Executa:
    1. Dimensionamento estrutural conforme NBR 8800:2008 (LRFD)
    2. Geração de relatório técnico (Markdown + HTML)
    3. Geração opcional de isométrico DXF com BOM
    4. Geração opcional de PDF

    Parâmetros:
    - **calculo_estrutural**: Dados de carga e vão para dimensionamento
    - **isometrico**: Modelo de tubulação 3D (opcional)
    - **gerar_pdf**: Se True, tenta gerar PDF do relatório
    """
    output_dir = _get_output_dir()

    try:
        # ===== FASE 1: CÁLCULO ESTRUTURAL NBR 8800 =====
        entrada = EntradaCalculo(
            g=req.calculo_estrutural.g,
            q=req.calculo_estrutural.q,
            L=req.calculo_estrutural.L,
            Lb=req.calculo_estrutural.Lb,
            Cb=req.calculo_estrutural.Cb,
        )

        calculista = Calculista()
        relatorio_nbr = calculista.dimensionar(entrada)
        resultado = relatorio_nbr.perfil_selecionado

        # Gerar relatório Markdown
        md_content = gerar_relatorio_markdown(relatorio_nbr)
        md_path = output_dir / "relatorio_nbr8800_api.md"
        md_path.write_text(md_content, encoding="utf-8")

        # Gerar relatório HTML
        html_content = gerar_relatorio_html(relatorio_nbr)
        html_path = output_dir / "relatorio_nbr8800_api.html"
        html_path.write_text(html_content, encoding="utf-8")

        # Lista de perfis homologados
        perfis_homologados = [p.nome for p in relatorio_nbr.lista_homologados[:10]]

        response_data = {
            "status": "ok",
            "perfil_selecionado": resultado.perfil.nome,
            "taxa_utilizacao": round(resultado.flexao.eta, 4),
            "aprovado": resultado.aprovado,
            "relatorio_md_path": str(md_path),
            "relatorio_html_path": str(html_path),
            "perfis_homologados": perfis_homologados,
        }

        # ===== FASE 2: GERAÇÃO DE ISOMÉTRICO (OPCIONAL) =====
        if req.isometrico and (req.isometrico.tubos or req.isometrico.valvulas):
            sistema = SistemaIsometrico()

            # Adicionar tubos
            for t in req.isometrico.tubos:
                tubo = Tubo(
                    nome=t.nome,
                    P1=Ponto3D(x=t.P1[0], y=t.P1[1], z=t.P1[2]),
                    P2=Ponto3D(x=t.P2[0], y=t.P2[1], z=t.P2[2]),
                    diametro=t.diametro_m,
                    material=t.material,
                    label=t.label,
                )
                sistema.adicionar_tubo(tubo)

            # Adicionar válvulas
            for v in req.isometrico.valvulas:
                valvula = Valvula(
                    nome=v.nome,
                    tipo=_tipo_valvula_from_str(v.tipo),
                    posicao=Ponto3D(x=v.posicao[0], y=v.posicao[1], z=v.posicao[2]),
                    diametro=v.diametro_m,
                    label=v.label,
                )
                sistema.adicionar_valvula(valvula)

            # Suportes automáticos
            sistema.calcular_vaos_livres(vao_maximo=req.isometrico.vao_maximo_suporte_m)

            # BOM
            bom = sistema.gerar_bom()
            response_data["bom"] = bom

            # DXF
            titulo_dxf = f"{req.isometrico.titulo} — {resultado.perfil.nome}"
            gerador_dxf = GeradorDXF(sistema, titulo=titulo_dxf)
            dxf_path = output_dir / "isometrico_api.dxf"
            gerador_dxf.gerar(dxf_path)
            response_data["dxf_path"] = str(dxf_path)

        # ===== FASE 3: PDF (OPCIONAL) =====
        if req.gerar_pdf:
            pdf_path = _tentar_gerar_pdf(html_path, output_dir)
            if pdf_path:
                response_data["relatorio_pdf_path"] = str(pdf_path)

        return CalculoIsometricoResponse(**response_data)

    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro no cálculo/geração: {exc}") from exc


def _tentar_gerar_pdf(html_path: Path, output_dir: Path) -> Optional[Path]:
    """Tenta gerar PDF a partir do HTML usando weasyprint ou pdfkit.

    Retorna caminho do PDF ou None se não conseguir.
    """
    pdf_path = output_dir / "relatorio_nbr8800_api.pdf"

    # Tentativa 1: weasyprint
    try:
        from weasyprint import HTML
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return pdf_path
    except ImportError:
        pass
    except Exception:
        pass

    # Tentativa 2: pdfkit (requer wkhtmltopdf instalado)
    try:
        import pdfkit
        pdfkit.from_file(str(html_path), str(pdf_path))
        return pdf_path
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: não gera PDF, mas não falha
    return None


@router.get("/download/{filename}")
async def download_arquivo(filename: str):
    """Download de arquivos gerados (relatórios, DXF)."""
    output_dir = _get_output_dir()
    file_path = output_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {filename}")

    # Determinar content-type
    suffix = file_path.suffix.lower()
    media_types = {
        ".md": "text/markdown",
        ".html": "text/html",
        ".pdf": "application/pdf",
        ".dxf": "application/dxf",
        ".json": "application/json",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(path=file_path, filename=filename, media_type=media_type)
