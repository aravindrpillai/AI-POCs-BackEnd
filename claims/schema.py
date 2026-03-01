from __future__ import annotations

from typing import List, Optional, Literal, Union, Dict
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from datetime import date
import re

ResponseType = Literal["text", "number", "date", "file", "yesno"]
CarView = Literal["front", "rear", "left", "right", "top"]

# ---------- Inputs from UI (uploads) ----------

class UploadedFile(BaseModel):
    fileid: str = Field(..., min_length=1)            # provided by request
    filename: str = Field(..., min_length=1)
    content_type: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)               # storage pointer / presigned URL
    customer_note: Optional[str] = ""                 # provided by customer/UI


# ---------- AI outputs per image ----------

class ImageAnalysis(BaseModel):
    fileid: str = Field(..., min_length=1)
    customer_note: str = ""
    ai_analysis: str = Field(..., min_length=1)
    genuinity: int = Field(..., ge=1, le=10)          # 10 genuine, 1 likely fraud
    genuinity_flags: List[str] = Field(default_factory=list)


# ---------- Damage map / generated image requests ----------

class DamageZone(BaseModel):
    zone: str = Field(..., min_length=1)              # e.g., "front_bumper"
    severity: int = Field(..., ge=1, le=10)           # zone severity
    notes: str = ""


class DamageMap(BaseModel):
    is_collision: bool = False
    view: Optional[CarView] = None
    damage_zones: List[DamageZone] = Field(default_factory=list)


class GenerationRequest(BaseModel):
    type: Literal["car_damage_map"]
    view: CarView
    damage_zones: List[DamageZone] = Field(default_factory=list)


class AIImage(BaseModel):
    image_url: Optional[str] = None                   # URL to generated image asset
    summary: str = Field(..., min_length=1)
    generation_request: Optional[GenerationRequest] = None

    @model_validator(mode="after")
    def validate_image_or_request(self):
        # Must have either image_url OR generation_request
        if not self.image_url and not self.generation_request:
            raise ValueError("ai_images item must include image_url or generation_request")
        return self


# ---------- FNOL canonical data ----------

class FNOLFinalData(BaseModel):
    what_happened: str = Field(..., min_length=5)
    incident_date: date
    incident_location: str = Field(..., min_length=3)
    injury: str = Field(..., min_length=2)
    parties_involved: str = Field(..., min_length=2)
    vehicle_number: str = Field(..., min_length=1)

    police_fir_number: str = "Not provided"
    policy_number: str = "Not provided"

    contact_number: str = Field(..., min_length=7)
    email: EmailStr

    # Required final outputs you requested:
    severity: int = Field(..., ge=1, le=10)           # 10 very severe
    genuinity_score: int = Field(..., ge=1, le=10)    # 10 genuine, 1 likely fraud
    genuinity_rationale: str = Field(..., min_length=5)

    images: List[ImageAnalysis] = Field(default_factory=list)
    damage_map: DamageMap = Field(default_factory=DamageMap)
    ai_images: List[AIImage] = Field(default_factory=list)

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, v: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", v)
        if len(re.sub(r"\D", "", cleaned)) < 7:
            raise ValueError("contact_number looks too short")
        return v

    @model_validator(mode="after")
    def validate_collision_outputs(self):
        # If collision flagged, view must exist and either ai_images contains a request/image
        if self.damage_map.is_collision:
            if not self.damage_map.view:
                raise ValueError("damage_map.view is required when is_collision=true")
            # If collision with damage zones, encourage ai_images presence (enforce hard)
            if self.damage_map.damage_zones and not self.ai_images:
                raise ValueError("ai_images must be provided when collision damage zones exist")
        else:
            # If not collision, ai_images should be empty (enforce to keep clean)
            if self.ai_images:
                raise ValueError("ai_images must be empty when is_collision=false")
        return self


# ---------- Assistant response envelope ----------

class FNOLQuestionResponse(BaseModel):
    type: ResponseType
    message: str = Field(..., min_length=1)
    summary: Literal["false"] = "false"
    data: Dict[str, object] = Field(default_factory=dict)  # partial state is fine


class FNOLSummaryResponse(BaseModel):
    summary: Literal["true"] = "true"
    data: FNOLFinalData


FNOLResponse = Union[FNOLQuestionResponse, FNOLSummaryResponse]