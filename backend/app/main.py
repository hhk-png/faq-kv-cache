from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.faq import router as faq_router
from app.api.document import router as document_router
from app.api.qa import router as qa_router
from app.api.cache import router as cache_router

app = FastAPI(title=settings.app_name, version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(faq_router)
app.include_router(document_router)
app.include_router(qa_router)
app.include_router(cache_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.app_name}
