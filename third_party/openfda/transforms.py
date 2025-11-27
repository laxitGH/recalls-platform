from typing import Any, Dict, List


def normalize_recall(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": record.get("recall_number", "") or "",
        "classification": record.get("classification", "") or "",
        "productName": record.get("product_description", "") or "",
        "firmName": record.get("firm_name", record.get("recalling_firm", "")) or "",
        "status": record.get("status", "") or "",
        "recallInitiationDate": record.get("recall_initiation_date", "") or "",
        "state": record.get("state", "") or "",
        "reasonForRecall": record.get("reason_for_recall", "") or "",
        "city": record.get("city", "") or "",
    }


def extract_year_from_yyyymmdd(date_yyyymmdd: str) -> str:
    if not date_yyyymmdd or len(date_yyyymmdd) < 4:
        return ""
    return date_yyyymmdd[:4]


def group_year_counts(records: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for r in records:
        year = extract_year_from_yyyymmdd(r.get("recall_initiation_date", ""))
        if not year:
            continue
        counts[year] = counts.get(year, 0) + 1
    return counts


