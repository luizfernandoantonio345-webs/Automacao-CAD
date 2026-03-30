from __future__ import annotations

from pydantic import BaseModel, confloat, constr


class LoginRequest(BaseModel):
    email: constr(strip_whitespace=True, min_length=3, max_length=120)
    senha: constr(min_length=1, max_length=120)


class RegisterRequest(BaseModel):
    email: constr(strip_whitespace=True, min_length=3, max_length=120)
    senha: constr(min_length=8, max_length=120)
    empresa: constr(strip_whitespace=True, min_length=1, max_length=120) | None = None


class DemoLoginResponse(BaseModel):
    email: str
    empresa: str
    limite: int
    usado: int


class GenerateRequest(BaseModel):
    diameter: confloat(gt=0, le=1_000_000)
    length: confloat(gt=0, le=10_000_000)
    company: constr(strip_whitespace=True, min_length=1, max_length=120)
    part_name: constr(strip_whitespace=True, min_length=1, max_length=120)
    code: constr(strip_whitespace=True, min_length=1, max_length=120)
    executar: bool = False


class AutopilotRequest(BaseModel):
    project_name: constr(strip_whitespace=True, min_length=3, max_length=100)
    company: constr(strip_whitespace=True, min_length=1, max_length=120)
    code: constr(strip_whitespace=True, min_length=1, max_length=120)
    shed_width_m: confloat(gt=1, le=300)
    shed_length_m: confloat(gt=1, le=500)
    bay_spacing_m: confloat(gt=0.5, le=25)
    eave_height_m: confloat(gt=1, le=50)
    roof_slope_percent: confloat(ge=0, le=100)
    load_knm: confloat(gt=0, le=10_000)
    material_id: int
    execute_in_autocad: bool = False
