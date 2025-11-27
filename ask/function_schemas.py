from typing import Any, Dict, List


def gemini_function_declarations() -> List[Dict[str, Any]]:
    # Gemini expects a list of function_declarations (no 'type': 'function' wrapper)
    return [
        {
            "name": "search_recalls",
            "description": "Search FDA drug recall (enforcement) records.",
            "parameters": {
                "type": "object",
                "properties": {
                    "firm": {
                        "type": "string",
                        "description": "Exact firm name to filter by recalling_firm, e.g., 'SUN PHARMACEUTICAL INDUSTRIES INC'.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Lucene-style query, e.g., product_description:ibuprofen OR firm_name:\"Pfizer\"",
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["Class I", "Class II", "Class III"],
                        "description": "Recall severity classification",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max records to return (cap at 50).",
                    },
                    "skip": {
                        "type": "integer",
                        "description": "Pagination offset (>=0).",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort expression, e.g., recall_initiation_date:desc",
                    },
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "id",
                                "classification",
                                "productName",
                                "firmName",
                                "status",
                                "recallInitiationDate",
                                "state",
                                "reasonForRecall",
                                "city",
                            ],
                        },
                        "description": "Optional projection: return only these fields per recall.",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_recall_stats",
            "description": "Get only the requested statistics about drug recalls. Choose minimal metrics needed for the user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "stats": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["total", "byClassification", "topFirms", "bottomFirms", "byYear", "mostYear", "leastYear", "firmTotal"],
                        },
                        "description": "List of metrics to return. Provide only those needed for the question.",
                    },
                    "topFirmsLimit": {
                        "type": "integer",
                        "description": "How many firms to include when requesting topFirms (cap internally).",
                    },
                    "bottomFirmsLimit": {
                        "type": "integer",
                        "description": "How many firms to include when requesting bottomFirms (cap internally).",
                    },
                    "firm": {
                        "type": "string",
                        "description": "Firm name to compute totals for when requesting firmTotal (uses recalling_firm exact match).",
                    },
                    "classification": {
                        "type": "string",
                        "enum": ["Class I", "Class II", "Class III"],
                        "description": "Optional filter to apply to firm counts and/or totals.",
                    },
                    "startYear": {
                        "type": "integer",
                        "description": "Start year for byYear/mostYear/leastYear (inclusive).",
                    },
                    "endYear": {
                        "type": "integer",
                        "description": "End year for byYear/mostYear/leastYear (inclusive).",
                    },
                },
                "required": [],
            },
        },
    ]


