from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from ask.schemas import AskRequest
from ask.services import run_conversation_with_gemini


router = APIRouter()


@router.post("/ask")
def ask(body: AskRequest):
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing 'question'")
    try:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise HTTPException(status_code=400, detail="GEMINI_API_KEY not set")
        result = run_conversation_with_gemini(question)
        return JSONResponse(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


