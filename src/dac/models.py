"""Pydantic models for YAML schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class EnablementManifest(BaseModel):
    """Schema for enablement.yaml - declares which rules should be enabled/disabled."""

    enabled: list[str] = Field(
        default_factory=list,
        description="List of rule_ids that should be enabled",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="List of rule_ids that should be explicitly disabled",
    )


class RuleOverride(BaseModel):
    """Schema for OOTB rule override files."""

    rule_id: str = Field(description="The prebuilt rule's rule_id to override")
    severity: Literal["low", "medium", "high", "critical"] | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    enabled: bool | None = None
    tags: list[str] | None = None


class ExceptionList(BaseModel):
    """Schema for exception list definitions."""

    list_id: str = Field(description="Stable unique identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="")
    type: Literal["detection", "endpoint", "rule_default"] = "detection"
    namespace_type: Literal["single", "agnostic"] = "single"
    tags: list[str] = Field(default_factory=list)


class ExceptionEntry(BaseModel):
    """A single condition in an exception item."""

    field: str
    operator: Literal["included", "excluded"]
    type: Literal["match", "match_any", "exists", "list", "wildcard"]
    value: str | list[str] | None = None


class ExceptionItem(BaseModel):
    """Schema for exception item definitions."""

    item_id: str = Field(description="Stable unique identifier")
    list_id: str = Field(description="Parent list identifier")
    name: str = Field(description="Human-readable name")
    description: str = Field(default="")
    type: Literal["simple"] = "simple"
    namespace_type: Literal["single", "agnostic"] = "single"
    entries: list[ExceptionEntry] = Field(default_factory=list)
