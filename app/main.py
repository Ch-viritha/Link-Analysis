from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import settings
from app.schemas import LinkRequest
from app.services import analysis_service
from app.services.llm_service import LLMError
from app.services.website_extractor import ExtractionError
from app.utils.validators import URLValidationError

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    yield


app = FastAPI(title="AI Link Analysis API", version="1.0.0", lifespan=lifespan,
              description="Analyse any website with an LLM: competitors, search queries, SEO, services and audience.")


def _err(status: int, message: str, kind: str):
    return JSONResponse(status_code=status, content={"success": False, "error": {"type": kind, "message": message}})


@app.post("/link-analysis", tags=["Analysis"])
async def link_analysis(req: LinkRequest):
    try:
        return await analysis_service.analyze(req.url, req.force_refresh)
    except URLValidationError as e:
        return _err(400, str(e), "invalid_url")
    except ExtractionError as e:
        return _err(e.status_code, str(e), "website_unreachable")
    except LLMError as e:
        return _err(502, str(e), "llm_error")


@app.get("/api/history", tags=["History"])
def history():
    return {"items": db.history()}


@app.get("/api/history/{rid}", tags=["History"])
def history_item(rid: int):
    item = db.get(rid)
    if not item:
        raise HTTPException(404, "Analysis not found")
    return item


@app.delete("/api/history/{rid}", tags=["History"])
def history_delete(rid: int):
    if not db.delete(rid):
        raise HTTPException(404, "Analysis not found")
    return {"success": True}


@app.get("/health", tags=["System"])
def health():
    p = settings.provider
    return {"status": "ok", "provider": p, "model": settings.models.get(p), "llm_configured": bool(settings.keys.get(p))}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
