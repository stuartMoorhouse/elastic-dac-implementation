"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from dac.models import CustomerConfig, EnablementManifest, InScopeRules, RuleOverride


class TestEnablementManifest:
    """Tests for EnablementManifest model."""

    def test_empty_manifest(self) -> None:
        """Test empty manifest is valid."""
        manifest = EnablementManifest()
        assert manifest.enabled == []
        assert manifest.disabled == []

    def test_manifest_with_rules(self) -> None:
        """Test manifest with rule IDs."""
        manifest = EnablementManifest(
            enabled=["rule-1", "rule-2"],
            disabled=["rule-3"],
        )
        assert "rule-1" in manifest.enabled
        assert "rule-3" in manifest.disabled


class TestInScopeRules:
    """Tests for InScopeRules model."""

    def test_empty_in_scope_rules(self) -> None:
        """Test empty in-scope rules is valid."""
        rules = InScopeRules()
        assert rules.enabled == []
        assert rules.disabled == []

    def test_in_scope_rules_with_rules(self) -> None:
        """Test in-scope rules with rule IDs."""
        rules = InScopeRules(
            enabled=["28d39238-0c01-420a-b77a-24e5a7378663"],
            disabled=["ff10d4d8-fea7-422d-afb1-e5a2702369a9"],
        )
        assert len(rules.enabled) == 1
        assert len(rules.disabled) == 1


class TestCustomerConfig:
    """Tests for CustomerConfig model."""

    def test_minimal_customer_config(self) -> None:
        """Test minimal valid customer config."""
        config = CustomerConfig(
            name="ACME Corp",
            enabled_rules_repo="acme-org/acme-enabled-rules",
        )
        assert config.name == "ACME Corp"
        assert config.enabled_rules_repo == "acme-org/acme-enabled-rules"
        assert config.authored_rules_repo is None
        assert config.kibana_url is None
        assert config.elastic_space == "default"

    def test_full_customer_config(self) -> None:
        """Test full customer config with all fields."""
        config = CustomerConfig(
            name="ACME Corp",
            enabled_rules_repo="acme-org/acme-enabled-rules",
            authored_rules_repo="acme-org/acme-authored-rules",
            kibana_url="https://acme.kb.us-central1.gcp.cloud.es.io",
            elastic_space="security",
        )
        assert config.authored_rules_repo == "acme-org/acme-authored-rules"
        assert config.kibana_url == "https://acme.kb.us-central1.gcp.cloud.es.io"
        assert config.elastic_space == "security"

    def test_customer_config_missing_required(self) -> None:
        """Test customer config fails without required fields."""
        with pytest.raises(ValidationError):
            CustomerConfig(name="ACME Corp")  # missing enabled_rules_repo


class TestRuleOverride:
    """Tests for RuleOverride model."""

    def test_minimal_override(self) -> None:
        """Test minimal valid override."""
        override = RuleOverride(rule_id="28d39238-0c01-420a-b77a-24e5a7378663")
        assert override.rule_id == "28d39238-0c01-420a-b77a-24e5a7378663"
        assert override.severity is None
        assert override.risk_score is None

    def test_override_with_severity(self) -> None:
        """Test override with severity change."""
        override = RuleOverride(
            rule_id="28d39238-0c01-420a-b77a-24e5a7378663",
            severity="critical",
            risk_score=95,
        )
        assert override.severity == "critical"
        assert override.risk_score == 95

    def test_override_invalid_severity(self) -> None:
        """Test override fails with invalid severity."""
        with pytest.raises(ValidationError):
            RuleOverride(
                rule_id="28d39238-0c01-420a-b77a-24e5a7378663",
                severity="super-high",  # invalid
            )

    def test_override_invalid_risk_score(self) -> None:
        """Test override fails with invalid risk score."""
        with pytest.raises(ValidationError):
            RuleOverride(
                rule_id="28d39238-0c01-420a-b77a-24e5a7378663",
                risk_score=150,  # must be 0-100
            )

    def test_override_with_scheduling(self) -> None:
        """Test override with scheduling fields."""
        override = RuleOverride(
            rule_id="28d39238-0c01-420a-b77a-24e5a7378663",
            interval="1m",
        )
        assert override.interval == "1m"
