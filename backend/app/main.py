from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.database import init_db

# Configure default logging format and level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentravision.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """
    Handles application startup and shutdown lifecycles.
    Ensures storage directories are present and initializes database connection.
    """
    logger.info("Starting up SentraVision API service...")
    try:
        # Create directories required for storage
        for name, directory in [
            ("Uploads", settings.upload_dir),
            ("Processed", settings.processed_dir),
            ("Frames", settings.frames_dir),
        ]:
            if not directory.exists():
                logger.info("Creating directory for %s at: %s", name, directory)
                directory.mkdir(parents=True, exist_ok=True)
            
        await init_db()
        logger.info("Application startup hook executed successfully.")
    except Exception as exc:
        logger.critical("Error during application startup!", exc_info=exc)
        raise

    yield

    logger.info("Shutting down SentraVision API service...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

