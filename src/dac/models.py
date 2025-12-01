"""Pydantic models for YAML schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class EnablementManifest(BaseModel):
    """Schema for enablement.yaml - declares which prebuilt rules should be enabled/disabled."""

    enabled: list[str] = Field(
        default_factory=list,
        description="List of rule_ids that should be enabled",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="List of rule_ids that should be explicitly disabled",
    )


class RuleOverride(BaseModel):
    """Schema for prebuilt rule override files.

    Allows customizing properties of prebuilt rules without replacing them.
    """

    rule_id: str = Field(description="The prebuilt rule's rule_id to override")
    severity: Literal["low", "medium", "high", "critical"] | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = Field(default=None, description="Additional tags to add")

    # Scheduling overrides
    interval: str | None = Field(default=None, description="Rule run interval (e.g., '5m')")
    from_: str | None = Field(default=None, alias="from", description="Lookback period (e.g., 'now-6m')")

    model_config = {"populate_by_name": True}


class CustomerConfig(BaseModel):
    """Schema for customer configuration in customers/<name>/config.yaml."""

    name: str = Field(description="Customer display name")
    enabled_rules_repo: str = Field(description="GitHub repo for enabled rules (e.g., 'owner/acme-enabled-rules')")
    authored_rules_repo: str | None = Field(
        default=None,
        description="GitHub repo for custom rules (e.g., 'owner/acme-authored-rules')",
    )
    kibana_url: str | None = Field(
        default=None,
        description="Override KIBANA_URL for this customer",
    )
    elastic_space: str = Field(
        default="default",
        description="Kibana space for this customer",
    )


class InScopeRules(BaseModel):
    """Schema for customers/<name>/in-scope-rules.yaml.

    Master list of prebuilt rules that should be enabled for this customer.
    This is the source of truth that gets synced to the customer's enabled-rules repo.
    """

    enabled: list[str] = Field(
        default_factory=list,
        description="List of prebuilt rule_ids to enable",
    )
    disabled: list[str] = Field(
        default_factory=list,
        description="List of prebuilt rule_ids to explicitly disable",
    )
