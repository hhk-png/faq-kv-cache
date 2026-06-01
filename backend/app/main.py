import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.block_manager import block_manager
from app.api.faq import router as faq_router
from app.api.document import router as document_router
from app.api.qa import router as qa_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize FAQ blocks on startup and warmup cache."""
    logger.info("Building FAQ blocks...")
    block_manager.rebuild_blocks()
    logger.info(f"Built {block_manager.block_count} blocks")

    if block_manager.block_count > 0:
        logger.info("Starting cache warmup...")
        await block_manager.warmup_all_blocks()
    else:
        logger.info("No FAQs to warm up. Import data first.")

    yield
    logger.info("Shutting down...")


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

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


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "faq_blocks": block_manager.block_count,
    }
