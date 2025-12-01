"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from dac.models import EnablementManifest, ExceptionEntry, ExceptionItem, ExceptionList


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


class TestExceptionList:
    """Tests for ExceptionList model."""

    def test_minimal_exception_list(self) -> None:
        """Test minimal valid exception list."""
        exc_list = ExceptionList(
            list_id="my-list",
            name="My Exception List",
        )
        assert exc_list.list_id == "my-list"
        assert exc_list.type == "detection"
        assert exc_list.namespace_type == "single"

    def test_exception_list_missing_required(self) -> None:
        """Test exception list fails without required fields."""
        with pytest.raises(ValidationError):
            ExceptionList(list_id="my-list")  # missing name


class TestExceptionItem:
    """Tests for ExceptionItem model."""

    def test_exception_item_with_entry(self) -> None:
        """Test exception item with entry."""
        entry = ExceptionEntry(
            field="host.name",
            operator="included",
            type="match",
            value="server-01",
        )
        item = ExceptionItem(
            item_id="item-1",
            list_id="my-list",
            name="Allow server-01",
            entries=[entry],
        )
        assert item.entries[0].field == "host.name"
        assert item.entries[0].value == "server-01"
