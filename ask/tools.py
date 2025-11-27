from typing import Any, Dict, List
from datetime import datetime

from third_party.openfda.client import OpenFDAClient
from third_party.openfda.transforms import normalize_recall, group_year_counts


def search_recalls_handler(args: Dict[str, Any], client: OpenFDAClient) -> Dict[str, Any]:
    query = args.get("query")
    firm = (args.get("firm") or "").strip()
    if firm:
        firm_clause = f'recalling_firm:"{firm}"'
        if query:
            query = f"({query}) AND {firm_clause}"
        else:
            query = firm_clause
    classification = args.get("classification")
    # Coerce numeric inputs to safe ints for the OpenFDA API
    raw_limit = args.get("limit", 10)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = 10
    # enforce bounds
    if limit < 1:
        limit = 1
    if limit > 50:
        limit = 50
    skip = int(args.get("skip", 0) or 0)
    sort = args.get("sort")
    fields = args.get("fields")  # optional projection
    data = client.search_enforcements(query=query, classification=classification, limit=limit, skip=skip, sort=sort)
    results = data.get("results", []) or []
    normalized = [normalize_recall(r) for r in results]
    if isinstance(fields, list) and fields:
        filtered: List[Dict[str, Any]] = []
        for item in normalized:
            filtered.append({k: v for k, v in item.items() if k in fields})
        normalized = filtered
    return {"recalls": normalized, "meta": data.get("meta", {})}


def get_recall_stats_handler(args: Dict[str, Any], client: OpenFDAClient) -> Dict[str, Any]:
    stats_requested: List[str] = args.get("stats") or []
    # Normalize values
    stats_requested = [s for s in stats_requested if isinstance(s, str)]
    include_total = "total" in stats_requested
    include_class = "byClassification" in stats_requested
    include_top_firms = "topFirms" in stats_requested
    include_bottom_firms = "bottomFirms" in stats_requested
    include_by_year = "byYear" in stats_requested or "mostYear" in stats_requested or "leastYear" in stats_requested
    include_firm_total = "firmTotal" in stats_requested
    classification_filter = (args.get("classification") or "").strip()

    result: Dict[str, Any] = {}

    # firmTotal
    if include_firm_total:
        firm = (args.get("firm") or "").strip()
        if firm:
            parts = [f'recalling_firm:"{firm}"']
            if classification_filter:
                parts.append(f'classification:"{classification_filter}"')
            query = " AND ".join(parts)
            data = client.search_enforcements(query=query, limit=1, skip=0)
            meta = (data or {}).get("meta", {})
            total = int(((meta.get("results") or {}).get("total")) or 0)
            result["firmTotal"] = total
            result["firm"] = firm
            # Early return if only firmTotal requested
            if set(stats_requested) == {"firmTotal"}:
                return result
        else:
            result["firmTotal"] = 0

    # byClassification and/or total
    recalls_by_classification: Dict[str, int] = {}
    if include_class or include_total:
        classification_buckets = client.count_buckets("classification")
        recalls_by_classification = {b.get("term", "") or "Unknown": int(b.get("count", 0) or 0) for b in classification_buckets}
        if include_class:
            result["recallsByClassification"] = recalls_by_classification
        if include_total:
            result["totalRecalls"] = sum(recalls_by_classification.values())

    # topFirms
    if include_top_firms or include_bottom_firms:
        limit = int(args.get("topFirmsLimit", 5) or 5)
        limit = max(1, min(limit, 10))
        bottom_limit = int(args.get("bottomFirmsLimit", limit) or limit)
        bottom_limit = max(1, min(bottom_limit, 10))
        search_clause = None
        if classification_filter:
            search_clause = f'classification:"{classification_filter}"'
        firm_buckets = client.count_buckets("recalling_firm", search=search_clause)
        # top
        if include_top_firms:
            top_firms: List[Dict[str, Any]] = []
            for b in firm_buckets[:limit]:
                term = b.get("term", "") or "Unknown"
                count = int(b.get("count", 0) or 0)
                top_firms.append({"firm": term, "count": count})
            result["topFirms"] = top_firms
        # bottom (ascending)
        if include_bottom_firms:
            sorted_asc = sorted(
                [{"firm": (b.get("term", "") or "Unknown"), "count": int(b.get("count", 0) or 0)} for b in firm_buckets],
                key=lambda x: x["count"]
            )
            bottom = [b for b in sorted_asc if b["count"] > 0][:bottom_limit]
            result["bottomFirms"] = bottom

    # byYear / mostYear / leastYear
    if include_by_year:
        start_year = args.get("startYear")
        end_year = args.get("endYear")
        this_year = datetime.utcnow().year
        if not isinstance(start_year, int) or not isinstance(end_year, int) or start_year > end_year:
            start_year = this_year - 9
            end_year = this_year
        recalls_by_year: Dict[str, int] = {}
        for year in range(start_year, end_year + 1):
            search = f"recall_initiation_date:[{year}0101 TO {year}1231]"
            try:
                data = client.search_enforcements(query=search, limit=1)
                meta = (data or {}).get("meta", {})
                total = ((meta.get("results") or {}).get("total")) or 0
                recalls_by_year[str(year)] = int(total)
            except Exception:
                recalls_by_year[str(year)] = 0
        if "byYear" in stats_requested:
            result["recallsByYear"] = recalls_by_year
        if "mostYear" in stats_requested and recalls_by_year:
            most_year = max(recalls_by_year.items(), key=lambda kv: kv[1])
            result["mostYear"] = {"year": most_year[0], "count": most_year[1]}
        if "leastYear" in stats_requested and recalls_by_year:
            least_year = min(recalls_by_year.items(), key=lambda kv: kv[1])
            result["leastYear"] = {"year": least_year[0], "count": least_year[1]}

    return result


