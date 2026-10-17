"""Pydantic request and response contracts for the NagarSeva API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict, HttpUrl, field_validator


class RequestModel(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)


class PriorityRequest(RequestModel):
    model_config = ConfigDict(extra="allow")
    features: dict[str, float] = Field(default_factory=dict)


class InterventionRequest(RequestModel):
    model_config = ConfigDict(extra="allow")
    features: dict[str, Any] = Field(default_factory=dict)


class CostRequest(RequestModel):
    units: int = Field(500, ge=1)
    carpet_area_sqft: float = Field(300, gt=0)
    land_value_per_sqm: float = Field(40_000, ge=0)
    FSI: float = Field(2.5, gt=0)
    cross_subsidy_ratio: float = Field(.5, ge=0, le=1)


class FeasibilityRequest(RequestModel):
    land_area_sqm: float = Field(..., gt=0)
    fsi: float = Field(..., gt=0, le=10)
    eligible_households: int = Field(..., ge=0)
    rehab_area_sqft: float = Field(300, gt=0)
    construction_cost_per_sqft: float = Field(3200, gt=0)
    market_sale_rate_per_sqft: float = Field(14500, gt=0)
    tdr_value_per_sqft: float = Field(900, ge=0)
    premiums_and_fees_pct: float = Field(.12, ge=0, le=1)
    sales_share_pct: float = Field(.65, ge=0, le=1)
    cost_inflation_pct: float = Field(0, ge=-50, le=200)


class OptimizeRequest(RequestModel):
    budget_inr: float = Field(..., gt=0)
    min_vulnerable_share: float = Field(.25, ge=0, le=1)
    min_wards: int = Field(3, ge=1, le=20)


class GrievanceRequest(RequestModel):
    text: str = Field(..., min_length=3, max_length=2_000)
    pocket_id: str | None = None
    language: str = Field("en", pattern="^(en|hi|mr)$")
    synthetic: bool = True
    consent: bool = False

    @field_validator("text")
    @classmethod
    def meaningful_text(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("Describe the issue in at least three characters")
        return value.strip()


class EligibilityRequest(RequestModel):
    monthly_income_inr: float = Field(..., ge=0)
    family_size: int = Field(..., ge=1, le=20)
    has_aadhaar: bool = False
    has_ration_card: bool = False
    has_address_proof: bool = False
    years_in_settlement: int = Field(0, ge=0)
    tenure_document: bool = False
    urban_resident: bool | None = None
    owns_pucca_house: bool | None = None
    received_housing_benefit_last_20_years: bool | None = None
    owns_buildable_land: bool | None = None
    wants_rental: bool = False
    loan_amount_inr: float | None = Field(None, gt=0)
    property_value_inr: float | None = Field(None, gt=0)
    carpet_area_sqm: float | None = Field(None, gt=0)


class ObservationRequest(RequestModel):
    service: Literal["water", "sanitation", "power", "waste", "health"]
    value: float = Field(..., ge=0, le=168, allow_inf_nan=False)
    observed_at: datetime
    source_label: str = Field(..., min_length=3, max_length=200)
    evidence_url: HttpUrl | None = None
    notes: str = Field(..., min_length=3, max_length=2000)
    synthetic: bool = True
    consent: bool = False

    @field_validator("observed_at")
    @classmethod
    def date_not_future(cls, value: datetime) -> datetime:
        value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
        if (value - datetime.now(timezone.utc)).total_seconds() > 300:
            raise ValueError("Observation time cannot be in the future")
        return value

    @field_validator("source_label", "notes")
    @classmethod
    def trim_text(cls, value: str) -> str:
        if len(value.strip()) < 3:
            raise ValueError("Provide a meaningful source and evidence note")
        return value.strip()


class ComplaintAction(RequestModel):
    action: Literal["assign", "start", "complete", "escalate"]
    officer: str = Field(..., min_length=2, max_length=100)
    notes: str = Field(..., min_length=3, max_length=2000)
    department: str | None = Field(None, min_length=2, max_length=100)
    observation: ObservationRequest | None = None
    category: Literal["water", "sanitation", "power", "waste", "drainage", "health", "safety", "housing", "other"] | None = None
    urgency: Literal["urgent", "standard"] | None = None


class ResidentConfirmation(RequestModel):
    resolved: bool
    notes: str = Field(..., min_length=3, max_length=2000)


class ObservationVerification(RequestModel):
    reviewer: str = Field(..., min_length=2, max_length=100)
    notes: str = Field(..., min_length=3, max_length=2000)


class PilotEvaluation(RequestModel):
    participant_ref: str = Field(..., min_length=2, max_length=60)
    task: Literal["prepare_brief", "report_issue", "review_plan", "classify_complaint"]
    language: Literal["en", "hi", "mr"] = "en"
    baseline_seconds: float | None = Field(None, gt=0, le=86400)
    app_seconds: float | None = Field(None, gt=0, le=86400)
    completed: bool
    expected_category: Literal["water", "sanitation", "power", "waste", "drainage", "health", "safety", "housing", "other"] | None = None
    predicted_category: Literal["water", "sanitation", "power", "waste", "drainage", "health", "safety", "housing", "other"] | None = None
    feedback: str = Field(..., min_length=3, max_length=2000)
    synthetic: bool = True
    consent: bool = False


class ServiceCommitmentRequest(RequestModel):
    service: Literal["water", "sanitation", "power", "waste", "health"]
    target: float = Field(..., gt=0, le=168, allow_inf_nan=False)
    standard_source: str = Field(..., min_length=5, max_length=500)
    source_url: HttpUrl | None = None
    department: str = Field(..., min_length=2, max_length=100)
    approved_by: str = Field(..., min_length=2, max_length=100)
    synthetic: bool = True


class PilotLocationRequest(RequestModel):
    pocket_id: str = Field(..., pattern=r"^PILOT-[A-Za-z0-9-]{1,40}$")
    city: str = Field(..., min_length=2, max_length=100)
    ward: str = Field(..., min_length=2, max_length=100)
    lat: float = Field(..., ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(..., ge=-180, le=180, allow_inf_nan=False)
    area_sqm: float = Field(..., gt=0, allow_inf_nan=False)
    households: int = Field(..., ge=0)
    population: int = Field(..., ge=0)
    avg_household_income_inr: float | None = Field(None, ge=0, allow_inf_nan=False)
    approved_priority_score: float | None = Field(None, ge=0, le=100, allow_inf_nan=False)
    source_label: str = Field(..., min_length=5, max_length=200)
    source_url: HttpUrl
    licence: str = Field(..., min_length=3, max_length=200)
    approved_by: str = Field(..., min_length=2, max_length=100)
    consent: bool
