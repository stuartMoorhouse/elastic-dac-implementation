"""Elastic/Kibana API client."""

from typing import Any

import httpx

from dac.config import Settings


class ElasticClient:
    """Client for Kibana Security Detections API."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.kibana_api_url,
            headers={
                "Authorization": f"ApiKey {settings.elastic_api_key}",
                "kbn-xsrf": "true",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "ElasticClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # Rule operations

    def find_rules(self, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        """Find detection rules with pagination."""
        response = self._client.get(
            "/detection_engine/rules/_find",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def get_all_rules(self) -> list[dict[str, Any]]:
        """Fetch all detection rules, handling pagination."""
        all_rules: list[dict[str, Any]] = []
        page = 1
        per_page = 1000  # Max allowed by API

        while True:
            result = self.find_rules(page=page, per_page=per_page)
            rules = result.get("data", [])
            all_rules.extend(rules)

            total = result.get("total", 0)
            if len(all_rules) >= total:
                break
            page += 1

        return all_rules

    def get_rule(self, rule_id: str) -> dict[str, Any]:
        """Get a rule by rule_id."""
        response = self._client.get(
            "/detection_engine/rules",
            params={"rule_id": rule_id},
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def create_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """Create a new detection rule."""
        response = self._client.post("/detection_engine/rules", json=rule)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def update_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """Update an existing detection rule."""
        response = self._client.put("/detection_engine/rules", json=rule)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def bulk_action(
        self, action: str, rule_ids: list[str], dry_run: bool = False
    ) -> dict[str, Any]:
        """Perform bulk action on rules (enable, disable, delete, etc.)."""
        response = self._client.post(
            "/detection_engine/rules/_bulk_action",
            params={"dry_run": str(dry_run).lower()},
            json={"action": action, "ids": rule_ids},
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    # Exception list operations

    def find_exception_lists(
        self, page: int = 1, per_page: int = 100
    ) -> dict[str, Any]:
        """Find exception lists with pagination."""
        response = self._client.get(
            "/exception_lists/_find",
            params={"page": page, "per_page": per_page},
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def get_exception_list(self, list_id: str) -> dict[str, Any]:
        """Get an exception list by list_id."""
        response = self._client.get(
            "/exception_lists",
            params={"list_id": list_id, "namespace_type": "single"},
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def create_exception_list(self, exception_list: dict[str, Any]) -> dict[str, Any]:
        """Create a new exception list."""
        response = self._client.post("/exception_lists", json=exception_list)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def find_exception_items(
        self, list_id: str, page: int = 1, per_page: int = 100
    ) -> dict[str, Any]:
        """Find exception items in a list."""
        response = self._client.get(
            "/exception_lists/items/_find",
            params={
                "list_id": list_id,
                "namespace_type": "single",
                "page": page,
                "per_page": per_page,
            },
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    def create_exception_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Create a new exception item."""
        response = self._client.post("/exception_lists/items", json=item)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]
