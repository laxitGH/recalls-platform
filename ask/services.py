from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import re
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content as glm_content

from app.config import get_settings
from ask.function_tools import get_recall_stats_handler, search_recalls_handler
from third_party.openfda.client import OpenFDAClient
from utils.logger import get_logger, kv_message as kv

logger = get_logger(__name__)


def run_conversation_with_gemini(question: str) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=settings.gemini_api_key)

    from ask.function_schemas import gemini_function_declarations

    # available_models = genai.list_models()
    # available_model_names = [f'{m.name} - {m.supported_generation_methods}' for m in available_models]
    # print("Available models", available_model_names)
    
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        tools=[{"function_declarations": gemini_function_declarations()}],
        system_instruction=(
            "You are an assistant that answers questions about FDA drug recalls using the openFDA "
            "Drug Enforcement API. Use the available tools to fetch real data before answering. "
            "Do not ask follow-up questions if the user intent is clear enough to apply sensible defaults. "
            "Defaults: for 'per firm' or firm-level questions, return topFirms with topFirmsLimit=10; "
            "for 'per year' questions use the last 10 years; for search requests use limit=10 unless specified. "
            "Translate natural-language time ranges into openFDA date range queries using recall_initiation_date, "
            "e.g., recall_initiation_date:[YYYYMMDD TO YYYYMMDD], and sort by recall_initiation_date:desc. "
            "When filtering by firm, USE the 'recalling_firm' field (not 'firm_name'). "
            "For queries like 'how many recalls for firm <NAME>', call get_recall_stats with "
            "stats:['firmTotal'] and firm:'<NAME>' and return only that metric. "
            "For 'least recalls' or 'fewest recalls', call get_recall_stats with stats:['bottomFirms'] "
            "and bottomFirmsLimit. You may include classification:'Class I'|'Class II'|'Class III' to filter."
            "Return only the minimal metrics needed for the user's question."
        ),
    )

    chat = model.start_chat()
    openfda_client = OpenFDAClient()
    last_tool_payload: Optional[Dict[str, Any]] = None
    max_rounds = 5

    def call_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(kv("tool_call", name=name, args=args))
        if name == "search_recalls":
            return search_recalls_handler(args, openfda_client)
        if name == "get_recall_stats":
            return get_recall_stats_handler(args, openfda_client)
        return {"error": f"Unknown tool: {name}"}

    logger.info(kv("question", text=question))
    response = chat.send_message(question)
    for _ in range(max_rounds):
        parts = []
        if response and response.candidates:
            parts = response.candidates[0].content.parts or []
        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        if function_calls:
            for fc in function_calls:
                name = fc.name
                args = dict(fc.args) if hasattr(fc, "args") else {}
                # Intercept misrouted calls based on intent and rewrite appropriately
                uq = (question or "").lower()
                # map numeric class to label
                class_label = None
                if "classification" in uq:
                    if " 1" in uq or " class 1" in uq or "class i" in uq:
                        class_label = "Class I"
                    elif " 2" in uq or " class 2" in uq or "class ii" in uq:
                        class_label = "Class II"
                    elif " 3" in uq or " class 3" in uq or "class iii" in uq:
                        class_label = "Class III"
                if name == "get_recall_stats" and ("how many" in uq and "firm" in uq):
                    # try to extract firm name from the question
                    try:
                        firm_part = uq.split("firm", 1)[1].strip()
                        tokens = [t for t in firm_part.split() if t not in ("is", "are", "exists", "for", "of", "the")]
                        firm_name = " ".join(tokens).strip().strip('"\'' )
                    except Exception:
                        firm_name = ""
                    args = {"stats": ["firmTotal"], "firm": firm_name or (args.get("firm") or "")}
                    if class_label:
                        args["classification"] = class_label
                # least/fewest → bottomFirms (force even if model tried something else)
                if ("least" in uq) or ("fewest" in uq):
                    name = "get_recall_stats"
                    args = {"stats": ["bottomFirms"], "bottomFirmsLimit": 10}
                    if class_label:
                        args["classification"] = class_label
                # If user asked to list recalls for a firm, force search_recalls with firm filter (regex with word boundary)
                firm_list_match = re.search(r'(?:recalls\s+for\s+firm|list\s+(?:all\s+)?recalls\s+for\s+firm)\s+(.+)', uq)
                if firm_list_match:
                    firm_name = firm_list_match.group(1).strip().strip('"\'' )
                    name = "search_recalls"
                    args = {"firm": firm_name, "limit": 50, "sort": "recall_initiation_date:desc"}
                payload = call_tool(name, args)
                logger.info(kv("tool_result", name=name, keys=list(payload.keys())))
                last_tool_payload = payload
                # Send function response back to the model
                tool_msg = glm_content.Content(
                    role="tool",
                    parts=[
                        glm_content.Part(
                            function_response=glm_content.FunctionResponse(
                                name=name,
                                response=payload,
                            )
                        )
                    ],
                )
                response = chat.send_message(tool_msg)
            # Continue loop to allow the model to produce a final message
            continue
        # No function call; add lightweight fallbacks for common intents with defaults
        final_text = getattr(response, "text", "") or ""
        user_q = (question or "").lower()
        # Fallback: "last N recalls"
        if ("last" in user_q) and ("recall" in user_q):
            try:
                after_last = user_q.split("last", 1)[1].strip()
                tokens = after_last.split()
                n = None
                if tokens and tokens[0].isdigit():
                    n = int(tokens[0])
                if n is None:
                    n = 10
            except Exception:
                n = 10
            payload = search_recalls_handler(
                {"limit": n, "sort": "recall_initiation_date:desc"},
                openfda_client,
            )
            count = len(payload.get("recalls", []) or [])
            answer = f"Last {n} recalls (newest first). Found {count}."
            return {"answer": answer, "data": payload}
        # Fallback: list recalls for a specific firm
        if (("list" in user_q or "recalls for firm" in user_q or "list all recalls" in user_q) and "firm" in user_q):
            try:
                firm_part = user_q.split("firm", 1)[1].strip()
                tokens = [t for t in firm_part.split() if t not in ("is", "are", "exists", "for", "of", "the")]
                firm_name = " ".join(tokens).strip().strip('"\'' )
            except Exception:
                firm_name = ""
            payload = search_recalls_handler(
                {"firm": firm_name, "limit": 50, "sort": "recall_initiation_date:desc"},
                openfda_client,
            )
            count = len(payload.get("recalls", []) or [])
            answer = f"Showing {count} recalls for firm {firm_name or ''} (newest first)."
            return {"answer": answer, "data": payload}
        # Fallback: only for generic “which firms/top firms/most recalls”
        if any(kw in user_q for kw in ["which firms", "top firms", "most recalls", "who has the most"]):
            payload = get_recall_stats_handler({"stats": ["topFirms"], "topFirmsLimit": 10}, openfda_client)
            top = payload.get("topFirms", []) or []
            if top:
                lines = [f'{i+1}. {t.get("firm","Unknown")}: {t.get("count",0)}' for i, t in enumerate(top)]
                answer = "Top firms by recall count:\n" + "\n".join(lines)
            else:
                answer = "No firm recall data available."
            return {"answer": answer, "data": payload}
        # Time range fallback: last N days/weeks/months → recall_initiation_date range
        if ("last" in user_q or "past" in user_q) and "recall" in user_q:
            # crude parse for "last 1 week(s)/day(s)/month(s)"
            n = 1
            if "last" in user_q:
                try:
                    after_last = user_q.split("last", 1)[1].strip()
                    tokens = after_last.split()
                    if tokens and tokens[0].isdigit():
                        n = int(tokens[0])
                        unit = tokens[1] if len(tokens) > 1 else "days"
                    else:
                        unit = tokens[0] if tokens else "days"
                except Exception:
                    unit = "days"
            elif "past" in user_q:
                try:
                    after_past = user_q.split("past", 1)[1].strip()
                    tokens = after_past.split()
                    if tokens and tokens[0].isdigit():
                        n = int(tokens[0])
                        unit = tokens[1] if len(tokens) > 1 else "days"
                    else:
                        unit = tokens[0] if tokens else "days"
                except Exception:
                    unit = "days"
            unit = unit.rstrip('s')
            now = datetime.utcnow()
            if unit in ("day",):
                start = now - timedelta(days=n)
            elif unit in ("week",):
                start = now - timedelta(weeks=n)
            elif unit in ("month",):
                # approximate months as 30 days
                start = now - timedelta(days=30 * n)
            else:
                start = now - timedelta(days=n)
            start_str = start.strftime("%Y%m%d")
            end_str = now.strftime("%Y%m%d")
            query = f"recall_initiation_date:[{start_str} TO {end_str}]"
            payload = search_recalls_handler(
                {"query": query, "limit": 50, "sort": "recall_initiation_date:desc"},
                openfda_client,
            )
            count = len(payload.get("recalls", []) or [])
            answer = f"Showing {count} recalls from {start_str} to {end_str}."
            return {"answer": answer, "data": payload}
        # Firm total fallback: "how many ... firm <NAME>"
        if ("how many" in user_q) and ("firm" in user_q):
            try:
                # naive extract text after 'firm'
                firm_part = user_q.split("firm", 1)[1].strip()
                # remove leading words like 'is', 'are', 'exists', etc.
                tokens = [t for t in firm_part.split() if t not in ("is", "are", "exists", "for", "of", "the")]
                # take a reasonable slice, rejoin and uppercase as in dataset
                firm_name = " ".join(tokens).strip().strip('"\'' )
                if firm_name:
                    query = f'recalling_firm:"{firm_name}"'
                    data = openfda_client.search_enforcements(query=query, limit=1, skip=0)
                    meta = (data or {}).get("meta", {})
                    total = int(((meta.get("results") or {}).get("total")) or 0)
                    answer = f"Total recalls for firm {firm_name}: {total}"
                    # Also return a small sample list for context
                    sample_payload = search_recalls_handler({"query": query, "limit": min(10, total), "sort": "recall_initiation_date:desc"}, openfda_client)
                    return {"answer": answer, "data": sample_payload if sample_payload else {"total": total}}
            except Exception:
                pass
        return {"answer": final_text, "data": last_tool_payload}

    return {"answer": "Sorry, I could not complete the request.", "data": last_tool_payload}


