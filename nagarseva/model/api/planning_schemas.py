"""Shared validated planning and evidence request contracts."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictFloat


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class PriorityInput(Request):
    weights: dict[str, StrictFloat] | None = None


class Option(Request):
    kind: Literal["upgrade", "redevelop", "relocate"]
    unit_cost_inr: float = Field(ge=0, le=100_000_000)
    shared_works_inr: float = Field(ge=0, le=100_000_000_000)
    months: float = Field(ge=1, le=120)
    temporary_months: float = Field(ge=0, le=120)
    disrupted_share: float = Field(ge=0, le=1)
    assumed_service_coverage_pct: float = Field(ge=0, le=100)


class ScenarioInput(Request):
    households: int | None = Field(None, ge=1, le=100_000, strict=True)
    contingency_pct: float = Field(10, ge=0, le=100)
    temporary_rent_per_month: float = Field(5000, ge=0, le=1_000_000)
    annual_maintenance_per_household: float = Field(1200, ge=0, le=1_000_000)
    include_relocation: bool = False
    relocation_reason: str = Field("", max_length=2000)
    options: list[Option] = Field(min_length=2, max_length=3)


class EvidenceInput(Request):
    filename: str = Field(min_length=1, max_length=160)
    content_type: Literal["image/png", "image/jpeg", "application/pdf", "text/plain"]
    content_base64: str = Field(min_length=1, max_length=2_800_000)
    actor: str = Field(min_length=2, max_length=80)
    notes: str = Field(min_length=5, max_length=2000)
