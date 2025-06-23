import logging
from fastapi import FastAPI, APIRouter, Depends
from typing import Dict, Any, Annotated
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from .state_manager import state_manager
from .module_loader import ModuleLoader
from .api import create_api_routes
from .auth import router as auth_router, get_current_user
from .models import User
from .database import create_db_and_tables
from .init_db import init_db
from .content_pack_manager import ContentPackManager
from .logging_config import setup_logging
from .modules.timeline.tool import router as timeline_router

# Apply the JSON logging configuration at the earliest point
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This code runs on server startup
    logging.info("--- IntentVerse Core Engine Starting Up ---")
    create_db_and_tables()
    # Initialize the database with default data (admin user and groups)
    init_db()
    # Discover and load all modules from the 'modules' directory
    loader.load_modules()
    # Load default content pack after modules are loaded
    content_pack_manager.load_default_content_pack()
    
    # Log system startup event
    from .modules.timeline.tool import log_system_event
    log_system_event(
        title="Core Service Started",
        description="The IntentVerse Core Engine has been started and is ready to accept connections."
    )
    logging.info("Logged system startup event")
    
    yield
    # This code runs on server shutdown
    logging.info("--- IntentVerse Core Engine Shutting Down ---")
    
    # Log system shutdown event
    try:
        from .modules.timeline.tool import log_system_event
        log_system_event(
            title="Core Service Stopped",
            description="The IntentVerse Core Engine has been stopped."
        )
        logging.info("Logged system shutdown event")
    except Exception as e:
        logging.error(f"Failed to log shutdown event: {e}")

# --- Application Initialization ---
app = FastAPI(
    title="IntentVerse Core Engine",
    description="Manages state, tools, and logic for the IntentVerse simulation.",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow cross-origin requests from the web client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Web client URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

loader = ModuleLoader(state_manager)
content_pack_manager = ContentPackManager(state_manager, loader)

# Create the main API routes, passing the loader and content pack manager to them.
api_router = create_api_routes(loader, content_pack_manager)
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(timeline_router)

# Create a new, separate router for debug endpoints
debug_router = APIRouter()

@debug_router.get("/debug/module-loader-state", tags=["Debug"])
def get_module_loader_state(
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Returns a snapshot of the ModuleLoader's state for debugging purposes.
    This allows us to see from the outside what the server sees on the inside.
    Only available to authenticated users.
    """
    return {
        "modules_path_calculated": str(loader.modules_path),
        "modules_path_exists": loader.modules_path.exists(),
        "loading_errors": loader.errors,
        "loaded_modules": list(loader.modules.keys())
    }

app.include_router(debug_router, prefix="/api/v1")


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def read_root():
    """
    A simple root endpoint to confirm the server is running.
    """
    return {"message": "Welcome to the IntentVerse Core Engine"}