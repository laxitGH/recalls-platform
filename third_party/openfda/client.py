from typing import Any, Dict, List, Optional

import requests


class OpenFDAClient:
    BASE_URL = "https://api.fda.gov/drug/enforcement.json"

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()

    def _http_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.get(self.BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _compose_search(query: Optional[str], classification: Optional[str]) -> Optional[str]:
        terms: List[str] = []
        if classification:
            terms.append(f'classification:"{classification}"')
        if query:
            terms.append(query)
        if not terms:
            return None
        return " AND ".join(terms)

    def search_enforcements(
        self,
        query: Optional[str] = None,
        classification: Optional[str] = None,
        limit: int = 10,
        skip: int = 0,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        limit = max(1, min(limit, 100))
        params: Dict[str, Any] = {"limit": limit, "skip": max(0, skip)}
        search = self._compose_search(query, classification)
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort
        return self._http_get(params)

    def count_buckets(self, field: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"count": f"{field}.exact"}
        if search:
            params["search"] = search
        data = self._http_get(params)
        return data.get("results", []) or []

    def get_recent_enforcements(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 100))
        data = self.search_enforcements(limit=limit, sort="recall_initiation_date:desc")
        return data.get("results", []) or []


