"""Proposed minimised field form. No observations are supplied with the project."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from pydantic import Field, model_validator
from .planning_schemas import Request


class FieldSurvey(Request):
    survey_id: str = Field(pattern=r"^[a-zA-Z0-9:_-]{2,100}$")
    settlement_id: str
    observed_at: datetime
    water_hours_per_day: float | None = Field(None, ge=0, le=24)
    functional_toilets_observed: int | None = Field(None, ge=0, le=10000, strict=True)
    blocked_drain_segments_observed: int | None = Field(None, ge=0, le=10000, strict=True)
    sanitation_condition: Literal["functioning", "partly_functioning", "not_functioning", "not_observed"] = "not_observed"
    drainage_condition: Literal["clear", "partly_blocked", "blocked", "not_observed"] = "not_observed"
    housing_or_infrastructure_observation: str = Field("", max_length=2000)
    gps_latitude: float | None = Field(None, ge=-90, le=90)
    gps_longitude: float | None = Field(None, ge=-180, le=180)
    evidence_reference: str | None = Field(None, pattern=r"^https://\S+$", max_length=2000)
    evidence_consent: bool = False
    inspector_reference: str = Field(min_length=2, max_length=80)
    verification_status: Literal["reported"] = "reported"
    collection_platform: Literal["KoboToolbox", "ODK", "authorized_manual"]
    protocol_reference: str = Field(min_length=5, max_length=2000)

    @model_validator(mode="after")
    def validate_field_record(self):
        if self.observed_at.tzinfo is None or self.observed_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Observation time must be timezone aware and not in the future")
        if (self.gps_latitude is None) != (self.gps_longitude is None):
            raise ValueError("Supply both coarse coordinates or neither")
        for value in (self.gps_latitude, self.gps_longitude):
            if value is not None and abs(value - round(value, 3)) > 1e-9:
                raise ValueError("Use at most three decimal places for privacy-preserving location (about 100 metres)")
        if self.evidence_reference and not self.evidence_consent:
            raise ValueError("Evidence references require recorded consent and an approved store")
        return self
