from typing import Any

from app.config import get_settings
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ask.routes import router as ask_router


settings = get_settings()


app = FastAPI(title="OpenFDA Drug Recall Assistant")
app.mount("/static", StaticFiles(directory="public"), name="static")
app.include_router(ask_router)


@app.get("/", response_class=FileResponse)
def index() -> Any:
    return FileResponse("public/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
